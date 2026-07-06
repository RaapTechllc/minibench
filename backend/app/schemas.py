from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from typing import Optional, Any


class BenchmarkSubmit(BaseModel):
    cpu_model: str = Field(..., max_length=128)
    cpu_cores: Optional[int] = None
    cpu_threads: Optional[int] = None
    gpu_model: Optional[str] = Field(None, max_length=128)
    igpu_model: Optional[str] = Field(None, max_length=128)
    total_ram_gb: Decimal = Field(..., ge=0.1)
    vram_gb: Optional[Decimal] = Field(None, ge=0)
    memory_type: Optional[str] = Field(None, max_length=32)
    memory_bandwidth_gbs: Optional[Decimal] = None
    system_type: Optional[str] = Field(None, max_length=64)
    hardware_price_usd: Optional[Decimal] = None

    os: str = Field(..., max_length=64)
    inference_engine: str = Field(..., max_length=64)
    engine_version: Optional[str] = Field(None, max_length=32)
    model_name: str = Field(..., max_length=128)
    model_params_b: Optional[Decimal] = None
    quantization: str = Field(..., max_length=32)

    tokens_per_second: Decimal = Field(..., ge=Decimal("0.1"), le=Decimal("500"))
    time_to_first_token: Optional[Decimal] = None
    watts_per_token: Optional[Decimal] = None
    total_power_watts: Optional[Decimal] = None
    prompt_tokens: int = Field(..., ge=1)
    completion_tokens: int = Field(..., ge=1)
    test_duration_secs: Decimal = Field(..., ge=Decimal("10"))

    fingerprint: Optional[str] = Field(None, max_length=64)
    client_version: Optional[str] = Field(None, max_length=16)
    thermal_setting: Optional[str] = Field(None, max_length=32)
    ambient_temp_c: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class BenchmarkResponse(BaseModel):
    id: int
    submission_id: UUID
    submitted_at: datetime
    cpu_model: str
    cpu_cores: Optional[int] = None
    cpu_threads: Optional[int] = None
    gpu_model: Optional[str] = None
    igpu_model: Optional[str] = None
    total_ram_gb: Decimal
    vram_gb: Optional[Decimal] = None
    memory_type: Optional[str] = None
    memory_bandwidth_gbs: Optional[Decimal] = None
    system_type: Optional[str] = None
    hardware_price_usd: Optional[Decimal] = None
    os: str
    inference_engine: str
    engine_version: Optional[str] = None
    model_name: str
    model_params_b: Optional[Decimal] = None
    quantization: str
    tokens_per_second: Decimal
    time_to_first_token: Optional[Decimal] = None
    watts_per_token: Optional[Decimal] = None
    total_power_watts: Optional[Decimal] = None
    prompt_tokens: int
    completion_tokens: int
    test_duration_secs: Decimal
    model_quality_score: Optional[Decimal] = None
    quality_source: Optional[str] = None
    fingerprint: Optional[str] = None
    client_version: Optional[str] = None
    ip_hash: Optional[str] = None
    thermal_setting: Optional[str] = None
    ambient_temp_c: Optional[Decimal] = None
    hei: Optional[float] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class HardwareSpecResponse(BaseModel):
    id: int
    system_name: str
    cpu_model: Optional[str] = None
    gpu_model: Optional[str] = None
    igpu_model: Optional[str] = None
    system_ram_gb: Optional[int] = None
    vram_gb: Optional[int] = None
    memory_type: Optional[str] = None
    max_memory_gb: Optional[int] = None
    memory_bandwidth_gbs: Optional[Decimal] = None
    tdp_watts: Optional[int] = None
    msrp_usd: Optional[Decimal] = None
    release_year: Optional[int] = None
    form_factor: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ModelQualityResponse(BaseModel):
    id: int
    model_family: str
    model_variant: str
    params_b: Optional[Decimal] = None
    mmlu_score: Optional[Decimal] = None
    lmsys_elo: Optional[int] = None
    source_url: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class LeaderboardEntry(BaseModel):
    rank: int
    id: int
    system_type: Optional[str] = None
    cpu_model: str
    total_ram_gb: Decimal
    vram_gb: Optional[Decimal] = None
    memory_bandwidth_gbs: Optional[Decimal] = None
    model_name: str
    quantization: str
    tokens_per_second: Decimal
    time_to_first_token: Optional[Decimal] = None
    model_quality_score: Optional[Decimal] = None
    hardware_price_usd: Optional[Decimal] = None
    hei: Optional[float] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class CompareResponse(BaseModel):
    a: BenchmarkResponse
    b: BenchmarkResponse


