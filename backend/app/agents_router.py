"""Agent-benchmark API — the second product, kept on its own router.

Additive to the hardware endpoints: separate router mounted under
``/api/v1/agents/*`` so the two leaderboards share one app without entangling
their tables or query logic.
"""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, cast, Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import AgentRun, AgentTaskResult, KnownModel
from app.schemas import (
    AgentRunSubmit,
    AgentRunResponse,
    AgentRunDetailResponse,
    AgentTaskResultResponse,
    AgentLeaderboardEntry,
    ModelLeaderboardEntry,
    KnownModelResponse,
)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


def _pareto_frontier(points: list[tuple[int, Optional[Decimal], Decimal]]) -> set[int]:
    """Indices on the accuracy-vs-cost Pareto frontier.

    ``points`` is (index, cost_per_task, pass_rate). Higher pass_rate is better,
    lower cost is better. A point is on the frontier if no other point dominates
    it — i.e. nothing has cost <= its cost AND pass_rate >= its pass_rate with at
    least one strictly better. Runs without a cost can't be placed and are
    excluded (the brief: compare configs at matched cost).
    """
    priced = [(i, c, p) for (i, c, p) in points if c is not None]
    frontier: set[int] = set()
    for i, ci, pi in priced:
        dominated = False
        for j, cj, pj in priced:
            if j == i:
                continue
            if cj <= ci and pj >= pi and (cj < ci or pj > pi):
                dominated = True
                break
        if not dominated:
            frontier.add(i)
    return frontier


# ─── POST /api/v1/agents/runs — ingest a run + its per-task results ────────────

@router.post("/runs", response_model=AgentRunResponse)
async def submit_agent_run(data: AgentRunSubmit, db: AsyncSession = Depends(get_db)):
    run = AgentRun(
        harness=data.harness,
        harness_version=data.harness_version,
        moa_config=data.moa_config,
        benchmark_suite=data.benchmark_suite,
        provider=data.provider,
        model_snapshot_date=data.model_snapshot_date,
        n_tasks=data.n_tasks,
        n_trials=data.n_trials,
        pass_rate=data.pass_rate,
        pass_hat_k=data.pass_hat_k,
        ci95_low=data.ci95_low,
        ci95_high=data.ci95_high,
        cost_usd_per_task=data.cost_usd_per_task,
        latency_p50_ms=data.latency_p50_ms,
        latency_p95_ms=data.latency_p95_ms,
        tokens_in=data.tokens_in,
        tokens_out=data.tokens_out,
    )
    db.add(run)
    await db.flush()  # assign run.run_id before inserting child rows

    for r in data.results:
        db.add(
            AgentTaskResult(
                run_id=run.run_id,
                task_id=r.task_id,
                category=r.category,
                trial=r.trial,
                passed=r.passed,
                score=r.score,
                cost_usd=r.cost_usd,
                latency_ms=r.latency_ms,
                tokens_in=r.tokens_in,
                tokens_out=r.tokens_out,
                raw_output_ref=r.raw_output_ref,
            )
        )
    # A published run marks its models as benchmarked so they leave the
    # "New — not yet benchmarked" panel. Model strings are provider-prefixed
    # ("openrouter/<catalog id>"); the catalog stores (provider, model_id).
    for model_string in (data.moa_config or {}).get("models", []):
        provider, _, model_id = model_string.partition("/")
        if not model_id:
            continue
        km = (
            await db.execute(
                select(KnownModel).where(
                    KnownModel.provider == provider, KnownModel.model_id == model_id
                )
            )
        ).scalars().first()
        if km and not km.benchmarked:
            km.benchmarked = True

    await db.commit()
    await db.refresh(run)
    return run


# ─── GET /api/v1/agents/leaderboard ────────────────────────────────────────────

