from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
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
