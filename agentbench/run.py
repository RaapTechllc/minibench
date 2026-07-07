"""Run a MoA config against a task suite with multiple trials, executable grading,
and real cost/latency accounting — then emit a committable results artifact.

Live model calls require a provider API key in the environment (OPENROUTER_API_KEY
or OLLAMA_API_KEY). Without one, use ``--dry-run`` to validate config + tasks +
the whole pipeline against a stub model (no network) — this is also what CI runs
as a smoke test so config drift can never ship silently.

Usage:
  python -m agentbench.run --config agentbench/presets/moa-v1.yaml \
      --tasks agentbench/tasks/coding-v1.json --trials 3 --provider openrouter
  python -m agentbench.run --config ... --tasks ... --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentbench.config import load_moa_config, single_model_config, MoAConfig
from agentbench.client import InfraError, OpenAICompatClient
from agentbench.grading import GRADER_VERSION, contains_canary, grade
from agentbench.moa import MoAModel, MoAResult
from agentbench.stats import (
    bootstrap_ci_by_task, consistency, mean_brier, pass_rate, pass_hat_k, wilson_ci, percentile,
)
from agentbench.resources import RESULTS_DIR
from agentbench import minibench_gen


def _load_env_files() -> None:
    """Load .env from repo root and agentbench/ (first wins for duplicate keys)."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env", override=False)
    load_dotenv(repo_root / "agentbench" / ".env", override=False)


@dataclass
class TrialResult:
    task_id: str
    category: str
    trial: int
    passed: bool
    score: float
    cost_usd: float | None
    latency_ms: int
    tokens_in: int
    tokens_out: int
    detail: str
    # True when the trial died on transient infrastructure (rate limit / 5xx /
    # timeout after retries). Excluded from every capability denominator.
    infra_error: bool = False
    # True when the model output echoed a benchmark canary string — a hard
    # training-contamination signal; the run must be quarantined.
    canary_flag: bool = False


class StubModel:
    """Offline stand-in for --dry-run. Returns canned answers that satisfy the
    seed tasks' oracles, so the full grade/aggregate path is exercised with no
    network. It is NOT a real model — dry-run scores are meaningless as a benchmark.
    """

    _ANSWERS = {
        "code-two-sum": "```python\ndef two_sum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        if target - n in seen:\n            return [seen[target - n], i]\n        seen[n] = i\n```",
        "code-parse-durations": "```python\nimport re\ndef total_seconds(spec):\n    units = {'h': 3600, 'm': 60, 's': 1}\n    return sum(int(v) * units[u] for v, u in re.findall(r'(\\d+)([hms])', spec))\n```",
        "reason-word-problem": "The journey is 165 minutes.",
        "tooluse-classify-json": '{"priority": "URGENT", "is_production": true}',
    }

    def generate_for(self, task_id: str) -> MoAResult:
        text = self._ANSWERS.get(task_id, "")
        return MoAResult(text=text, cost_usd=0.0, prompt_tokens=0, completion_tokens=0,
                         latency_ms=0, n_calls=0)


