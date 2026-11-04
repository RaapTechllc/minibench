from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
from typing import Optional, Any


# ─── Agent-benchmark schemas ───────────────────────────────────────────────────


class AgentTaskResultSubmit(BaseModel):
    task_id: str = Field(..., max_length=128)
    category: Optional[str] = Field(None, max_length=64)
    scenario_type: Optional[str] = Field(None, max_length=32)
    task_description: Optional[str] = Field(None, max_length=2000)
    trial: Optional[int] = None
    passed: bool
    passed_format: Optional[bool] = None
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
    pass_format: Optional[Decimal] = Field(None, ge=0, le=100)
    pass_hat_k: Optional[Decimal] = Field(None, ge=0, le=100)
    ci95_low: Optional[Decimal] = None
    ci95_high: Optional[Decimal] = None
    cost_usd_per_task: Optional[Decimal] = None
    latency_p50_ms: Optional[int] = None
    latency_p95_ms: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    # Provenance / validity (agentbench anti-gaming protocol).
    grader_version: Optional[str] = Field(None, max_length=8)
    decoding: Optional[dict[str, Any]] = None
    seed_sha256: Optional[str] = Field(None, max_length=64)
    generator_sha256: Optional[str] = Field(None, max_length=64)
    git_commit: Optional[str] = Field(None, max_length=64)
    is_private_split: bool = False
    n_infra_errors: int = Field(0, ge=0)
    n_canary_flags: int = Field(0, ge=0)
    # minibench-pro-v1 axes (only pro runs populate them).
    calibration_brier: Optional[Decimal] = None
    robustness_correct: Optional[Decimal] = None
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
    pass_format: Optional[Decimal] = None
    pass_hat_k: Optional[Decimal] = None
    ci95_low: Optional[Decimal] = None
    ci95_high: Optional[Decimal] = None
    cost_usd_per_task: Optional[Decimal] = None
    latency_p50_ms: Optional[int] = None
    latency_p95_ms: Optional[int] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    grader_version: Optional[str] = None
    decoding: Optional[dict[str, Any]] = None
    seed_sha256: Optional[str] = None
    generator_sha256: Optional[str] = None
    git_commit: Optional[str] = None
    is_private_split: Optional[bool] = None
    n_infra_errors: Optional[int] = None
    n_canary_flags: Optional[int] = None
    calibration_brier: Optional[Decimal] = None
    robustness_consistency: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class AgentLeaderboardEntry(BaseModel):
    rank: int
    run_id: UUID
    config_name: Optional[str] = None
    self_moa: bool = False
    models: list[str] = Field(default_factory=list)
    model_snapshot_date: Optional[date] = None
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

    model_config = ConfigDict(protected_namespaces=())


class ModelLeaderboardEntry(BaseModel):
    """Best published single-model run per model string (the capability axis)."""

    rank: int
    model_string: str                      # e.g. openrouter/moonshotai/kimi-k2.7-code
    run_id: UUID
    benchmark_suite: str
    provider: Optional[str] = None
    # Catalog annotations (joined from known_models when the id matches)
    display_name: Optional[str] = None
    family: Optional[str] = None
    license: Optional[str] = None
    prompt_price: Optional[Decimal] = None
    completion_price: Optional[Decimal] = None
    # Run metrics
    n_tasks: int
    n_trials: int
    pass_rate: Decimal
    pass_hat_k: Optional[Decimal] = None
    ci95_low: Optional[Decimal] = None
    ci95_high: Optional[Decimal] = None
    cost_usd_per_task: Optional[Decimal] = None
    latency_p50_ms: Optional[int] = None
    latency_p95_ms: Optional[int] = None
    submitted_at: datetime
    category_pass_rates: dict[str, float] = Field(default_factory=dict)
    on_pareto_frontier: bool = False
    # Validity badges: dev-slice scores are contamination-prone; only
    # private-split scores are "official".
    is_private_split: Optional[bool] = None
    grader_version: Optional[str] = None
    # minibench-pro-v1 axes (present only for pro runs).
    calibration_brier: Optional[Decimal] = None
    robustness_correct: Optional[Decimal] = None

    model_config = ConfigDict(protected_namespaces=())


class AgentTaskResultResponse(BaseModel):
    task_id: str
    category: Optional[str] = None
    scenario_type: Optional[str] = None
    task_description: Optional[str] = None
    trial: Optional[int] = None
    passed: bool
    passed_format: Optional[bool] = None
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
    family: Optional[str] = None
    license: Optional[str] = None
    snapshot_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())
