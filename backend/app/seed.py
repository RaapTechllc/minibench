import json
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import text

KNOWN_MODELS_SEED = Path(__file__).resolve().parent / "data" / "known_models_seed.json"

HARDWARE_SPECS = [
    {
        "system_name": "Mac Mini M4",
        "cpu_model": "Apple M4",
        "gpu_model": None,
        "igpu_model": "Apple M4 GPU (10-core)",
        "system_ram_gb": 16,
        "vram_gb": None,
        "memory_type": "Unified",
        "max_memory_gb": 32,
        "memory_bandwidth_gbs": 100.00,
        "tdp_watts": 15,
        "msrp_usd": 599.00,
        "release_year": 2024,
        "form_factor": "mini_pc",
    },
    {
        "system_name": "Mac Mini M4 Pro",
        "cpu_model": "Apple M4 Pro",
        "gpu_model": None,
        "igpu_model": "Apple M4 Pro GPU (20-core)",
        "system_ram_gb": 24,
        "vram_gb": None,
        "memory_type": "Unified",
        "max_memory_gb": 64,
        "memory_bandwidth_gbs": 273.00,
        "tdp_watts": 30,
        "msrp_usd": 1399.00,
        "release_year": 2024,
        "form_factor": "mini_pc",
    },
    {
        "system_name": "Mac Mini M4 Max",
        "cpu_model": "Apple M4 Max",
        "gpu_model": None,
        "igpu_model": "Apple M4 Max GPU (40-core)",
        "system_ram_gb": 64,
        "vram_gb": None,
        "memory_type": "Unified",
        "max_memory_gb": 128,
        "memory_bandwidth_gbs": 546.00,
        "tdp_watts": 40,
        "msrp_usd": 2999.00,
        "release_year": 2024,
        "form_factor": "mini_pc",
    },
    {
        "system_name": "Minisforum UM790 Pro",
        "cpu_model": "AMD Ryzen 9 7940HS",
        "gpu_model": None,
        "igpu_model": "AMD Radeon 780M",
        "system_ram_gb": 32,
        "vram_gb": None,
        "memory_type": "DDR5",
        "max_memory_gb": 64,
        "memory_bandwidth_gbs": 51.20,
        "tdp_watts": 54,
        "msrp_usd": 550.00,
        "release_year": 2023,
        "form_factor": "mini_pc",
    },
    {
        "system_name": "Minisforum MS-01",
        "cpu_model": "Intel Core i9-13900H",
        "gpu_model": None,
        "igpu_model": "Intel Iris Xe",
        "system_ram_gb": 64,
        "vram_gb": None,
        "memory_type": "DDR5",
        "max_memory_gb": 64,
        "memory_bandwidth_gbs": 76.80,
        "tdp_watts": 45,
        "msrp_usd": 850.00,
        "release_year": 2024,
        "form_factor": "mini_pc",
    },
    {
        "system_name": "Beelink SER8",
        "cpu_model": "AMD Ryzen 8945HS",
        "gpu_model": None,
        "igpu_model": "AMD Radeon 780M",
        "system_ram_gb": 32,
        "vram_gb": None,
        "memory_type": "DDR5",
        "max_memory_gb": 64,
        "memory_bandwidth_gbs": 51.20,
        "tdp_watts": 54,
        "msrp_usd": 450.00,
        "release_year": 2024,
        "form_factor": "mini_pc",
    },
    {
        "system_name": "Intel NUC 14 Pro",
        "cpu_model": "Intel Core Ultra 7 155H",
        "gpu_model": None,
        "igpu_model": "Intel Arc Graphics",
        "system_ram_gb": 32,
        "vram_gb": None,
        "memory_type": "DDR5",
        "max_memory_gb": 64,
        "memory_bandwidth_gbs": 76.80,
        "tdp_watts": 28,
        "msrp_usd": 600.00,
        "release_year": 2024,
        "form_factor": "nuc",
    },
    {
        "system_name": "NVIDIA Jetson AGX Orin",
        "cpu_model": "ARM Cortex-A78AE (12-core)",
        "gpu_model": "NVIDIA Ampere (2048 CUDA cores)",
        "igpu_model": None,
        "system_ram_gb": 64,
        "vram_gb": None,
        "memory_type": "LPDDR5",
        "max_memory_gb": 64,
        "memory_bandwidth_gbs": 204.00,
        "tdp_watts": 60,
        "msrp_usd": 1999.00,
        "release_year": 2023,
        "form_factor": "sbc",
    },
    {
        "system_name": "Framework 16",
        "cpu_model": "AMD Ryzen 7 7840HS",
        "gpu_model": None,
        "igpu_model": "AMD Radeon 780M",
        "system_ram_gb": 32,
        "vram_gb": None,
        "memory_type": "DDR5",
        "max_memory_gb": 64,
        "memory_bandwidth_gbs": 51.20,
        "tdp_watts": 54,
        "msrp_usd": 1400.00,
        "release_year": 2024,
        "form_factor": "laptop",
    },
    {
        "system_name": "Raspberry Pi 5",
        "cpu_model": "Broadcom BCM2712 (Cortex-A76)",
        "gpu_model": None,
        "igpu_model": "VideoCore VII",
        "system_ram_gb": 8,
        "vram_gb": None,
        "memory_type": "LPDDR4X",
        "max_memory_gb": 8,
        "memory_bandwidth_gbs": 34.00,
        "tdp_watts": 12,
        "msrp_usd": 80.00,
        "release_year": 2023,
        "form_factor": "sbc",
    },
]

