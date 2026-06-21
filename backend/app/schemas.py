from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional


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