def load_tasks(path: str | Path) -> tuple[str, list[dict[str, Any]]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("suite", "unknown"), data.get("tasks", [])


def gold_self_check(tasks: list[dict[str, Any]]) -> list[str]:
    """Grade each task's own ``_gold`` answer; return the ids that FAIL.

    Run on every freshly generated (private-seed) suite before any live call —
    a generator/grader drift bug on an unseen seed would otherwise silently
    misgrade every model. Tasks without ``_gold`` (loaded from a published
    file, which strips it) are skipped.
    """
    bad: list[str] = []
    for task in tasks:
        gold = task.get("_gold")
        if gold is None:
            continue
        if not grade(task["verification"], gold).passed:
            bad.append(task["id"])
    return bad


def run_suite(
    config: MoAConfig,
    tasks: list[dict[str, Any]],
    *,
    trials: int,
    model: MoAModel | None,
    stub: StubModel | None = None,
) -> list[TrialResult]:
    results: list[TrialResult] = []
    for task in tasks:
        for trial in range(1, trials + 1):
            try:
                if stub is not None:
                    out = stub.generate_for(task["id"])
                else:
                    assert model is not None
                    out = model.generate(task["prompt"])
            except InfraError as e:
                # Provider luck is not model capability: record and move on so
                # one flaky endpoint doesn't lose the rest of the suite.
                results.append(
                    TrialResult(
                        task_id=task["id"],
                        category=task.get("category", "unknown"),
                        trial=trial,
                        passed=False,
                        score=0.0,
                        cost_usd=None,
                        latency_ms=0,
                        tokens_in=0,
                        tokens_out=0,
                        detail=f"infra: {e}",
                        infra_error=True,
                    )
                )
                continue
            g = grade(task["verification"], out.text)
            results.append(
                TrialResult(
                    task_id=task["id"],
                    category=task.get("category", "unknown"),
                    trial=trial,
                    passed=g.passed,
                    score=g.score,
                    cost_usd=out.cost_usd,
                    latency_ms=out.latency_ms,
                    tokens_in=out.prompt_tokens,
                    tokens_out=out.completion_tokens,
                    detail=g.detail,
                    canary_flag=contains_canary(out.text),
                )
            )
    return results


def _calibration_axis(scored: list[TrialResult]) -> dict[str, Any]:
    """Suite-level calibration axis (Brier) when the run has calibration items.
    Calibration is CONTINUOUS (graded on score, not passed), so it is excluded
    from the binary pool and reported separately — a lower mean Brier is better."""
    calib = [r for r in scored if r.category == "calibration"]
    if not calib:
        return {}
    return {
        "calibration_brier": round(mean_brier([r.score for r in calib]), 4),
        "n_calibration_trials": len(calib),
    }


def _robustness_axis(scored: list[TrialResult]) -> dict[str, Any]:
    """Suite-level robustness axis when the run has matched (base, pert) pairs.
    Consistency = fraction of pair-trials where correctness agrees (1 − flip
    rate); robustness_correct = fraction where BOTH are correct. Pairing is
    read from the id convention ``...-<pid>-base`` / ``...-<pid>-pert``; trial
    numbers are intersected so an infra-dropped side never fabricates a flip."""
    robust = [r for r in scored if r.category == "robustness"]
    if not robust:
        return {}
    pairs: dict[str, dict[str, dict[int, bool]]] = {}
    for r in robust:
        pid, _, role = r.task_id.rpartition("-")
        pairs.setdefault(pid, {"base": {}, "pert": {}}).setdefault(role, {})[r.trial] = r.passed
    pair_trials: list[tuple[bool, bool]] = []
    both_correct = 0
    covered_pairs = 0  # pairs that actually contribute a scored (base, pert) trial
    for d in pairs.values():
        overlap = set(d.get("base", {})) & set(d.get("pert", {}))
        if overlap:
            covered_pairs += 1
        for j in overlap:
            b, p = d["base"][j], d["pert"][j]
            pair_trials.append((b, p))
            both_correct += b and p
    if not pair_trials:
        return {}
    return {
        # PRIMARY axis: fraction of perturbation pairs solved correctly on BOTH
        # sides. Unlike bare consistency, this can't be gamed by answering every
        # prompt with the same WRONG value (both-wrong agrees but isn't correct).
        "robustness_correct": round(both_correct / len(pair_trials), 4),
        # Diagnostics (stability regardless of correctness). Kept local, NOT
        # published as the leaderboard headline — consistency alone is 1.0 for a
        # uniformly-wrong model.
        "robustness_consistency": round(consistency(pair_trials), 4),
        "robustness_flip_rate": round(1 - consistency(pair_trials), 4),
        # Count only pairs that actually backed the numbers (an all-infra side
        # contributes nothing and must not inflate the reported coverage).
        "n_robust_pairs": covered_pairs,
    }


def summarize(config: MoAConfig, suite: str, trials: int, results: list[TrialResult]) -> dict[str, Any]:
    # Infra-error trials are excluded from EVERY capability denominator: they
    # measure the provider, not the model. They are still counted and reported
    # so a run with any of them can be blocked from publishing.
    scored = [r for r in results if not r.infra_error]
    # Two categories ride on their own axes and are EXCLUDED from the binary pool
    # so they can't distort pass_rate, pass^k, the CIs, or McNemar ranking:
    #   • calibration — continuous (graded on Brier, not pass/fail).
    #   • robustness  — matched base/pert PAIRS with the same gold; counting both
    #     sides would double-weight one capability with correlated near-duplicates
    #     and narrow the task-bootstrap CI on non-independent items. Its signal is
    #     the consistency axis, not the headline pass rate.
    # Suites without these categories leave `binary == scored`, so core/hard
    # summaries are byte-identical to pre-pro runs.
    _axis_only = {"calibration", "robustness"}
    binary = [r for r in scored if r.category not in _axis_only]
    total = len(binary)
    passes = sum(1 for r in binary if r.passed)
    # Per-task pass counts for pass^k.
    by_task: dict[str, list[TrialResult]] = {}
    for r in binary:
        by_task.setdefault(r.task_id, []).append(r)
    per_task_passes = [sum(1 for r in rs if r.passed) for rs in by_task.values()]
    per_task_trials = [len(rs) for rs in by_task.values()]
    per_task_fracs = [p / n for p, n in zip(per_task_passes, per_task_trials) if n > 0]

    # Cost/latency count EVERY non-infra call (calibration calls cost money too).
    n_all_tasks = len({r.task_id for r in scored})
    latencies = [float(r.latency_ms) for r in scored]
    costs = [r.cost_usd for r in scored if r.cost_usd is not None]
    total_cost = sum(costs) if costs else None
    ci_lo, ci_hi = wilson_ci(passes, total)
    boot_lo, boot_hi = bootstrap_ci_by_task(per_task_fracs)
    # Infra-excluded trials can leave a task with fewer than `trials` scored
    # trials; cap k so those tasks still contribute to pass^k instead of being
    # silently dropped (which would zero the metric).
    effective_k = min([trials, *per_task_trials]) if per_task_trials else trials

    proposer = config.proposers[0]
    summary = {
        "suite": suite,
        "moa_config": {
            "name": config.name,
            "self_moa": config.self_moa,
            "models": config.models,
        },
        "grader_version": GRADER_VERSION,
        "decoding": {
            "temperature": proposer.temperature,
            "top_p": proposer.top_p,
            "max_tokens": proposer.max_tokens,
            "system_prompt": None if config.single else "moa",
        },
        "n_tasks": len(by_task),
        "n_trials": trials,
        # The k actually used for pass^k: infra-excluded trials can lower it
        # below n_trials. Recorded so an inflated pass_hat_k can never masquerade
        # as a clean pass^{n_trials} on the leaderboard.
        "pass_hat_k_effective_k": effective_k,
        "n_infra_errors": sum(1 for r in results if r.infra_error),
        "n_canary_flags": sum(1 for r in results if r.canary_flag),
        "pass_rate": round(pass_rate(passes, total), 4),
        "pass_rate_ci95": [round(ci_lo, 4), round(ci_hi, 4)],
        # Task-level bootstrap CI: trials cluster within tasks, so the pooled
        # Wilson interval is too narrow — this one is honest about ranking noise.
        "pass_rate_ci95_boot": [round(boot_lo, 4), round(boot_hi, 4)],
        "pass_hat_k": round(pass_hat_k(per_task_passes, per_task_trials, k=effective_k), 4),
        "cost_usd_total": round(total_cost, 6) if total_cost is not None else None,
        "cost_usd_per_task": round(total_cost / n_all_tasks, 6) if total_cost is not None and n_all_tasks else None,
        "latency_p50_ms": round(percentile(latencies, 50), 1),
        "latency_p95_ms": round(percentile(latencies, 95), 1),
    }
    # Novel axes: present ONLY when the run contains those items, so core/hard
    # summaries are unchanged.
    summary.update(_calibration_axis(scored))
    summary.update(_robustness_axis(scored))
    return summary


def to_agent_run_submit(
    summary: dict[str, Any],
    trials: list[TrialResult],
    *,
    provider: str,
    harness: str = "agentbench",
    harness_version: str | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Transform run.py output into the backend ``AgentRunSubmit`` shape."""
    ci = summary.get("pass_rate_ci95") or [None, None]

    def pct(x: float | None) -> float | None:
        return round(x * 100, 4) if x is not None else None

    tokens_in = sum(r.tokens_in for r in trials)
    tokens_out = sum(r.tokens_out for r in trials)

    return {
        "harness": harness,
        "harness_version": harness_version,
        "moa_config": summary.get("moa_config"),
        "benchmark_suite": summary["suite"],
        "provider": provider,
        "grader_version": summary.get("grader_version"),
        "decoding": summary.get("decoding"),
        "n_infra_errors": summary.get("n_infra_errors", 0),
        "n_canary_flags": summary.get("n_canary_flags", 0),
        **(provenance or {}),
        "n_tasks": summary["n_tasks"],
        "n_trials": summary["n_trials"],
        "pass_rate": pct(summary["pass_rate"]),
        "pass_hat_k": pct(summary.get("pass_hat_k")),
        "ci95_low": pct(ci[0]),
        "ci95_high": pct(ci[1]),
        "cost_usd_per_task": summary.get("cost_usd_per_task"),
        "latency_p50_ms": int(summary["latency_p50_ms"]) if summary.get("latency_p50_ms") is not None else None,
        "latency_p95_ms": int(summary["latency_p95_ms"]) if summary.get("latency_p95_ms") is not None else None,
        # Novel pro axes (None unless the run had those items). robustness_correct
        # (both-sides-correct) is the leaderboard headline — bare consistency is
        # gameable by uniform wrongness, so it is not published.
        "calibration_brier": summary.get("calibration_brier"),
        "robustness_correct": summary.get("robustness_correct"),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "results": [
            {
                "task_id": r.task_id,
                "category": r.category,
                "trial": r.trial,
                "passed": r.passed,
                "score": r.score,
                "cost_usd": r.cost_usd,
                "latency_ms": r.latency_ms,
                "tokens_in": r.tokens_in,
                "tokens_out": r.tokens_out,
            }
            for r in trials
        ],
    }


def publish_run(api_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST an ``AgentRunSubmit`` payload to the agents API."""
    base = api_url.rstrip("/")
    url = f"{base}/api/v1/agents/runs"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"publish failed ({e.code}): {detail}") from e


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=Path(__file__).resolve().parent,
        )
        return out.stdout.strip() or None if out.returncode == 0 else None
    except OSError:
        return None