class StatsResponse(BaseModel):
    total_submissions: int
    unique_systems: int
    unique_models: int
    avg_tokens_per_second: Optional[float] = None
    max_tokens_per_second: Optional[float] = None
    total_hardware_specs: int


# ─── Agent-benchmark schemas ───────────────────────────────────────────────────


class AgentTaskResultSubmit(BaseModel):
    task_id: str = Field(..., max_length=128)
    category: Optional[str] = Field(None, max_length=64)
    trial: Optional[int] = None
    passed: bool
    score: Optional[Decimal] = None
    cost_usd: Optional[Decimal] = None
    latency_ms: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    raw_output_ref: Optional[str] = None


class AgentRunSubmit(BaseModel):
    harness: Optional[str] = Field(None, max_length=64)
    harness_version: Optional[str] = Field(None, max_length=32)
    moa_config: Optional[dict[str, Any]] = None
    benchmark_suite: str = Field(..., max_length=64)
    provider: Optional[str] = Field(None, max_length=32)
    model_snapshot_date: Optional[date] = None
    n_tasks: int = Field(..., ge=1)
    n_trials: int = Field(..., ge=1)
    pass_rate: Decimal = Field(..., ge=0, le=100)
    pass_hat_k: Optional[Decimal] = Field(None, ge=0, le=100)
    ci95_low: Optional[Decimal] = None
    ci95_high: Optional[Decimal] = None
    cost_usd_per_task: Optional[Decimal] = None
    latency_p50_ms: Optional[int] = None
    latency_p95_ms: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    results: list[AgentTaskResultSubmit] = Field(default_factory=list)

    model_config = ConfigDict(protected_namespaces=())


class AgentRunResponse(BaseModel):
    id: int
    run_id: UUID
    submitted_at: datetime
    harness: Optional[str] = None
    harness_version: Optional[str] = None
    moa_config: Optional[dict[str, Any]] = None
    benchmark_suite: str
    provider: Optional[str] = None
    model_snapshot_date: Optional[date] = None
    n_tasks: int
    n_trials: int
    pass_rate: Decimal
    pass_hat_k: Optional[Decimal] = None
    ci95_low: Optional[Decimal] = None
    ci95_high: Optional[Decimal] = None
    cost_usd_per_task: Optional[Decimal] = None
    latency_p50_ms: Optional[int] = None
    latency_p95_ms: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class AgentLeaderboardEntry(BaseModel):
    rank: int
    run_id: UUID
    config_name: Optional[str] = None
    self_moa: bool = False
    benchmark_suite: str
    provider: Optional[str] = None
    n_tasks: int
    n_trials: int
    pass_rate: Decimal
    pass_hat_k: Optional[Decimal] = None
    ci95_low: Optional[Decimal] = None
    ci95_high: Optional[Decimal] = None
    cost_usd_per_task: Optional[Decimal] = None
    latency_p50_ms: Optional[int] = None
    latency_p95_ms: Optional[int] = None
    on_pareto_frontier: bool = False


class AgentTaskResultResponse(BaseModel):
    task_id: str
    category: Optional[str] = None
    trial: Optional[int] = None
    passed: bool
    score: Optional[Decimal] = None
    cost_usd: Optional[Decimal] = None
    latency_ms: Optional[int] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class AgentRunDetailResponse(AgentRunResponse):
    results: list[AgentTaskResultResponse] = Field(default_factory=list)


class KnownModelResponse(BaseModel):
    id: int
    provider: str
    model_id: str
    display_name: Optional[str] = None
    first_seen: datetime
    context_length: Optional[int] = None
    prompt_price: Optional[Decimal] = None
    completion_price: Optional[Decimal] = None
    benchmarked: bool

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


# ─── Arena dashboard + voting schemas ─────────────────────────────────────────


class ArenaModelResponse(BaseModel):
    id: int
    model_id: str
    display_name: str
    provider: str
    modality: str
    task_tags: list[str]
    arena_rank: Optional[int] = None
    arena_score: Optional[Decimal] = None
    intelligence_index: Optional[Decimal] = None
    output_speed_tps: Optional[Decimal] = None
    cost_per_million_tokens: Optional[Decimal] = None
    context_window: Optional[int] = None
    strengths: list[str]
    source_name: str
    source_url: str
    updated_at: datetime
    vote_count: int = 0

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class ArenaVoteSubmit(BaseModel):
    task: str = Field(..., min_length=2, max_length=64)
    model_id: str = Field(..., min_length=2, max_length=160)

    model_config = ConfigDict(protected_namespaces=())


class ArenaVoteResponse(BaseModel):
    task: str
    model_id: str
    vote_count: int
    accepted: bool

    model_config = ConfigDict(protected_namespaces=())
