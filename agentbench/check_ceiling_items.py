"""Release gate for new-season ceiling items.

Run this on a comparable frontier sweep before publishing a new cabinet season.
It wraps ``item_stats.audit`` and exits non-zero when any task is at or above the
ceiling threshold (90% pass by default).

Usage:
    python -m agentbench.check_ceiling_items agentbench/results/sweep-*.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agentbench.compare import ComparabilityError, check_comparable, load_run
from agentbench.item_stats import audit

DEFAULT_CEILING_THRESHOLD = 0.9
DEFAULT_MIN_MODELS = 3


def ceiling_items(report: dict[str, Any], *, threshold: float = DEFAULT_CEILING_THRESHOLD) -> list[dict[str, Any]]:
    """Return audited items whose scored model pass fraction hits the ceiling."""
    return [
        item
        for item in report["items"]
        if item["n_models_scored"] > 0 and item["mean_pass"] >= threshold
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fail when a season sweep contains ceiling items.")
    ap.add_argument("results", nargs="+", help="results JSONs from one comparable season sweep")
    ap.add_argument(
        "--ceiling-threshold",
        type=float,
        default=DEFAULT_CEILING_THRESHOLD,
        help="mean per-item pass fraction that blocks publishing (default: 0.9)",
    )
    ap.add_argument(
        "--min-models",
        type=int,
        default=DEFAULT_MIN_MODELS,
        help="minimum number of models required for the gate to be meaningful (default: 3)",
    )
    ap.add_argument("--json", action="store_true", help="print the full item_stats audit JSON")
    args = ap.parse_args(argv)

    if not 0 < args.ceiling_threshold <= 1:
        ap.error("--ceiling-threshold must be in (0, 1]")

    runs = [load_run(Path(p)) for p in args.results]
    if len(runs) < args.min_models:
        print(
            f"NOT ENOUGH MODELS: got {len(runs)}, need at least {args.min_models} "
            "for a season ceiling audit"
        )
        return 2
    try:
        check_comparable(runs)
    except ComparabilityError as e:
        print(f"NOT COMPARABLE: {e}")
        return 2

    report = audit(runs)
    blockers = ceiling_items(report, threshold=args.ceiling_threshold)
    if args.json:
        print(json.dumps(report, indent=2))

    if blockers:
        ids = ", ".join(item["task_id"] for item in blockers)
        print(
            f"CEILING ITEMS BLOCK PUBLISH: {len(blockers)} item(s) at "
            f">={args.ceiling_threshold:.0%} pass: {ids}"
        )
        print("Resolve by pruning, rewriting, or moving the season target before publishing.")
        return 1

    print(f"OK: no items at >={args.ceiling_threshold:.0%} pass across {report['n_models']} models.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