def build_provenance(*, seed: int | None, is_private_split: bool) -> dict[str, Any]:
    """Reproducibility fingerprint recorded with every run. ``seed_sha256``
    proves two runs shared a seed without revealing it."""
    gen_path = Path(minibench_gen.__file__)
    return {
        "seed_sha256": hashlib.sha256(str(seed).encode()).hexdigest() if seed is not None else None,
        "generator_sha256": hashlib.sha256(gen_path.read_bytes()).hexdigest(),
        "git_commit": _git_commit(),
        "is_private_split": is_private_split,
    }


def main(argv: list[str] | None = None) -> int:
    _load_env_files()
    ap = argparse.ArgumentParser(description="Run a MoA config against a task suite.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--config", help="MoA preset YAML")
    src.add_argument(
        "--model",
        help="score ONE model as one model string (e.g. openrouter/moonshotai/kimi-k2.7-code); "
        "single call per prompt, no aggregator",
    )
    task_src = ap.add_mutually_exclusive_group(required=True)
    task_src.add_argument("--tasks", help="published suite JSON (public dev slice)")
    task_src.add_argument(
        "--generate",
        choices=sorted(minibench_gen.SUITES),
        help="generate the suite IN-MEMORY from the MINIBENCH_SEED env var "
        "(private split; golds never touch disk)",
    )
    ap.add_argument("--per-category", type=int, default=5,
                    help="instances per category for --generate (default 5)")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--provider", default="openrouter")
    ap.add_argument("--dry-run", action="store_true", help="offline stub, no network/keys")
    ap.add_argument("--out", default=None, help="results JSON path (default: agentbench/results/<ts>.json)")
    ap.add_argument(
        "--publish",
        default=None,
        metavar="API_URL",
        help="POST summary to backend (e.g. http://localhost:3070)",
    )
    ap.add_argument(
        "--allow-infra-errors",
        action="store_true",
        help="publish even with infra-error trials (default: refuse; rerun instead)",
    )
    args = ap.parse_args(argv)

    config = single_model_config(args.model) if args.model else load_moa_config(args.config)

    seed: int | None = None
    if args.generate:
        raw_seed = os.environ.get("MINIBENCH_SEED")
        if not raw_seed:
            print("ERROR: --generate requires the MINIBENCH_SEED env var (the private "
                  "sweep seed). Never commit or log the raw seed.", file=sys.stderr)
            return 2
        seed = int(raw_seed)
        if seed < 2**32:
            print("WARNING: MINIBENCH_SEED < 2^32 is brute-forceable against the "
                  "published seed_sha256 — use secrets.randbits(63) so the private "
                  "split stays private.", file=sys.stderr)
        tasks = minibench_gen.generate_tasks(seed, args.per_category, suite=args.generate)
        suite = minibench_gen.SUITES[args.generate]["name"]
        # Gate: every generated task must grade its own gold answer as a pass,
        # or a generator/grader drift bug on this fresh seed would silently
        # misgrade every model in the sweep.
        bad = gold_self_check(tasks)
        if bad:
            print(f"ERROR: gold self-check failed for {len(bad)} task(s): {bad}. "
                  "Refusing to run — generator and grader disagree on this seed.",
                  file=sys.stderr)
            return 2
    else:
        suite, tasks = load_tasks(args.tasks)

    # minibench suites are single-model, raw-prompt evals by contract: no MoA
    # aggregation, no system prompt — otherwise scores measure the harness.
    if suite.startswith("minibench") and not config.single:
        print(f"ERROR: suite '{suite}' only accepts single-model runs (--model). "
              "MoA configs add system prompts/aggregation and are not comparable.",
              file=sys.stderr)
        return 2

    if args.dry_run:
        results = run_suite(config, tasks, trials=args.trials, model=None, stub=StubModel())
    else:
        client = OpenAICompatClient(provider=args.provider)
        if client.api_key in (None, "ollama") and args.provider == "openrouter":
            print("ERROR: no OPENROUTER_API_KEY set. Use --dry-run for an offline smoke test.",
                  file=sys.stderr)
            return 2
        model = MoAModel(config, client)
        results = run_suite(config, tasks, trials=args.trials, model=model)

    summary = summarize(config, suite, args.trials, results)
    provenance = build_provenance(seed=seed, is_private_split=args.generate is not None)

    if args.generate:
        # Grader detail strings embed the gold answer ("got 3, expected 7",
        # "key=x != y", pytest assert tails) — even on PASSING trials. Writing
        # them for a PRIVATE split would leak the golds to disk, defeating the
        # whole point of an uncommitted seed. Redact to a non-leaking tag; the
        # pass/score fields are all a private-run artifact needs.
        for tr in results:
            tr.detail = "pass" if tr.passed else ("infra" if tr.infra_error else "fail")
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "provenance": provenance,
        "summary": summary,
        "trials": [asdict(r) for r in results],
    }

    # Commit results to the repo (not /tmp) so numbers are auditable.
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    if args.out:
        out_path = Path(args.out)
    else:
        # Seed-hash + timestamp so a new sweep can never silently overwrite an
        # earlier one.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        seed_tag = provenance["seed_sha256"][:8] if provenance["seed_sha256"] else (
            "dryrun" if args.dry_run else "devslice"
        )
        out_path = RESULTS_DIR / f"{config.name}-{suite}-{seed_tag}-{stamp}.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"\nWrote {out_path}")

    if args.publish:
        if summary["n_canary_flags"] > 0:
            print(f"ERROR: {summary['n_canary_flags']} canary-echo trial(s) — this model "
                  "emitted a benchmark canary string (training contamination). "
                  "Refusing to publish; quarantine this run.", file=sys.stderr)
            return 3
        if summary["n_infra_errors"] > 0 and not args.allow_infra_errors:
            print(f"ERROR: {summary['n_infra_errors']} infra-error trial(s). Refusing to "
                  "publish a partial run — rerun, or pass --allow-infra-errors.",
                  file=sys.stderr)
            return 3
        submit = to_agent_run_submit(summary, results, provider=args.provider,
                                     provenance=provenance)
        published = publish_run(args.publish, submit)
        print(f"Published run_id={published.get('run_id')} to {args.publish}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
