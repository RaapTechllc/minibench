"""Presentation helpers for Real-Work Agent Cabinet rows.

``default_view`` is the public scorecard (completion, category breakdown, cost,
latency). ``technician_view`` nests provenance and reliability; it is never
flattened onto the default item.

Refuse reasons live in ``agentbench.agent_cabinet`` — this module does not
reimplement publication or comparability gates.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from agentbench.agent_cabinet import (  # noqa: E402
    COMPARABILITY_FIELDS,
    REQUIRED_PROVENANCE_KEYS,
)


CHANGED_VARIABLE_CANDIDATES = ("model_route", "harness")
INDEPENDENT_VARIABLES_NOTE = (
    "Independent variables that may differ across listed runs are model_route "
    "and harness. Task snapshot, tools, limits, verification, and trials stay "
    "in held_constant."
)


def _pct(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value) * 100.0, 2)


def completion_from_artifact(artifact: dict[str, Any]) -> float:
    """Stored/display completion is 0–100 (artifact ``summary.pass_rate`` × 100)."""
    rate = (artifact.get("summary") or {}).get("pass_rate") or 0.0
    return round(float(rate) * 100.0, 2)


def category_completion_from_trials(trials: list[dict[str, Any]] | None) -> dict[str, float]:
    """Average of ``passed`` grouped by raw trial category (not Arcade labels)."""
    grouped: dict[str, list[bool]] = {}
    for trial in trials or []:
        category = trial.get("category") or "unknown"
        grouped.setdefault(category, []).append(bool(trial.get("passed")))
    return {
        category: round(100.0 * sum(flags) / len(flags), 2)
        for category, flags in grouped.items()
    }


def canonical_budgets(budgets: Any) -> str:
    return json.dumps(budgets if budgets is not None else {}, sort_keys=True, separators=(",", ":"), allow_nan=False)


def changed_variables_note(
    left: dict[str, Any] | None = None,
    right: dict[str, Any] | None = None,
) -> str:
    """Short note: which of model_route / harness differ, or the contract default."""
    if left is None or right is None:
        return INDEPENDENT_VARIABLES_NOTE
    left_prov = left.get("provenance") or {}
    right_prov = right.get("provenance") or {}
    differed = [
        field
        for field in CHANGED_VARIABLE_CANDIDATES
        if left_prov.get(field) != right_prov.get(field)
    ]
    if not differed:
        return "model_route and harness match on this pair."
    if len(differed) == 1:
        return f"Changed variable: {differed[0]}."
    return "Changed variables: " + " and ".join(differed) + "."


def default_view(row: dict[str, Any]) -> dict[str, Any]:
    """Default scorecard: completion, category completion, cost, latency."""
    return {
        "run_id": row["run_id"],
        "submitted_at": row.get("submitted_at"),
        "suite": row.get("suite"),
        "model_route": row.get("model_route"),
        "harness": row.get("harness"),
        "harness_version": row.get("harness_version"),
        "completion": float(row["completion"]),
        "pass_rate": float(row["completion"]),
        "category_completion": dict(row.get("category_completion") or {}),
        "cost_usd_per_task": (
            None if row.get("cost_usd_per_task") is None else float(row["cost_usd_per_task"])
        ),
        "latency_p50_ms": row.get("latency_p50_ms"),
        "private_split": bool(row.get("private_split")),
    }


def technician_view(row: dict[str, Any]) -> dict[str, Any]:
    """Nested technician object: required provenance plus reliability diagnostics."""
    artifact = row.get("artifact") or {}
    provenance = artifact.get("provenance") or row.get("provenance") or {}
    summary = artifact.get("summary") or row.get("summary") or {}
    ci = summary.get("pass_rate_ci95") or [None, None]
    technician = {key: provenance.get(key) for key in REQUIRED_PROVENANCE_KEYS}
    technician.update(
        {
            "false_verification_rate": summary.get("false_verification_rate"),
            "regression_rate": summary.get("regression_rate"),
            "termination_reasons": summary.get("termination_reasons") or {},
            "pass_hat_k": _pct(summary.get("pass_hat_k")),
            "ci95_low": _pct(ci[0]) if len(ci) > 0 else None,
            "ci95_high": _pct(ci[1]) if len(ci) > 1 else None,
            "pass_rate_ci95": [_pct(item) for item in (summary.get("pass_rate_ci95") or [])],
            "pass_rate_ci95_boot": [
                _pct(item) for item in (summary.get("pass_rate_ci95_boot") or [])
            ],
            "budgets": provenance.get("budgets"),
            "trials": artifact.get("trials") or [],
        }
    )
    return technician


def detail_view(row: dict[str, Any]) -> dict[str, Any]:
    """Default view plus nested technician, held_constant, and changed-variables note."""
    payload = default_view(row)
    payload["technician"] = technician_view(row)
    payload["held_constant"] = list(COMPARABILITY_FIELDS)
    payload["changed_variables"] = changed_variables_note()
    return payload


def list_item_view(row: dict[str, Any], *, technician: bool = False) -> dict[str, Any]:
    payload = default_view(row)
    if technician:
        payload["technician"] = technician_view(row)
    return payload
