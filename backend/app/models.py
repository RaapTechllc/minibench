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
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from app.database import Base


class Benchmark(Base):
    __tablename__ = "benchmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    submission_id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Hardware
    cpu_model = Column(String(128), nullable=False)
    cpu_cores = Column(Integer)
    cpu_threads = Column(Integer)
    gpu_model = Column(String(128))
    igpu_model = Column(String(128))
    total_ram_gb = Column(Numeric(6, 1), nullable=False)
    vram_gb = Column(Numeric(6, 1))  # Dedicated VRAM - distinguish from system RAM
    memory_type = Column(String(32))
    memory_bandwidth_gbs = Column(Numeric(8, 2))
    system_type = Column(String(64))
    hardware_price_usd = Column(Numeric(8, 2))

    # Software
    os = Column(String(64), nullable=False)
    inference_engine = Column(String(64), nullable=False)
    engine_version = Column(String(32))
    model_name = Column(String(128), nullable=False)
    model_params_b = Column(Numeric(6, 2))
    quantization = Column(String(32), nullable=False)

    # Performance
    tokens_per_second = Column(Numeric(8, 2), nullable=False)
    time_to_first_token = Column(Numeric(8, 4))
    watts_per_token = Column(Numeric(8, 4))
    total_power_watts = Column(Numeric(8, 2))
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    test_duration_secs = Column(Numeric(8, 2), nullable=False)

    # Quality (from lookup)
    model_quality_score = Column(Numeric(6, 2))
    quality_source = Column(String(32))

    # Validation
    fingerprint = Column(String(64))
    client_version = Column(String(16))
    ip_hash = Column(String(64))

    # Thermal
    thermal_setting = Column(String(32))
    ambient_temp_c = Column(Numeric(4, 1))


class HardwareSpec(Base):
    __tablename__ = "hardware_specs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    system_name = Column(String(128), nullable=False, unique=True)
    cpu_model = Column(String(128))
    gpu_model = Column(String(128))
    igpu_model = Column(String(128))
    system_ram_gb = Column(Integer)  # System RAM
    vram_gb = Column(Integer)       # Dedicated VRAM (NULL if none)
    memory_type = Column(String(32))
    max_memory_gb = Column(Integer)
    memory_bandwidth_gbs = Column(Numeric(8, 2))
    tdp_watts = Column(Integer)
    msrp_usd = Column(Numeric(8, 2))
    release_year = Column(Integer)
    form_factor = Column(String(32))


class ReferenceProfile(Base):
    """A canonical, pinned run configuration ("how we run models").

    The pivot demotes hardware to a controlled variable: models are benchmarked
    *on a profile*, so numbers are comparable. Each profile pins the engine,
    quantization, context and decoding defaults; ``representative_system``
    points at a ``hardware_specs.system_name`` row where applicable.
    """

    __tablename__ = "reference_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_key = Column(String(64), nullable=False, unique=True)  # consumer-gpu-24gb
    display_name = Column(String(128), nullable=False)
    description = Column(Text)                    # why this is the official setting
    engine = Column(String(64))                   # ollama, llama.cpp, MLX, vLLM; NULL = provider API
    engine_version_min = Column(String(32))
    quantization = Column(String(32))             # Q4_K_M default; NULL = provider-served
    context_length = Column(Integer)
    temperature = Column(Numeric(3, 2))
    top_p = Column(Numeric(3, 2))
    max_tokens = Column(Integer)
    representative_system = Column(String(128))   # hardware_specs.system_name


class ModelQuality(Base):
    __tablename__ = "model_quality"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_family = Column(String(64), nullable=False)
    model_variant = Column(String(128), nullable=False)
    params_b = Column(Numeric(6, 2))
    mmlu_score = Column(Numeric(5, 2))
    lmsys_elo = Column(Integer)
    source_url = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


# ─── Agent-benchmark product (additive; separate from the hardware tables) ─────


class AgentRun(Base):
    """One MoA/agent config scored over a task suite with N trials.

    Mirrors the summary that ``agentbench.run`` emits so a run can be published
    straight to the leaderboard.
    """

    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # UNIQUE so agent_task_results.run_id can foreign-key it (a FK target must be
    # unique). This was the schema bug flagged in the brief's DDL sketch.
    run_id = Column(UUID(as_uuid=True), default=uuid.uuid4, nullable=False, unique=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    harness = Column(String(64))          # inspect-native, OpenClaw, Hermes-agent
    harness_version = Column(String(32))
    moa_config = Column(JSONB)            # {name, self_moa, models[], ...}
    benchmark_suite = Column(String(64), nullable=False)  # our-coding-v1, swe-live
    provider = Column(String(32))         # openrouter, ollama
    model_snapshot_date = Column(Date)

    n_tasks = Column(Integer, nullable=False)
    n_trials = Column(Integer, nullable=False)
    pass_rate = Column(Numeric(5, 2), nullable=False)     # 0–100 (%)
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
    decoding = Column(JSONB)              # {temperature, top_p, max_tokens, system_prompt}
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

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("agent_runs.run_id"), nullable=False)
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
