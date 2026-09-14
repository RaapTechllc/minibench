from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import engine, Base
from app.seed import run_seed
from app.agents_router import router as agents_router
from app.agent_cabinet_router import router as agent_cabinet_router
from app.openrouter_board import router as openrouter_board_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables (async engine), then seed the model catalog (sync).
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
    version="2.0.0",
    description="Cited, contamination-resistant model and agent benchmark evidence",
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

# Solo / Multiplayer cabinets and the model catalog.
app.include_router(agents_router)
# Real-Work Agent Cabinet (never mixed into Solo/MoA).
app.include_router(agent_cabinet_router)
# Cached OpenRouter Usage Board (CC BY 4.0 republish). No recommend, no live hop.
app.include_router(openrouter_board_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "minibench-api"}
