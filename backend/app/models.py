from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Numeric,
    DateTime,
    Date,
    Text,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy import JSON, Uuid
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from datetime import datetime, timezone

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# Portable column types: native JSONB on PostgreSQL, JSON on SQLite, so the API
# and its tests can run without a Postgres daemon.
JSONCol = JSON().with_variant(JSONB(), "postgresql")
# SQLite only autoincrements INTEGER PRIMARY KEY, never BIGINT.
BigPK = BigInteger().with_variant(Integer(), "sqlite")


# ─── Agent-benchmark product ───────────────────────────────────────────────────


class AgentRun(Base):
    """One MoA/agent config scored over a task suite with N trials.

    Mirrors the summary that ``agentbench.run`` emits so a run can be published
    straight to the leaderboard.
    """

    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # UNIQUE so agent_task_results.run_id can foreign-key it (a FK target must be
    # unique). This was the schema bug flagged in the brief's DDL sketch.
    run_id = Column(Uuid(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True)
    submitted_at = Column(DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False)

    harness = Column(String(64))          # inspect-native, OpenClaw, Hermes-agent
    harness_version = Column(String(32))
    moa_config = Column(JSONCol)            # {name, self_moa, models[], ...}
    benchmark_suite = Column(String(64), nullable=False)  # our-coding-v1, swe-live
    provider = Column(String(32))         # openrouter, ollama
    model_snapshot_date = Column(Date)

    n_tasks = Column(Integer, nullable=False)
    n_trials = Column(Integer, nullable=False)
    pass_rate = Column(Numeric(5, 2), nullable=False)     # 0–100 (%)
    pass_format = Column(Numeric(5, 2))                   # canonical strict-format rate
    pass_hat_k = Column(Numeric(5, 2))                    # consistency across trials
    ci95_low = Column(Numeric(5, 2))
    ci95_high = Column(Numeric(5, 2))
    cost_usd_per_task = Column(Numeric(10, 4))
    latency_p50_ms = Column(Integer)
    latency_p95_ms = Column(Integer)
    tokens_in = Column(BigInteger)
    tokens_out = Column(BigInteger)

    # Provenance / validity (agentbench anti-gaming protocol). Rows are only
    # comparable when grader_version, decoding and seed_sha256 all match; runs
    # with canary flags are contaminated and never ranked.
    grader_version = Column(String(8))
    decoding = Column(JSONCol)              # {temperature, top_p, max_tokens, system_prompt}
    seed_sha256 = Column(String(64))      # proves same-sweep without revealing the seed
    generator_sha256 = Column(String(64))
    git_commit = Column(String(64))
    is_private_split = Column(Boolean, nullable=False, default=False)
    n_infra_errors = Column(Integer, nullable=False, default=0)
    n_canary_flags = Column(Integer, nullable=False, default=0)
    # minibench-pro-v1 axes (nullable; only pro runs populate them).
    calibration_brier = Column(Numeric(6, 4))    # lower is better (Brier)
    robustness_correct = Column(Numeric(6, 4))   # frac of perturbation pairs solved on both sides


class AgentTaskResult(Base):
    """Per-task (optionally per-trial) result for an :class:`AgentRun`."""

    __tablename__ = "agent_task_results"

    id = Column(BigPK, primary_key=True, autoincrement=True)
    run_id = Column(Uuid(as_uuid=True), ForeignKey("agent_runs.run_id"), nullable=False)
    task_id = Column(String(128), nullable=False)
    category = Column(String(64))
    scenario_type = Column(String(32))
    task_description = Column(Text)
    trial = Column(Integer)
    passed = Column(Boolean, nullable=False)
    passed_format = Column(Boolean)
    score = Column(Numeric(6, 3))
    cost_usd = Column(Numeric(10, 5))
    latency_ms = Column(Integer)
    tokens_in = Column(Integer)
    tokens_out = Column(Integer)
    raw_output_ref = Column(Text)  # object-store key, not an inline blob


class KnownModel(Base):
    """Catalog of models seen on a provider, for the new-model tracker."""

    __tablename__ = "known_models"
    __table_args__ = (UniqueConstraint("provider", "model_id", name="uq_known_model"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(32), nullable=False)   # openrouter, ollama
    model_id = Column(String(160), nullable=False)  # namespaced id
    display_name = Column(String(160))
    first_seen = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    context_length = Column(Integer)
    prompt_price = Column(Numeric(12, 8))
    completion_price = Column(Numeric(12, 8))
    benchmarked = Column(Boolean, nullable=False, default=False)
    # Catalog annotations (docs/PIVOT-PLAN.md W2)
    family = Column(String(64))          # Qwen, Kimi, GLM, Claude, ...
    license = Column(String(16))         # open | closed
    snapshot_date = Column(Date)         # provider release date of the pinned id


# ─── Real-Work Agent Cabinet (additive; never mixed into agent_runs) ────────────


class AgentCabinetRun(Base):
    """One published Real-Work Agent Cabinet artifact.

    Separate from :class:`AgentRun` so Solo/MoA contracts and leaderboards stay
    untouched. Only rows that passed ``publication_receipt`` at ingest exist.
    """

    __tablename__ = "agent_cabinet_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Uuid(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True)
    submitted_at = Column(DateTime(timezone=True), default=_utcnow, server_default=func.now(), nullable=False)

    suite = Column(String(64), nullable=False)
    model_route = Column(String(256), nullable=False)
    harness = Column(String(64), nullable=False)
    harness_version = Column(String(32), nullable=False)
    tool_contract_sha256 = Column(String(64), nullable=False)
    fixture_digest = Column(String(80), nullable=False)
    budgets = Column(JSONCol, nullable=False)
    budgets_canonical = Column(Text, nullable=False)
    grader_version = Column(String(32), nullable=False)
    private_split = Column(Boolean, nullable=False, default=False)
    private_split_id = Column(String(64), nullable=False)

    # Stored/display pass rate is 0–100 (artifact summary.pass_rate * 100).
    completion = Column(Numeric(5, 2), nullable=False)
    pass_rate = Column(Numeric(5, 2), nullable=False)
    cost_usd_per_task = Column(Numeric(10, 6))
    latency_p50_ms = Column(Integer)
    category_completion = Column(JSONCol, nullable=False)

    provenance = Column(JSONCol, nullable=False)
    summary = Column(JSONCol, nullable=False)
    artifact = Column(JSONCol, nullable=False)
    publication_receipt = Column(JSONCol, nullable=False)


class AgentCabinetTaskResult(Base):
    """Per-trial child of an :class:`AgentCabinetRun`."""

    __tablename__ = "agent_cabinet_task_results"

    id = Column(BigPK, primary_key=True, autoincrement=True)
    run_id = Column(Uuid(as_uuid=True), ForeignKey("agent_cabinet_runs.run_id"), nullable=False)
    task_id = Column(String(128), nullable=False)
    category = Column(String(64))
    trial = Column(Integer)
    passed = Column(Boolean, nullable=False)
    outcome = Column(String(64))
    trial_payload = Column(JSONCol)
