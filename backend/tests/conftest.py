"""Test fixtures.

Each test runs against an isolated ``minibench_test`` database whose schema is
reset before the test, so the seed data is deterministic. The app's engine is
disposed on shutdown (see ``app.main.lifespan``), which lets a fresh TestClient
— and its own event loop — be created per test without asyncpg complaining about
connections bound to a different loop.
"""
import os

import psycopg2
import pytest

PG_HOST = os.environ.get("MINIBENCH_TEST_PG_HOST", "127.0.0.1")
PG_PORT = os.environ.get("MINIBENCH_TEST_PG_PORT", "5438")
PG_USER = os.environ.get("MINIBENCH_TEST_PG_USER", "minibench")
PG_PASS = os.environ.get("MINIBENCH_TEST_PG_PASSWORD", "minibench")
TEST_DB = os.environ.get("MINIBENCH_TEST_PG_DB", "minibench_test")

# Point the app at the test database BEFORE app.config / app.database import.
os.environ["DATABASE_URL"] = f"postgresql+asyncpg://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{TEST_DB}"
os.environ["DATABASE_URL_SYNC"] = f"postgresql+psycopg2://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{TEST_DB}"


def _connect(dbname: str):
    return psycopg2.connect(host=PG_HOST, port=PG_PORT, user=PG_USER, password=PG_PASS, dbname=dbname)


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_database():
    admin = _connect("postgres")
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{TEST_DB}"')
    admin.close()
    yield


def _reset_schema():
    conn = _connect(TEST_DB)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    conn.close()


@pytest.fixture()
def client(_ensure_test_database):
    _reset_schema()
    from fastapi.testclient import TestClient
    from app.main import app

    # Rate limiting would make repeated submissions flaky across tests.
    app.state.limiter.enabled = False
    with TestClient(app) as test_client:  # context manager runs lifespan -> create + seed
        yield test_client