# Canonical run configurations for the capability pivot (docs/PIVOT-PLAN.md W1).
# A model is benchmarked ON a profile, so numbers are comparable. One official
# setting per profile — the descriptions record why it's the official one.
REFERENCE_PROFILES = [
    {
        "profile_key": "consumer-gpu-24gb",
        "display_name": "Consumer GPU 24 GB",
        "description": (
            "Single consumer GPU with 24 GB VRAM (RTX 4090/3090 class). "
            "ollama (llama.cpp backend) with Q4_K_M — the most common community "
            "default: near-FP16 quality at ~4.8 bits/weight, fits 30B-class "
            "models fully in VRAM."
        ),
        "engine": "ollama",
        "engine_version_min": "0.5",
        "quantization": "Q4_K_M",
        "context_length": 8192,
        "temperature": 0.2,
        "top_p": 0.95,
        "max_tokens": 1024,
        "representative_system": None,
    },
    {
        "profile_key": "apple-unified-32gb",
        "display_name": "Apple Silicon unified 32 GB",
        "description": (
            "Apple-silicon Mac with >=24 GB unified memory (Mac Mini M4 Pro "
            "class). MLX 4-bit — the recommended Apple-native path; unified "
            "memory lets models spill past dedicated-VRAM limits."
        ),
        "engine": "MLX",
        "engine_version_min": "0.21",
        "quantization": "4bit",
        "context_length": 8192,
        "temperature": 0.2,
        "top_p": 0.95,
        "max_tokens": 1024,
        "representative_system": "Mac Mini M4 Pro",
    },
    {
        "profile_key": "cpu-only-mini-pc",
        "display_name": "CPU-only mini PC",
        "description": (
            "No dedicated GPU: DDR5 mini PC (Ryzen 7940HS / Core Ultra class). "
            "ollama with Q4_K_M; memory bandwidth is the bottleneck, which is "
            "exactly what the legacy hardware benchmark measured."
        ),
        "engine": "ollama",
        "engine_version_min": "0.5",
        "quantization": "Q4_K_M",
        "context_length": 4096,
        "temperature": 0.2,
        "top_p": 0.95,
        "max_tokens": 1024,
        "representative_system": "Minisforum UM790 Pro",
    },
    {
        "profile_key": "provider-api",
        "display_name": "Provider API (OpenRouter)",
        "description": (
            "Closed / API-only models. Engine and quantization are the "
            "provider's; we pin the dated model snapshot, provider.order and "
            "allow_fallbacks=false, and record the serving provider per run."
        ),
        "engine": None,
        "engine_version_min": None,
        "quantization": None,
        "context_length": 8192,
        "temperature": 0.2,
        "top_p": 0.95,
        "max_tokens": 1024,
        "representative_system": None,
    },
]

