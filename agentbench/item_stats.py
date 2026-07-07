"""Item-level discrimination audit across a sweep's result files.

A benchmark item earns its slot by SEPARATING models. This tool reads the
results JSONs of one sweep (same seed, same tasks — validated by compare.py's
rules) and reports, per task: pass fraction across models, ceiling/floor flags,
and the point-biserial correlation between item score and each model's total.

Pruning policy (scientific, ordering-blind): drop items by DISCRIMINATION
ONLY — all-pass ceiling items, all-fail floor items, and near-zero/negative
point-biserial items. NEVER prune by which model an item favors; that is
benchmark tuning, the thing this repo exists to avoid. A hard-suite ceiling
tie across top models is a finding ("design hard-v2"), not a grading problem.

Usage:
    python -m agentbench.item_stats agentbench/results/sweep-*.json
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

LOW_DISCRIMINATION = 0.1


def _model_name(run: dict[str, Any]) -> str:
    models = run["summary"]["moa_config"]["models"]
    return models[0] if len(models) == 1 else run["summary"]["moa_config"]["name"]


def _item_scores(run: dict[str, Any]) -> dict[str, float]:
    """Per-task pass fraction for one model (infra trials excluded)."""
    by_task: dict[str, list[bool]] = {}
    for t in run["trials"]:
        if t.get("infra_error"):
            continue
        by_task.setdefault(t["task_id"], []).append(bool(t["passed"]))
    return {task: sum(v) / len(v) for task, v in by_task.items() if v}


def point_biserial(item: list[float], totals: list[float]) -> float:
    """Pearson correlation between an item's score and the model total.

    Positive = stronger models do better on this item (discriminates in the
    right direction). Near zero = noise slot. Negative = the item punishes
    stronger models — usually a broken oracle; inspect it.
    """
    n = len(item)
    if n < 2:
        return 0.0
    mi, mt = sum(item) / n, sum(totals) / n
    cov = sum((a - mi) * (b - mt) for a, b in zip(item, totals))
    var_i = sum((a - mi) ** 2 for a in item)
    var_t = sum((b - mt) ** 2 for b in totals)
    if var_i == 0 or var_t == 0:
        return 0.0
    return cov / math.sqrt(var_i * var_t)


def audit(runs: list[dict[str, Any]]) -> dict[str, Any]:
    per_model = {_model_name(r): _item_scores(r) for r in runs}
    models = sorted(per_model)
    tasks = sorted(set().union(*(set(s) for s in per_model.values())))
    totals = {m: sum(per_model[m].values()) / max(1, len(per_model[m])) for m in models}

    items = []
    for task in tasks:
        # Only models that actually have a scored result for this task. A model
        # whose trials were all infra-excluded is ABSENT, not a 0.0 — fabricating
        # a zero would corrupt mean_pass and point_biserial (a provider rate-limit
        # would masquerade as a capability floor).
        present = [m for m in models if task in per_model[m]]
        scores = [per_model[m][task] for m in present]
        item_totals = [totals[m] for m in present]
        missing = len(models) - len(present)
        mean = sum(scores) / len(scores) if scores else 0.0
        r_pb = point_biserial(scores, item_totals)
        flags = []
        if scores and all(s == 1.0 for s in scores):
            flags.append("ceiling")
        elif scores and all(s == 0.0 for s in scores):
            flags.append("floor")
        elif abs(r_pb) < LOW_DISCRIMINATION:
            flags.append("low-discrimination")
        if r_pb < -LOW_DISCRIMINATION:
            flags.append("negative-discrimination")  # inspect the oracle
        if missing:
            flags.append(f"missing-{missing}-models")  # incomplete coverage, interpret with care
        items.append({
            "task_id": task,
            "n_models_scored": len(present),
            "mean_pass": round(mean, 4),
            "point_biserial": round(r_pb, 4),
            "flags": flags,
        })

    prune_candidates = [i["task_id"] for i in items if i["flags"]]
    return {
        "n_models": len(models),
        "models": models,
        "items": items,
        "prune_candidates": prune_candidates,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Item discrimination audit for a sweep.")
    ap.add_argument("results", nargs="+", help="results JSONs from one sweep")
    args = ap.parse_args(argv)
    runs = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.results]
    if len(runs) < 3:
        print("WARNING: point-biserial with <3 models is nearly meaningless; "
              "run the audit on the full sweep.")
    report = audit(runs)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
