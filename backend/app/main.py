import hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import select, func, distinct, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, engine, Base
from app.models import Benchmark, HardwareSpec, ModelQuality, ReferenceProfile
from app.schemas import (
    BenchmarkSubmit,
    BenchmarkResponse,
    HardwareSpecResponse,
    ModelQualityResponse,
    ReferenceProfileResponse,
    LeaderboardEntry,
    CompareResponse,
    StatsResponse,
)
from app.seed import run_seed
from app.agents_router import router as agents_router
from app.agent_cabinet_router import router as agent_cabinet_router
from app.openrouter_board import router as openrouter_board_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (async engine), then seed reference + sample data (sync).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        run_seed()
    except Exception as e:  # pragma: no cover - seeding is best-effort
        print(f"Seed warning: {e}")
    yield
    # Release pooled connections on shutdown (also lets the test suite rebind
    # the engine to a fresh event loop between cases).
    await engine.dispose()


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="MiniBench API",
    version="1.0.0",
    description="AI model and agent benchmark evidence, with legacy hardware reference data",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

# Agent-benchmark product (additive; separate router + tables).
app.include_router(agents_router)
# Real-Work Agent Cabinet (additive; never mixed into Solo/MoA or hardware).
app.include_router(agent_cabinet_router)
# Cached OpenRouter Usage Board (CC BY 4.0 republish). No recommend, no live hop.
app.include_router(openrouter_board_router)


def compute_hei(tokens_per_second: Decimal, model_quality_score: Optional[Decimal], hardware_price_usd: Optional[Decimal]) -> Optional[float]:
    """Hardware Efficiency Index = (t/s × model_quality) / price"""
    if model_quality_score and hardware_price_usd and hardware_price_usd > 0:
        return round(float(tokens_per_second * model_quality_score) / float(hardware_price_usd), 4)
    return None


def benchmark_to_response(b: Benchmark) -> BenchmarkResponse:
    hei = compute_hei(b.tokens_per_second, b.model_quality_score, b.hardware_price_usd)
    return BenchmarkResponse(
        id=b.id, submission_id=b.submission_id, submitted_at=b.submitted_at,
        cpu_model=b.cpu_model, cpu_cores=b.cpu_cores, cpu_threads=b.cpu_threads,
        gpu_model=b.gpu_model, igpu_model=b.igpu_model,
        total_ram_gb=b.total_ram_gb, vram_gb=b.vram_gb,
        memory_type=b.memory_type, memory_bandwidth_gbs=b.memory_bandwidth_gbs,
        system_type=b.system_type, hardware_price_usd=b.hardware_price_usd,
        os=b.os, inference_engine=b.inference_engine, engine_version=b.engine_version,
        model_name=b.model_name, model_params_b=b.model_params_b, quantization=b.quantization,
        tokens_per_second=b.tokens_per_second, time_to_first_token=b.time_to_first_token,
        watts_per_token=b.watts_per_token, total_power_watts=b.total_power_watts,
        prompt_tokens=b.prompt_tokens, completion_tokens=b.completion_tokens,
        test_duration_secs=b.test_duration_secs,
        model_quality_score=b.model_quality_score, quality_source=b.quality_source,
        fingerprint=b.fingerprint, client_version=b.client_version, ip_hash=b.ip_hash,
        thermal_setting=b.thermal_setting, ambient_temp_c=b.ambient_temp_c,
        hei=hei,
    )


# ─── Health ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "minibench-api"}


# ─── POST /api/v1/submit ─────────────────────────────────────────────────────