MODEL_QUALITY = [
    {"model_family": "Llama-3", "model_variant": "Llama-3-8B-Instruct", "params_b": 8.0, "mmlu_score": 68.4, "lmsys_elo": None, "source_url": "https://huggingface.co/meta-llama/Meta-Llama-3-8B"},
    {"model_family": "Llama-3", "model_variant": "Llama-3-70B-Instruct", "params_b": 70.0, "mmlu_score": 82.0, "lmsys_elo": None, "source_url": "https://huggingface.co/meta-llama/Meta-Llama-3-70B"},
    {"model_family": "Mistral", "model_variant": "Mistral-7B-Instruct-v0.2", "params_b": 7.0, "mmlu_score": 62.5, "lmsys_elo": None, "source_url": "https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.2"},
    {"model_family": "Gemma-2", "model_variant": "Gemma-2-9B-Instruct", "params_b": 9.0, "mmlu_score": 71.3, "lmsys_elo": None, "source_url": "https://huggingface.co/google/gemma-2-9b"},
    {"model_family": "Phi-3", "model_variant": "Phi-3-mini-4k-instruct", "params_b": 3.8, "mmlu_score": 68.8, "lmsys_elo": None, "source_url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct"},
    {"model_family": "Qwen2", "model_variant": "Qwen2-7B-Instruct", "params_b": 7.0, "mmlu_score": 70.3, "lmsys_elo": None, "source_url": "https://huggingface.co/Qwen/Qwen2-7B-Instruct"},
    {"model_family": "Qwen2.5", "model_variant": "Qwen2.5-72B-Instruct", "params_b": 72.0, "mmlu_score": 85.3, "lmsys_elo": None, "source_url": "https://huggingface.co/Qwen/Qwen2.5-72B-Instruct"},
]

