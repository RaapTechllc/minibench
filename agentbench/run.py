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
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentbench.config import load_moa_config, MoAConfig
from agentbench.client import OpenAICompatClient
from agentbench.grading import grade
from agentbench.moa import MoAModel, MoAResult
from agentbench.stats import pass_rate, pass_hat_k, wilson_ci, percentile
from agentbench.resources import RESULTS_DIR


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
            if stub is not None:
                out = stub.generate_for(task["id"])
            else:
                assert model is not None
                out = model.generate(task["prompt"])
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
                )
            )
    return results


def summarize(config: MoAConfig, suite: str, trials: int, results: list[TrialResult]) -> dict[str, Any]:
    total = len(results)
    passes = sum(1 for r in results if r.passed)
    # Per-task pass counts for pass^k.
    by_task: dict[str, list[TrialResult]] = {}
    for r in results:
        by_task.setdefault(r.task_id, []).append(r)
    per_task_passes = [sum(1 for r in rs if r.passed) for rs in by_task.values()]
    per_task_trials = [len(rs) for rs in by_task.values()]

    latencies = [float(r.latency_ms) for r in results]
    costs = [r.cost_usd for r in results if r.cost_usd is not None]
    total_cost = sum(costs) if costs else None
    ci_lo, ci_hi = wilson_ci(passes, total)

    return {
        "suite": suite,
        "moa_config": {
            "name": config.name,
            "self_moa": config.self_moa,
            "models": config.models,
        },
        "n_tasks": len(by_task),
        "n_trials": trials,
        "pass_rate": round(pass_rate(passes, total), 4),
        "pass_rate_ci95": [round(ci_lo, 4), round(ci_hi, 4)],
        "pass_hat_k": round(pass_hat_k(per_task_passes, per_task_trials, k=trials), 4),
        "cost_usd_total": round(total_cost, 6) if total_cost is not None else None,
        "cost_usd_per_task": round(total_cost / len(by_task), 6) if total_cost is not None and by_task else None,
        "latency_p50_ms": round(percentile(latencies, 50), 1),
        "latency_p95_ms": round(percentile(latencies, 95), 1),
    }


def main(argv: list[str] | None = None) -> int:
    _load_env_files()
    ap = argparse.ArgumentParser(description="Run a MoA config against a task suite.")
    ap.add_argument("--config", required=True)
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--provider", default="openrouter")
    ap.add_argument("--dry-run", action="store_true", help="offline stub, no network/keys")
    ap.add_argument("--out", default=None, help="results JSON path (default: agentbench/results/<ts>.json)")
    args = ap.parse_args(argv)

    config = load_moa_config(args.config)
    suite, tasks = load_tasks(args.tasks)

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
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": args.dry_run,
        "summary": summary,
        "trials": [asdict(r) for r in results],
    }

    # Commit results to the repo (not /tmp) so numbers are auditable.
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else RESULTS_DIR / (
        f"{config.name}-{suite}-{'dryrun' if args.dry_run else 'live'}.json"
    )
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2))
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
