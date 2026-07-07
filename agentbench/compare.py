"""Pairwise significance for ranking claims: no p-value, no ordering.

A leaderboard delta is a CLAIM, and at minibench scale (tens of tasks) most
deltas are noise. This CLI takes >=2 results JSONs from the SAME sweep,
verifies they are actually comparable (same suite, seed hash, grader version,
decoding, task set), and runs an exact McNemar test on paired (task, trial)
outcomes plus task-bootstrap CIs. A > B is only claimed at p < ALPHA;
everything else is reported as indistinguishable.

Usage:
    python -m agentbench.compare agentbench/results/a.json agentbench/results/b.json [...]
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any

from agentbench.stats import bootstrap_ci_by_task, mcnemar_exact

ALPHA = 0.05

# Fields that must match across runs for a comparison to mean anything.
_COMPARABILITY_KEYS = ("suite", "grader_version", "decoding")


class ComparabilityError(ValueError):
    """The runs differ in a way that makes their scores incommensurable."""


def load_run(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("dry_run"):
        raise ComparabilityError(f"{path}: dry-run artifact — scores are meaningless")
    return data


def _model_name(run: dict[str, Any]) -> str:
    models = run["summary"]["moa_config"]["models"]
    return models[0] if len(models) == 1 else run["summary"]["moa_config"]["name"]


def check_comparable(runs: list[dict[str, Any]]) -> None:
    """Refuse to compare runs from different sweeps / graders / task sets."""
    ref = runs[0]
    for run in runs[1:]:
        for key in _COMPARABILITY_KEYS:
            if run["summary"].get(key) != ref["summary"].get(key):
                raise ComparabilityError(
                    f"{_model_name(run)} vs {_model_name(ref)}: '{key}' differs "
                    f"({run['summary'].get(key)!r} != {ref['summary'].get(key)!r})"
                )
        a = (run.get("provenance") or {}).get("seed_sha256")
        b = (ref.get("provenance") or {}).get("seed_sha256")
        if a != b:
            raise ComparabilityError(
                f"{_model_name(run)} vs {_model_name(ref)}: seed_sha256 differs — "
                "not the same sweep"
            )
        keys_a = {(t["task_id"], t["trial"]) for t in run["trials"]}
        keys_b = {(t["task_id"], t["trial"]) for t in ref["trials"]}
        if keys_a != keys_b:
            raise ComparabilityError(
                f"{_model_name(run)} vs {_model_name(ref)}: task/trial sets differ"
            )


# Axis-only categories excluded from binary/McNemar ranking: calibration is
# continuous (Brier), and robustness base/pert are correlated near-duplicates
# that would double-weight one capability and violate McNemar's independent-pair
# assumption. Both are scored on their own axes instead.
_AXIS_ONLY = {"calibration", "robustness"}


def _outcomes(run: dict[str, Any]) -> dict[tuple[str, int], bool]:
    """Paired binary outcomes keyed by (task_id, trial); infra + axis-only excluded."""
    return {
        (t["task_id"], t["trial"]): bool(t["passed"])
        for t in run["trials"]
        if not t.get("infra_error") and t.get("category") not in _AXIS_ONLY
    }


def compare_pair(run_a: dict[str, Any], run_b: dict[str, Any], *, alpha: float = ALPHA) -> dict[str, Any]:
    a, b = _outcomes(run_a), _outcomes(run_b)
    shared = sorted(set(a) & set(b))
    a_only_wins = sum(1 for k in shared if a[k] and not b[k])
    b_only_wins = sum(1 for k in shared if b[k] and not a[k])
    p = mcnemar_exact(a_only_wins, b_only_wins)

    def frac_by_task(outcomes: dict[tuple[str, int], bool]) -> list[float]:
        by_task: dict[str, list[bool]] = {}
        for (task_id, _), passed in outcomes.items():
            by_task.setdefault(task_id, []).append(passed)
        return [sum(v) / len(v) for v in by_task.values()]

    name_a, name_b = _model_name(run_a), _model_name(run_b)
    if p < alpha:
        verdict = f"{name_a} > {name_b}" if a_only_wins > b_only_wins else f"{name_b} > {name_a}"
    else:
        verdict = "indistinguishable"
    return {
        "a": name_a,
        "b": name_b,
        "pass_rate_a": run_a["summary"]["pass_rate"],
        "pass_rate_b": run_b["summary"]["pass_rate"],
        "boot_ci_a": [round(x, 4) for x in bootstrap_ci_by_task(frac_by_task(a))],
        "boot_ci_b": [round(x, 4) for x in bootstrap_ci_by_task(frac_by_task(b))],
        "discordant_a_wins": a_only_wins,
        "discordant_b_wins": b_only_wins,
        "mcnemar_p": round(p, 6),
        "verdict": verdict,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pairwise significance across a sweep.")
    ap.add_argument("results", nargs="+", help=">=2 results JSONs from the SAME sweep")
    ap.add_argument("--alpha", type=float, default=ALPHA)
    args = ap.parse_args(argv)
    if len(args.results) < 2:
        ap.error("need at least 2 results files")

    runs = [load_run(p) for p in args.results]
    try:
        check_comparable(runs)
    except ComparabilityError as e:
        print(f"NOT COMPARABLE: {e}")
        return 2

    reports = [compare_pair(a, b, alpha=args.alpha) for a, b in itertools.combinations(runs, 2)]
    print(json.dumps(reports, indent=2))
    n_sig = sum(1 for r in reports if r["verdict"] != "indistinguishable")
    print(f"\n{n_sig}/{len(reports)} pairs significant at alpha={args.alpha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
