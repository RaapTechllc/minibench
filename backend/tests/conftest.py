"""Test fixtures.

Each test runs against an isolated database whose schema is reset before the
test, so the seed data is deterministic. The app's engine is disposed on
shutdown (see ``app.main.lifespan``), which lets a fresh TestClient and its own
event loop be created per test.

Backend selection (``MINIBENCH_TEST_DB``):

- ``postgres``: the ``minibench_test`` database on the documented Docker port
  (override with ``MINIBENCH_TEST_PG_*``). This is what CI runs.
- ``sqlite``: a throwaway file under the system temp dir. No daemon needed.
- ``auto`` (default): Postgres when reachable, otherwise SQLite.
"""
import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

PG_HOST = os.environ.get("MINIBENCH_TEST_PG_HOST", "127.0.0.1")
PG_PORT = os.environ.get("MINIBENCH_TEST_PG_PORT", "5438")
PG_USER = os.environ.get("MINIBENCH_TEST_PG_USER", "minibench")
PG_PASS = os.environ.get("MINIBENCH_TEST_PG_PASSWORD", "minibench")
TEST_DB = os.environ.get("MINIBENCH_TEST_PG_DB", "minibench_test")


def _postgres_reachable() -> bool:
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS,
            dbname="postgres", connect_timeout=2,
        )
        conn.close()
        return True
    except Exception:
        return False


BACKEND = os.environ.get("MINIBENCH_TEST_DB", "auto").lower()
if BACKEND == "auto":
    BACKEND = "postgres" if _postgres_reachable() else "sqlite"
if BACKEND not in {"postgres", "sqlite"}:
    raise RuntimeError(f"MINIBENCH_TEST_DB must be postgres, sqlite or auto, got {BACKEND!r}")

IS_POSTGRES = BACKEND == "postgres"
SQLITE_PATH = Path(tempfile.gettempdir()) / f"minibench_test_{os.getpid()}.sqlite3"

if IS_POSTGRES:
    DATABASE_URL = f"postgresql+asyncpg://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{TEST_DB}"
    DATABASE_URL_SYNC = f"postgresql+psycopg2://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{TEST_DB}"
else:
    DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_PATH}"
    DATABASE_URL_SYNC = f"sqlite:///{SQLITE_PATH}"

# Point the app at the test database BEFORE app.config / app.database import.
os.environ["DATABASE_URL"] = DATABASE_URL
os.environ["DATABASE_URL_SYNC"] = DATABASE_URL_SYNC


def requires_postgres(reason: str = "PostgreSQL-only behaviour"):
    """Decorator for tests that exercise Postgres-specific SQL."""
    return pytest.mark.skipif(not IS_POSTGRES, reason=reason)


def execute(sql: str, params: dict | None = None):
    """Run one statement against the test database and return all rows."""
    engine = create_engine(DATABASE_URL_SYNC)
    try:
        with engine.begin() as conn:
            result = conn.execute(text(sql), params or {})
            return result.fetchall() if result.returns_rows else []
    finally:
        engine.dispose()


def table_count(table: str) -> int:
    return execute(f"SELECT count(*) FROM {table}")[0][0]


def _connect(dbname: str):
    """Raw psycopg2 connection; only valid on the Postgres backend."""
    import psycopg2

    return psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=dbname)


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_database():
    if IS_POSTGRES:
        admin = _connect("postgres")
        admin.autocommit = True
        with admin.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{TEST_DB}"')
        admin.close()
    yield
    if not IS_POSTGRES and SQLITE_PATH.exists():
        SQLITE_PATH.unlink()


def _reset_schema():
    if IS_POSTGRES:
        conn = _connect(TEST_DB)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        conn.close()
    elif SQLITE_PATH.exists():
        SQLITE_PATH.unlink()


@pytest.fixture()
def client(_ensure_test_database):
    _reset_schema()
    from fastapi.testclient import TestClient
    from app.main import app

    app.state.limiter.enabled = False
    with TestClient(app) as test_client:  # context manager runs lifespan -> create + seed
        yield test_client


@pytest.fixture()
def seed_known_models(client):
    """Insert a benchmarked + an un-benchmarked model into ``known_models``.

    Depends on ``client`` so the schema exists (tables are created in lifespan).
    """
    execute(
        "INSERT INTO known_models (provider, model_id, display_name, benchmarked) "
        "VALUES (:p1, :m1, :d1, :b1), (:p2, :m2, :d2, :b2)",
        {
            "p1": "openrouter", "m1": "openrouter/new/model-a", "d1": "Model A", "b1": False,
            "p2": "openrouter", "m2": "openrouter/old/benchmarked", "d2": "Old", "b2": True,
        },
    )
    yield