# Sample benchmark submissions for demonstration
SAMPLE_BENCHMARKS = [
    {
        "cpu_model": "Apple M4 Pro",
        "cpu_cores": 14,
        "cpu_threads": 14,
        "gpu_model": None,
        "igpu_model": "Apple M4 Pro GPU (20-core)",
        "total_ram_gb": 24,
        "vram_gb": None,
        "memory_type": "Unified",
        "memory_bandwidth_gbs": 273.00,
        "system_type": "Mac Mini M4 Pro",
        "hardware_price_usd": 1399.00,
        "os": "macOS 15.2",
        "inference_engine": "MLX",
        "engine_version": "0.21.0",
        "model_name": "Llama-3-8B-Instruct",
        "model_params_b": 8.0,
        "quantization": "Q4_K_M",
        "tokens_per_second": 52.3,
        "time_to_first_token": 0.18,
        "prompt_tokens": 245,
        "completion_tokens": 512,
        "test_duration_secs": 14.5,
        "model_quality_score": 68.4,
        "quality_source": "mmlu",
        "fingerprint": "abc123def456",
        "client_version": "0.1.0",
    },
    {
        "cpu_model": "Apple M4",
        "cpu_cores": 10,
        "cpu_threads": 10,
        "gpu_model": None,
        "igpu_model": "Apple M4 GPU (10-core)",
        "total_ram_gb": 16,
        "vram_gb": None,
        "memory_type": "Unified",
        "memory_bandwidth_gbs": 100.00,
        "system_type": "Mac Mini M4",
        "hardware_price_usd": 599.00,
        "os": "macOS 15.2",
        "inference_engine": "MLX",
        "engine_version": "0.21.0",
        "model_name": "Llama-3-8B-Instruct",
        "model_params_b": 8.0,
        "quantization": "Q4_K_M",
        "tokens_per_second": 28.7,
        "time_to_first_token": 0.32,
        "prompt_tokens": 245,
        "completion_tokens": 512,
        "test_duration_secs": 26.3,
        "model_quality_score": 68.4,
        "quality_source": "mmlu",
        "fingerprint": "xyz789ghi012",
        "client_version": "0.1.0",
    },
    {
        "cpu_model": "AMD Ryzen 9 7940HS",
        "cpu_cores": 8,
        "cpu_threads": 16,
        "gpu_model": None,
        "igpu_model": "AMD Radeon 780M",
        "total_ram_gb": 32,
        "vram_gb": None,
        "memory_type": "DDR5",
        "memory_bandwidth_gbs": 51.20,
        "system_type": "Minisforum UM790 Pro",
        "hardware_price_usd": 550.00,
        "os": "Ubuntu 24.04",
        "inference_engine": "ollama",
        "engine_version": "0.3.12",
        "model_name": "Llama-3-8B-Instruct",
        "model_params_b": 8.0,
        "quantization": "Q4_K_M",
        "tokens_per_second": 18.4,
        "time_to_first_token": 0.45,
        "prompt_tokens": 245,
        "completion_tokens": 512,
        "test_duration_secs": 41.1,
        "model_quality_score": 68.4,
        "quality_source": "mmlu",
        "fingerprint": "um790pro_001",
        "client_version": "0.1.0",
    },
    {
        "cpu_model": "Apple M4 Max",
        "cpu_cores": 16,
        "cpu_threads": 16,
        "gpu_model": None,
        "igpu_model": "Apple M4 Max GPU (40-core)",
        "total_ram_gb": 64,
        "vram_gb": None,
        "memory_type": "Unified",
        "memory_bandwidth_gbs": 546.00,
        "system_type": "Mac Mini M4 Max",
        "hardware_price_usd": 2999.00,
        "os": "macOS 15.2",
        "inference_engine": "MLX",
        "engine_version": "0.21.0",
        "model_name": "Qwen2.5-72B-Instruct",
        "model_params_b": 72.0,
        "quantization": "Q4_K_M",
        "tokens_per_second": 22.1,
        "time_to_first_token": 1.82,
        "prompt_tokens": 245,
        "completion_tokens": 512,
        "test_duration_secs": 34.9,
        "model_quality_score": 85.3,
        "quality_source": "mmlu",
        "fingerprint": "m4max_001",
        "client_version": "0.1.0",
    },
    {
        "cpu_model": "Intel Core i9-13900H",
        "cpu_cores": 14,
        "cpu_threads": 20,
        "gpu_model": None,
        "igpu_model": "Intel Iris Xe",
        "total_ram_gb": 64,
        "vram_gb": None,
        "memory_type": "DDR5",
        "memory_bandwidth_gbs": 76.80,
        "system_type": "Minisforum MS-01",
        "hardware_price_usd": 850.00,
        "os": "Ubuntu 24.04",
        "inference_engine": "ollama",
        "engine_version": "0.3.12",
        "model_name": "Mistral-7B-Instruct-v0.2",
        "model_params_b": 7.0,
        "quantization": "Q8_0",
        "tokens_per_second": 14.2,
        "time_to_first_token": 0.55,
        "prompt_tokens": 245,
        "completion_tokens": 512,
        "test_duration_secs": 53.2,
        "model_quality_score": 62.5,
        "quality_source": "mmlu",
        "fingerprint": "ms01_001",
        "client_version": "0.1.0",
    },
    {
        "cpu_model": "AMD Ryzen 8945HS",
        "cpu_cores": 8,
        "cpu_threads": 16,
        "gpu_model": None,
        "igpu_model": "AMD Radeon 780M",
        "total_ram_gb": 32,
        "vram_gb": None,
        "memory_type": "DDR5",
        "memory_bandwidth_gbs": 51.20,
        "system_type": "Beelink SER8",
        "hardware_price_usd": 450.00,
        "os": "Windows 11",
        "inference_engine": "ollama",
        "engine_version": "0.3.12",
        "model_name": "Phi-3-mini-4k-instruct",
        "model_params_b": 3.8,
        "quantization": "Q4_K_M",
        "tokens_per_second": 32.6,
        "time_to_first_token": 0.22,
        "prompt_tokens": 245,
        "completion_tokens": 512,
        "test_duration_secs": 23.5,
        "model_quality_score": 68.8,
        "quality_source": "mmlu",
        "fingerprint": "ser8_001",
        "client_version": "0.1.0",
    },
    {
        "cpu_model": "ARM Cortex-A78AE (12-core)",
        "cpu_cores": 12,
        "cpu_threads": 12,
        "gpu_model": "NVIDIA Ampere (2048 CUDA cores)",
        "igpu_model": None,
        "total_ram_gb": 64,
        "vram_gb": None,
        "memory_type": "LPDDR5",
        "memory_bandwidth_gbs": 204.00,
        "system_type": "NVIDIA Jetson AGX Orin",
        "hardware_price_usd": 1999.00,
        "os": "JetPack 6.0",
        "inference_engine": "llama.cpp",
        "engine_version": "b3100",
        "model_name": "Llama-3-8B-Instruct",
        "model_params_b": 8.0,
        "quantization": "Q4_K_M",
        "tokens_per_second": 38.9,
        "time_to_first_token": 0.28,
        "prompt_tokens": 245,
        "completion_tokens": 512,
        "test_duration_secs": 19.4,
        "model_quality_score": 68.4,
        "quality_source": "mmlu",
        "fingerprint": "jetson_001",
        "client_version": "0.1.0",
    },
    {
        "cpu_model": "Broadcom BCM2712 (Cortex-A76)",
        "cpu_cores": 4,
        "cpu_threads": 4,
        "gpu_model": None,
        "igpu_model": "VideoCore VII",
        "total_ram_gb": 8,
        "vram_gb": None,
        "memory_type": "LPDDR4X",
        "memory_bandwidth_gbs": 34.00,
        "system_type": "Raspberry Pi 5",
        "hardware_price_usd": 80.00,
        "os": "Raspberry Pi OS 12",
        "inference_engine": "llama.cpp",
        "engine_version": "b3100",
        "model_name": "Phi-3-mini-4k-instruct",
        "model_params_b": 3.8,
        "quantization": "Q4_K_M",
        "tokens_per_second": 4.2,
        "time_to_first_token": 2.10,
        "prompt_tokens": 245,
        "completion_tokens": 512,
        "test_duration_secs": 182.0,
        "model_quality_score": 68.8,
        "quality_source": "mmlu",
        "fingerprint": "rpi5_001",
        "client_version": "0.1.0",
    },
]