@router.get("/leaderboard", response_model=list[AgentLeaderboardEntry])
async def agent_leaderboard(
    suite: Optional[str] = None,
    provider: Optional[str] = None,
    sort_by: str = Query("pass_rate", pattern="^(pass_rate|cost_usd_per_task|pass_hat_k)$"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(AgentRun)
    if suite:
        q = q.where(AgentRun.benchmark_suite == suite)
    if provider:
        q = q.where(AgentRun.provider == provider)

    result = await db.execute(q)
    runs = list(result.scalars().all())

    # Pareto frontier is computed over the filtered set (cost vs pass rate).
    points = [(idx, r.cost_usd_per_task, r.pass_rate) for idx, r in enumerate(runs)]
    frontier = _pareto_frontier(points)

    # Sort: pass_rate/pass_hat_k desc (higher better), cost asc (lower better).
    if sort_by == "cost_usd_per_task":
        runs_sorted = sorted(
            enumerate(runs),
            key=lambda t: (t[1].cost_usd_per_task is None, t[1].cost_usd_per_task or 0),
        )
    else:
        runs_sorted = sorted(
            enumerate(runs),
            key=lambda t: getattr(t[1], sort_by) or Decimal(0),
            reverse=True,
        )

    entries = []
    for rank, (idx, r) in enumerate(runs_sorted[:limit], start=1):
        cfg = r.moa_config or {}
        entries.append(
            AgentLeaderboardEntry(
                rank=rank,
                run_id=r.run_id,
                config_name=cfg.get("name"),
                self_moa=bool(cfg.get("self_moa", False)),
                models=list(cfg.get("models", [])),
                model_snapshot_date=r.model_snapshot_date,
                benchmark_suite=r.benchmark_suite,
                provider=r.provider,
                n_tasks=r.n_tasks,
                n_trials=r.n_trials,
                pass_rate=r.pass_rate,
                pass_hat_k=r.pass_hat_k,
                ci95_low=r.ci95_low,
                ci95_high=r.ci95_high,
                cost_usd_per_task=r.cost_usd_per_task,
                latency_p50_ms=r.latency_p50_ms,
                latency_p95_ms=r.latency_p95_ms,
                on_pareto_frontier=idx in frontier,
            )
        )
    return entries


# ─── GET /api/v1/agents/models/leaderboard — model-centric view ────────────────

@router.get("/models/leaderboard", response_model=list[ModelLeaderboardEntry])
async def model_leaderboard(
    suite: Optional[str] = None,
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Best published run per MODEL (not per config): only runs whose config
    touches exactly one model string qualify, so a MoA pipeline never poses as
    a model. Joined against the master catalog for family/license/prices."""
    q = select(AgentRun)
    if suite:
        q = q.where(AgentRun.benchmark_suite == suite)
    runs = list((await db.execute(q)).scalars().all())

    # One model string == model-centric. (Self-MoA also qualifies: same model.)
    single_runs = [r for r in runs if len((r.moa_config or {}).get("models", [])) == 1]

    best: dict[str, AgentRun] = {}
    for r in single_runs:
        key = r.moa_config["models"][0]
        cur = best.get(key)
        if cur is None or (r.pass_rate, -(r.cost_usd_per_task or Decimal(0))) > (
            cur.pass_rate, -(cur.cost_usd_per_task or Decimal(0))
        ):
            best[key] = r

    # Catalog join: preset model strings are "openrouter/<catalog id>".
    catalog_rows = list((await db.execute(select(KnownModel))).scalars().all())
    catalog = {f"{m.provider}/{m.model_id}": m for m in catalog_rows}

    # Per-category pass rates for the chosen runs.
    run_ids = [r.run_id for r in best.values()]
    cat_rates: dict[UUID, dict[str, float]] = {}
    if run_ids:
        rows = await db.execute(
            select(
                AgentTaskResult.run_id,
                AgentTaskResult.category,
                func.avg(cast(AgentTaskResult.passed, Integer)),
            )
            .where(AgentTaskResult.run_id.in_(run_ids))
            .group_by(AgentTaskResult.run_id, AgentTaskResult.category)
        )
        for rid, category, rate in rows:
            cat_rates.setdefault(rid, {})[category or "unknown"] = round(float(rate) * 100, 2)

    ordered = sorted(
        best.items(),
        key=lambda kv: (kv[1].pass_rate, -(kv[1].cost_usd_per_task or Decimal(0))),
        reverse=True,
    )[:limit]
    points = [(i, r.cost_usd_per_task, r.pass_rate) for i, (_, r) in enumerate(ordered)]
    frontier = _pareto_frontier(points)

    entries = []
    for i, (model_string, r) in enumerate(ordered):
        cm = catalog.get(model_string)
        entries.append(
            ModelLeaderboardEntry(
                rank=i + 1,
                model_string=model_string,
                run_id=r.run_id,
                benchmark_suite=r.benchmark_suite,
                provider=r.provider,
                display_name=cm.display_name if cm else None,
                family=cm.family if cm else None,
                license=cm.license if cm else None,
                prompt_price=cm.prompt_price if cm else None,
                completion_price=cm.completion_price if cm else None,
                n_tasks=r.n_tasks,
                n_trials=r.n_trials,
                pass_rate=r.pass_rate,
                pass_hat_k=r.pass_hat_k,
                ci95_low=r.ci95_low,
                ci95_high=r.ci95_high,
                cost_usd_per_task=r.cost_usd_per_task,
                latency_p50_ms=r.latency_p50_ms,
                latency_p95_ms=r.latency_p95_ms,
                submitted_at=r.submitted_at,
                category_pass_rates=cat_rates.get(r.run_id, {}),
                on_pareto_frontier=i in frontier,
            )
        )
    return entries


# ─── GET /api/v1/agents/runs/{run_id} — detail with per-task results ───────────

@router.get("/runs/{run_id}", response_model=AgentRunDetailResponse)
async def get_agent_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).where(AgentRun.run_id == run_id))
    run = result.scalars().first()
    if not run:
        raise HTTPException(404, "Agent run not found")

    tr = await db.execute(
        select(AgentTaskResult)
        .where(AgentTaskResult.run_id == run_id)
        .order_by(AgentTaskResult.task_id, AgentTaskResult.trial)
    )
    task_results = [AgentTaskResultResponse.model_validate(t) for t in tr.scalars().all()]

    payload = AgentRunResponse.model_validate(run).model_dump()
    return AgentRunDetailResponse(**payload, results=task_results)


# ─── GET /api/v1/agents/models/new — models tracked but not yet benchmarked ────

@router.get("/models/new", response_model=list[KnownModelResponse])
async def new_models(
    provider: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    q = select(KnownModel).where(KnownModel.benchmarked.is_(False))
    if provider:
        q = q.where(KnownModel.provider == provider)
    q = q.order_by(KnownModel.first_seen.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())
