"""Arena-style model catalog and voting API.

MiniBench started as a hardware benchmark. This router adds the missing public
LLM-ranking surface: model rows from external leaderboard references plus
anonymous task-specific preference votes.
"""
import hashlib
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ArenaModel, ArenaVote
from app.schemas import ArenaModelResponse, ArenaVoteResponse, ArenaVoteSubmit

router = APIRouter(prefix="/api/v1/arena", tags=["arena"])


async def _vote_count(db: AsyncSession, task: str, model_id: str) -> int:
    result = await db.execute(
        select(func.count(ArenaVote.id)).where(
            ArenaVote.task == task,
            ArenaVote.model_id == model_id,
        )
    )
    return int(result.scalar() or 0)


@router.get("/models", response_model=list[ArenaModelResponse])
async def arena_models(task: str | None = None, db: AsyncSession = Depends(get_db)):
    q = select(ArenaModel)
    if task:
        # task_tags is JSONB; .contains([task]) compiles to @> on Postgres.
        q = q.where(ArenaModel.task_tags.contains([task]))
    q = q.order_by(ArenaModel.arena_rank.asc().nullslast(), ArenaModel.display_name.asc())
    rows = list((await db.execute(q)).scalars().all())

    counts: dict[str, int] = {}
    if rows:
        vote_q = select(ArenaVote.model_id, func.count(ArenaVote.id)).group_by(ArenaVote.model_id)
        if task:
            vote_q = vote_q.where(ArenaVote.task == task)
        counts = {model_id: int(count) for model_id, count in (await db.execute(vote_q)).all()}

    return [
        ArenaModelResponse.model_validate(row).model_copy(update={"vote_count": counts.get(row.model_id, 0)})
        for row in rows
    ]


@router.post("/votes", response_model=ArenaVoteResponse)
async def vote(payload: ArenaVoteSubmit, request: Request, db: AsyncSession = Depends(get_db)):
    model = (
        await db.execute(select(ArenaModel).where(ArenaModel.model_id == payload.model_id))
    ).scalars().first()
    if not model:
        raise HTTPException(404, "Arena model not found")
    if payload.task not in (model.task_tags or []):
        raise HTTPException(400, "Model is not listed for that task")

    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]
    accepted = True
    db.add(ArenaVote(task=payload.task, model_id=payload.model_id, ip_hash=ip_hash))
    try:
        await db.commit()
    except IntegrityError:
        accepted = False
        await db.rollback()

    return ArenaVoteResponse(
        task=payload.task,
        model_id=payload.model_id,
        vote_count=await _vote_count(db, payload.task, payload.model_id),
        accepted=accepted,
    )