@app.post("/api/v1/submit", response_model=BenchmarkResponse)
@limiter.limit("10/hour")
async def submit_benchmark(data: BenchmarkSubmit, request: Request, db: AsyncSession = Depends(get_db)):
    # Validate token count
    if data.prompt_tokens + data.completion_tokens < 100:
        raise HTTPException(400, "prompt_tokens + completion_tokens must be >= 100")

    # Compute IP hash
    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]

    # Compute fingerprint if not provided
    fingerprint = data.fingerprint
    if not fingerprint:
        fp_str = f"{data.cpu_model}{data.gpu_model}{data.total_ram_gb}{data.os}{data.inference_engine}{data.model_name}{data.quantization}"
        fingerprint = hashlib.sha256(fp_str.encode()).hexdigest()[:16]

    # Duplicate fingerprint within 1 hour
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    result = await db.execute(
        select(Benchmark).where(
            and_(Benchmark.fingerprint == fingerprint, Benchmark.submitted_at >= one_hour_ago)
        )
    )
    if result.scalars().first():
        raise HTTPException(429, "Duplicate submission — same hardware/model combo submitted within the last hour")

    # Auto-lookup model quality from the reference table (substring match).
    mq_result = await db.execute(
        select(ModelQuality).where(ModelQuality.model_variant.ilike(f"%{data.model_name}%"))
    )
    mq = mq_result.scalars().first()
    quality_score = mq.mmlu_score if mq else None
    quality_source = "mmlu" if mq else None

    benchmark = Benchmark(
        cpu_model=data.cpu_model,
        cpu_cores=data.cpu_cores,
        cpu_threads=data.cpu_threads,
        gpu_model=data.gpu_model,
        igpu_model=data.igpu_model,
        total_ram_gb=data.total_ram_gb,
        vram_gb=data.vram_gb,
        memory_type=data.memory_type,
        memory_bandwidth_gbs=data.memory_bandwidth_gbs,
        system_type=data.system_type,
        hardware_price_usd=data.hardware_price_usd,
        os=data.os,
        inference_engine=data.inference_engine,
        engine_version=data.engine_version,
        model_name=data.model_name,
        model_params_b=data.model_params_b,
        quantization=data.quantization,
        tokens_per_second=data.tokens_per_second,
        time_to_first_token=data.time_to_first_token,
        watts_per_token=data.watts_per_token,
        total_power_watts=data.total_power_watts,
        prompt_tokens=data.prompt_tokens,
        completion_tokens=data.completion_tokens,
        test_duration_secs=data.test_duration_secs,
        model_quality_score=quality_score,
        quality_source=quality_source,
        fingerprint=fingerprint,
        client_version=data.client_version,
        ip_hash=ip_hash,
        thermal_setting=data.thermal_setting,
        ambient_temp_c=data.ambient_temp_c,
    )
    db.add(benchmark)
    await db.commit()
    await db.refresh(benchmark)
    return benchmark_to_response(benchmark)


# ─── GET /api/v1/benchmarks ──────────────────────────────────────────────────