def seed_hardware_specs(session: Session):
    from app.models import HardwareSpec
    for spec in HARDWARE_SPECS:
        existing = session.query(HardwareSpec).filter_by(system_name=spec["system_name"]).first()
        if not existing:
            session.add(HardwareSpec(**spec))
    session.commit()


def seed_model_quality(session: Session):
    from app.models import ModelQuality
    for mq in MODEL_QUALITY:
        existing = session.query(ModelQuality).filter_by(
            model_family=mq["model_family"],
            model_variant=mq["model_variant"]
        ).first()
        if not existing:
            session.add(ModelQuality(**mq))
    session.commit()


def seed_reference_profiles(session: Session):
    from app.models import ReferenceProfile
    for rp in REFERENCE_PROFILES:
        existing = session.query(ReferenceProfile).filter_by(profile_key=rp["profile_key"]).first()
        if not existing:
            session.add(ReferenceProfile(**rp))
    session.commit()


def seed_known_models(session: Session):
    """Load the committed master-catalog file (generated by agentbench.catalog).

    Insert-if-absent on (provider, model_id) so a re-seed never clobbers
    ``benchmarked`` flags set by real published runs.
    """
    from app.models import KnownModel

    if not KNOWN_MODELS_SEED.exists():  # catalog file is optional in dev
        return
    payload = json.loads(KNOWN_MODELS_SEED.read_text(encoding="utf-8"))
    for row in payload.get("models", []):
        existing = (
            session.query(KnownModel)
            .filter_by(provider=row["provider"], model_id=row["model_id"])
            .first()
        )
        if existing:
            continue
        session.add(
            KnownModel(
                provider=row["provider"],
                model_id=row["model_id"],
                display_name=row.get("display_name"),
                context_length=row.get("context_length"),
                prompt_price=row.get("prompt_price"),
                completion_price=row.get("completion_price"),
                benchmarked=False,
                family=row.get("family"),
                license=row.get("license"),
                snapshot_date=date.fromisoformat(row["snapshot_date"]) if row.get("snapshot_date") else None,
            )
        )
    session.commit()


def seed_benchmarks(session: Session):
    from app.models import Benchmark
    # Only seed if table is empty
    if session.query(Benchmark).count() == 0:
        for b in SAMPLE_BENCHMARKS:
            session.add(Benchmark(**b))
        session.commit()


def run_seed():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings
    from app.database import Base

    engine = create_engine(settings.database_url_sync)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        seed_hardware_specs(session)
        seed_model_quality(session)
        seed_reference_profiles(session)
        seed_known_models(session)
        seed_benchmarks(session)
        print("Seed data loaded successfully.")
    finally:
        session.close()
        engine.dispose()


if __name__ == "__main__":
    run_seed()
