"""Real-Work Agent Cabinet read + ingest API.

Mounted at ``/api/v1/agent-cabinet``. Accepts the artifact JSON
``build_agent_artifact`` already emits. Publication and comparability reuse
``agentbench.agent_cabinet``; this router does not reimplement refuse reasons.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent_cabinet_present import (
    canonical_budgets,
    category_completion_from_trials,
    changed_variables_note,
    completion_from_artifact,
    detail_view,
    list_item_view,
)
from app.database import get_db
from app.models import AgentCabinetRun, AgentCabinetTaskResult, AgentRun

from agentbench.agent_cabinet import (  # path primed by agent_cabinet_present
    AGENT_CABINET_POLICY,
    COMPARABILITY_FIELDS,
    comparability_receipt,
    is_agent_cabinet_artifact,
    publication_receipt,
)
from agentbench.compare import compare_pair

router = APIRouter(prefix="/api/v1/agent-cabinet", tags=["agent-cabinet"])

_EVALUATION_TYPE_MISMATCH = {
    "policy_version": AGENT_CABINET_POLICY,
    "comparable": False,
    "publishable": False,
    "failing_fields": ["evaluation_type"],
    "reasons": ["evaluation_type mismatch"],
}


def _row_dict(run: AgentCabinetRun) -> dict[str, Any]:
    return {
        "run_id": str(run.run_id),
        "submitted_at": run.submitted_at,
        "suite": run.suite,
        "model_route": run.model_route,
        "harness": run.harness,
        "harness_version": run.harness_version,
        "completion": run.completion,
        "category_completion": run.category_completion or {},
        "cost_usd_per_task": run.cost_usd_per_task,
        "latency_p50_ms": run.latency_p50_ms,
        "private_split": run.private_split,
        "provenance": run.provenance,
        "summary": run.summary,
        "artifact": run.artifact,
    }


def _identity_value(run: AgentCabinetRun, field: str) -> Any:
    provenance = run.provenance or {}
    if field == "budgets":
        return canonical_budgets(provenance.get("budgets"))
    if field == "grader_version":
        return provenance.get("grader_version", run.grader_version)
    return provenance.get(field)


def _full_key(run: AgentCabinetRun) -> tuple[Any, ...]:
    """One model/harness result under the exact pairwise-comparison identity."""
    return (
        run.model_route,
        *(_identity_value(run, field) for field in COMPARABILITY_FIELDS),
    )


def _supersession_key(run: AgentCabinetRun) -> tuple[Any, ...]:
    return _full_key(run)[:-1]


def _latest_tuple(run: AgentCabinetRun) -> tuple[Any, str]:
    return (run.submitted_at, str(run.run_id))


def select_representative_runs(runs: list[AgentCabinetRun]) -> list[AgentCabinetRun]:
    """Latest valid run per exact identity; private supersedes matching public."""
    by_full: dict[tuple, AgentCabinetRun] = {}
    for run in runs:
        key = _full_key(run)
        current = by_full.get(key)
        if current is None or _latest_tuple(run) > _latest_tuple(current):
            by_full[key] = run

    grouped: dict[tuple, list[AgentCabinetRun]] = {}
    for run in by_full.values():
        grouped.setdefault(_supersession_key(run), []).append(run)

    best: list[AgentCabinetRun] = []
    for group in grouped.values():
        privates = [run for run in group if run.private_split]
        best.extend(privates if privates else group)
    return sorted(best, key=_latest_tuple, reverse=True)


def _latency_p50_ms(summary: dict[str, Any]) -> int | None:
    value = summary.get("latency_p50_ms")
    if value is None:
        return None
    return int(round(float(value)))


# ─── POST /api/v1/agent-cabinet/runs ──────────────────────────────────────────


@router.post("/runs")
async def submit_agent_cabinet_run(
    artifact: dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    if not is_agent_cabinet_artifact(artifact):
        raise HTTPException(status_code=422, detail=_EVALUATION_TYPE_MISMATCH)

    receipt = publication_receipt(artifact)
    if not receipt["publishable"]:
        raise HTTPException(status_code=422, detail=receipt)

    provenance = artifact.get("provenance") or {}
    summary = artifact.get("summary") or {}
    trials = [trial for trial in (artifact.get("trials") or []) if isinstance(trial, dict)]
    completion = completion_from_artifact(artifact)
    budgets = provenance.get("budgets") or {}

    run = AgentCabinetRun(
        suite=provenance.get("suite") or summary.get("suite"),
        model_route=provenance["model_route"],
        harness=provenance["harness"],
        harness_version=str(provenance["harness_version"]),
        tool_contract_sha256=provenance["tool_contract_sha256"],
        fixture_digest=provenance["fixture_digest"],
        budgets=budgets,
        budgets_canonical=canonical_budgets(budgets),
        grader_version=str(provenance.get("grader_version") or summary.get("grader_version")),
        private_split=bool(provenance.get("private_split")),
        private_split_id=provenance["private_split_id"],
        completion=completion,
        pass_rate=completion,
        cost_usd_per_task=summary.get("cost_usd_per_task"),
        latency_p50_ms=_latency_p50_ms(summary),
        category_completion=category_completion_from_trials(trials),
        provenance=provenance,
        summary=summary,
        artifact=artifact,
        publication_receipt=receipt,
    )
    db.add(run)
    await db.flush()

    for trial in trials:
        db.add(
            AgentCabinetTaskResult(
                run_id=run.run_id,
                task_id=trial.get("task_id") or "",
                category=trial.get("category"),
                trial=trial.get("trial"),
                passed=bool(trial.get("passed")),
                outcome=trial.get("outcome"),
                trial_payload=trial,
            )
        )

    await db.commit()
    await db.refresh(run)
    return detail_view(_row_dict(run))


# ─── GET /api/v1/agent-cabinet/runs ───────────────────────────────────────────


@router.get("/runs")
async def list_agent_cabinet_runs(
    view: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if view not in (None, "technician"):
        raise HTTPException(status_code=400, detail="view must be technician when set")
    result = await db.execute(select(AgentCabinetRun))
    best = select_representative_runs(list(result.scalars().all()))
    include_technician = view == "technician"
    return [list_item_view(_row_dict(run), technician=include_technician) for run in best]


# ─── GET /api/v1/agent-cabinet/runs/{run_id} ──────────────────────────────────


@router.get("/runs/{run_id}")
async def get_agent_cabinet_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    run = await _load_cabinet_run(run_id, db, missing="404")
    return detail_view(_row_dict(run))


# ─── GET /api/v1/agent-cabinet/compare ────────────────────────────────────────


@router.get("/compare")
async def compare_agent_cabinet_runs(
    a: UUID = Query(...),
    b: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    run_a = await _load_cabinet_run(a, db, missing="cross-cabinet")
    run_b = await _load_cabinet_run(b, db, missing="cross-cabinet")
    artifact_a = run_a.artifact
    artifact_b = run_b.artifact
    if not is_agent_cabinet_artifact(artifact_a) or not is_agent_cabinet_artifact(artifact_b):
        raise HTTPException(status_code=409, detail=_EVALUATION_TYPE_MISMATCH)

    receipt = comparability_receipt(artifact_a, artifact_b)
    if not receipt["comparable"]:
        raise HTTPException(status_code=409, detail=receipt)

    comparison = compare_pair(artifact_a, artifact_b)
    return {
        "a": detail_view(_row_dict(run_a)),
        "b": detail_view(_row_dict(run_b)),
        "receipt": receipt,
        "comparison": comparison,
        "held_constant": list(COMPARABILITY_FIELDS),
        "changed_variables": changed_variables_note(artifact_a, artifact_b),
    }


async def _load_cabinet_run(
    run_id: UUID,
    db: AsyncSession,
    *,
    missing: str,
) -> AgentCabinetRun:
    result = await db.execute(select(AgentCabinetRun).where(AgentCabinetRun.run_id == run_id))
    run = result.scalars().first()
    if run:
        return run
    if missing == "cross-cabinet":
        solo = await db.execute(select(AgentRun).where(AgentRun.run_id == run_id))
        if solo.scalars().first():
            raise HTTPException(status_code=409, detail=_EVALUATION_TYPE_MISMATCH)
    raise HTTPException(status_code=404, detail="Agent cabinet run not found")