@app.get("/api/v1/benchmarks", response_model=list[BenchmarkResponse])
async def list_benchmarks(
    response: Response,
    model: Optional[str] = None,
    quantization: Optional[str] = None,
    system_type: Optional[str] = None,
    engine: Optional[str] = None,
    sort_by: str = Query("tokens_per_second", pattern="^(tokens_per_second|time_to_first_token|submitted_at|memory_bandwidth_gbs)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if model:
        conditions.append(Benchmark.model_name.ilike(f"%{model}%"))
    if quantization:
        conditions.append(Benchmark.quantization == quantization)
    if system_type:
        conditions.append(Benchmark.system_type.ilike(f"%{system_type}%"))
    if engine:
        conditions.append(Benchmark.inference_engine.ilike(f"%{engine}%"))

    total = await db.scalar(
        select(func.count()).select_from(Benchmark).where(*conditions)
    )
    response.headers["X-Total-Count"] = str(total)

    col = getattr(Benchmark, sort_by)
    q = (
        select(Benchmark)
        .where(*conditions)
        .order_by(col.desc() if order == "desc" else col.asc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(q)
    benchmarks = result.scalars().all()
    return [benchmark_to_response(b) for b in benchmarks]


# ─── GET /api/v1/benchmarks/{id} ─────────────────────────────────────────────

@app.get("/api/v1/benchmarks/{benchmark_id}", response_model=BenchmarkResponse)
async def get_benchmark(benchmark_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Benchmark).where(Benchmark.id == benchmark_id))
    b = result.scalars().first()
    if not b:
        raise HTTPException(404, "Benchmark not found")
    return benchmark_to_response(b)


# ─── GET /api/v1/leaderboard ─────────────────────────────────────────────────

@app.get("/api/v1/leaderboard", response_model=list[LeaderboardEntry])
async def leaderboard(
    model: Optional[str] = None,
    quantization: Optional[str] = None,
    sort_by: str = Query("hei", pattern="^(hei|tokens_per_second|memory_bandwidth_gbs)$"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    # Express HEI as a SQL expression so ordering AND limiting happen in the
    # database. Sorting after a LIMIT (the previous approach) returned the wrong
    # top-N once the table held more rows than `limit`. NULLIF guards price=0,
    # and NULLS LAST pushes rows without price/quality (HEI is NULL) to the end.
    hei_expr = (
        Benchmark.tokens_per_second
        * Benchmark.model_quality_score
        / func.nullif(Benchmark.hardware_price_usd, 0)
    )
    sort_columns = {
        "hei": hei_expr,
        "tokens_per_second": Benchmark.tokens_per_second,
        "memory_bandwidth_gbs": Benchmark.memory_bandwidth_gbs,
    }
    order_col = sort_columns[sort_by]

    q = select(Benchmark)
    if model:
        q = q.where(Benchmark.model_name.ilike(f"%{model}%"))
    if quantization:
        q = q.where(Benchmark.quantization == quantization)

    q = q.order_by(order_col.desc().nullslast()).limit(limit)

    result = await db.execute(q)
    benchmarks = result.scalars().all()

    entries = []
    for rank, b in enumerate(benchmarks, start=1):
        hei = compute_hei(b.tokens_per_second, b.model_quality_score, b.hardware_price_usd)
        entries.append(LeaderboardEntry(
            rank=rank, id=b.id, system_type=b.system_type, cpu_model=b.cpu_model,
            total_ram_gb=b.total_ram_gb, vram_gb=b.vram_gb,
            memory_bandwidth_gbs=b.memory_bandwidth_gbs,
            model_name=b.model_name, quantization=b.quantization,
            tokens_per_second=b.tokens_per_second, time_to_first_token=b.time_to_first_token,
            model_quality_score=b.model_quality_score, hardware_price_usd=b.hardware_price_usd,
            hei=hei,
        ))

    return entries


# ─── GET /api/v1/hardware ────────────────────────────────────────────────────

@app.get("/api/v1/hardware", response_model=list[HardwareSpecResponse])
async def list_hardware(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(HardwareSpec).order_by(HardwareSpec.memory_bandwidth_gbs.desc()))
    return result.scalars().all()


# ─── GET /api/v1/profiles ────────────────────────────────────────────────────

@app.get("/api/v1/profiles", response_model=list[ReferenceProfileResponse])
async def list_reference_profiles(db: AsyncSession = Depends(get_db)):
    """Canonical reference profiles — the pinned configs models are run on."""
    result = await db.execute(select(ReferenceProfile).order_by(ReferenceProfile.id))
    return result.scalars().all()


# ─── GET /api/v1/compare ─────────────────────────────────────────────────────

@app.get("/api/v1/compare", response_model=CompareResponse)
async def compare(a: int = Query(...), b: int = Query(...), db: AsyncSession = Depends(get_db)):
    result_a = await db.execute(select(Benchmark).where(Benchmark.id == a))
    result_b = await db.execute(select(Benchmark).where(Benchmark.id == b))
    ba = result_a.scalars().first()
    bb = result_b.scalars().first()
    if not ba or not bb:
        raise HTTPException(404, "One or both benchmarks not found")
    return CompareResponse(a=benchmark_to_response(ba), b=benchmark_to_response(bb))


# ─── GET /api/v1/stats ───────────────────────────────────────────────────────

@app.get("/api/v1/stats", response_model=StatsResponse)
async def stats(db: AsyncSession = Depends(get_db)):
    total = await db.execute(select(func.count(Benchmark.id)))
    unique_sys = await db.execute(select(func.count(distinct(Benchmark.system_type))))
    unique_models = await db.execute(select(func.count(distinct(Benchmark.model_name))))
    avg_tps = await db.execute(select(func.avg(Benchmark.tokens_per_second)))
    max_tps = await db.execute(select(func.max(Benchmark.tokens_per_second)))
    hw_count = await db.execute(select(func.count(HardwareSpec.id)))

    return StatsResponse(
        total_submissions=total.scalar() or 0,
        unique_systems=unique_sys.scalar() or 0,
        unique_models=unique_models.scalar() or 0,
        avg_tokens_per_second=round(float(avg_tps.scalar() or 0), 2),
        max_tokens_per_second=round(float(max_tps.scalar() or 0), 2),
        total_hardware_specs=hw_count.scalar() or 0,
    )


# ─── GET /api/v1/models ──────────────────────────────────────────────────────

@app.get("/api/v1/models", response_model=list[ModelQualityResponse])
async def list_models(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ModelQuality).order_by(ModelQuality.mmlu_score.desc()))
    return result.scalars().all()
