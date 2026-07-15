"""Bring existing Postgres tables in line with SQLAlchemy models.

``Base.metadata.create_all`` only creates *missing* tables — it never adds
columns to tables that already exist. Older MiniBench databases therefore
drift (e.g. ``agent_runs`` without provenance columns, ``known_models``
without ``family``/``license``), which surfaces as 500s on
``/api/v1/agents/*``.

This module issues idempotent ``ALTER TABLE ... ADD COLUMN IF NOT EXISTS``
statements for the known gaps. Safe to run on every startup.
"""

from __future__ import annotations

from sqlalchemy import text


# (table, column, DDL type fragment). Keep this list additive-only.
_AGENT_RUN_COLUMNS: list[tuple[str, str]] = [
    ("grader_version", "character varying(8)"),
    ("decoding", "jsonb"),
    ("seed_sha256", "character varying(64)"),
    ("generator_sha256", "character varying(64)"),
    ("git_commit", "character varying(64)"),
    ("is_private_split", "boolean NOT NULL DEFAULT false"),
    ("n_infra_errors", "integer NOT NULL DEFAULT 0"),
    ("n_canary_flags", "integer NOT NULL DEFAULT 0"),
    ("calibration_brier", "numeric(6,4)"),
    ("robustness_correct", "numeric(6,4)"),
]

_KNOWN_MODEL_COLUMNS: list[tuple[str, str]] = [
    ("family", "character varying(64)"),
    ("license", "character varying(16)"),
    ("snapshot_date", "date"),
]


def ensure_schema(connection) -> list[str]:
    """Apply pending additive column migrations on a sync SQLAlchemy connection.

    Compatible with ``await conn.run_sync(ensure_schema)`` on the async engine.
    """
    applied: list[str] = []
    for col, typ in _AGENT_RUN_COLUMNS:
        stmt = f"ALTER TABLE agent_runs ADD COLUMN IF NOT EXISTS {col} {typ}"
        connection.execute(text(stmt))
        applied.append(stmt)
    for col, typ in _KNOWN_MODEL_COLUMNS:
        stmt = f"ALTER TABLE known_models ADD COLUMN IF NOT EXISTS {col} {typ}"
        connection.execute(text(stmt))
        applied.append(stmt)
    return applied
