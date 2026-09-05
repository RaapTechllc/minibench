# MiniBench — Technical Specification Document

> Historical March 2026 hardware specification. Current product scope and
> evidence are in [project status](docs/PROJECT-STATUS.md).

**Version:** 1.0
**Date:** 2026-03-29
**Author:** Maxx (for Kyle Raap / RaapTech LLC)

## 1. Overview
MiniBench crowdsources and visualizes performance benchmarks for Mini PCs running local LLMs. It answers: "What's the best hardware per dollar for running LLMs locally?"

**Two axes:**
- **Throughput** — Tokens per Second (t/s)
- **Model Quality** — MMLU / LMSYS Elo score for the model tested

Combined into a **Hardware Efficiency Index (HEI)** = `(tokens_per_second × model_quality_score) / hardware_price`

## 2. Architecture

```
┌─────────────────┐     POST /submit     ┌──────────────┐     ┌──────────────┐
│  CLI Benchmark   │ ──────────────────→  │  FastAPI API  │ ──→ │  PostgreSQL  │
│  (Python, local) │                      │  (DVM :3070)  │     │  (DVM :5432) │
└─────────────────┘                      └──────────────┘     └──────────────┘
                                                ↑
                                    ┌───────────┘
                                    │
                              ┌─────────────┐
                              │  React SPA   │
                              │  (Vercel)    │
                              └─────────────┘
```

## 3. Data Model

### 3.1 `benchmarks` table
```sql
CREATE TABLE benchmarks (
  id            SERIAL PRIMARY KEY,
  submission_id UUID NOT NULL DEFAULT gen_random_uuid(),
  submitted_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Hardware
  cpu_model         VARCHAR(128) NOT NULL,
  cpu_cores         INT,
  cpu_threads       INT,
  gpu_model         VARCHAR(128),        -- NULL if iGPU only
  igpu_model        VARCHAR(128),        -- integrated GPU
  total_ram_gb      DECIMAL(6,1) NOT NULL,
  memory_type       VARCHAR(32),         -- DDR4, DDR5, LPDDR5x, Unified
  memory_bandwidth_gbs DECIMAL(8,2),     -- GB/s — THE critical metric
  system_type       VARCHAR(64),         -- "Mac Mini M4 Pro", "Minisforum UM790"
  hardware_price_usd DECIMAL(8,2),       -- MSRP at time of test (optional)

  -- Software
  os                VARCHAR(64) NOT NULL,
  inference_engine  VARCHAR(64) NOT NULL, -- llama.cpp, MLX, vLLM, EXL2, ollama
  engine_version    VARCHAR(32),
  model_name        VARCHAR(128) NOT NULL, -- e.g. "Llama-3-8B-Instruct"
  model_params_b    DECIMAL(6,2),         -- billions
  quantization      VARCHAR(32) NOT NULL,  -- Q4_K_M, Q8_0, FP16, etc.

  -- Performance
  tokens_per_second    DECIMAL(8,2) NOT NULL,
  time_to_first_token  DECIMAL(8,4),         -- seconds
  watts_per_token      DECIMAL(8,4),         -- if measurable
  total_power_watts    DECIMAL(8,2),         -- system draw during test
  prompt_tokens        INT NOT NULL,
  completion_tokens    INT NOT NULL,
  test_duration_secs   DECIMAL(8,2) NOT NULL,

  -- Quality (from lookup)
  model_quality_score  DECIMAL(6,2),          -- MMLU or normalized Elo
  quality_source       VARCHAR(32),           -- "mmlu", "lmsys_elo", "manual"

  -- Validation
  fingerprint      VARCHAR(64),               -- SHA256 of hw+sw combo
  client_version   VARCHAR(16),
  ip_hash          VARCHAR(64),               -- hashed, not stored raw

  -- Thermal
  thermal_setting  VARCHAR(32),               -- "default", "performance", "quiet"
  ambient_temp_c   DECIMAL(4,1)
);

CREATE INDEX idx_benchmarks_system ON benchmarks(system_type);
CREATE INDEX idx_benchmarks_model ON benchmarks(model_name, quantization);
CREATE INDEX idx_benchmarks_tps ON benchmarks(tokens_per_second DESC);
```

### 3.2 `hardware_specs` lookup table
```sql
CREATE TABLE hardware_specs (
  id                SERIAL PRIMARY KEY,
  system_name       VARCHAR(128) NOT NULL UNIQUE,
  cpu_model         VARCHAR(128),
  gpu_model         VARCHAR(128),
  igpu_model        VARCHAR(128),
  memory_type       VARCHAR(32),
  max_memory_gb     INT,
  memory_bandwidth_gbs DECIMAL(8,2),
  tdp_watts         INT,
  msrp_usd          DECIMAL(8,2),
  release_year      INT,
  form_factor       VARCHAR(32)   -- "mini_pc", "nuc", "laptop", "sbc"
);
```

### 3.3 `model_quality` lookup table
```sql
CREATE TABLE model_quality (
  id            SERIAL PRIMARY KEY,
  model_family  VARCHAR(64) NOT NULL,
  model_variant VARCHAR(128) NOT NULL,
  params_b      DECIMAL(6,2),
  mmlu_score    DECIMAL(5,2),
  lmsys_elo     INT,
  source_url    TEXT,
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(model_family, model_variant)
);
```

## 4. API Endpoints (FastAPI)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/submit` | Submit benchmark result |
| GET | `/api/v1/benchmarks` | List benchmarks (paginated, filterable) |
| GET | `/api/v1/benchmarks/{id}` | Single benchmark detail |
| GET | `/api/v1/leaderboard` | Ranked by HEI (filterable by model, quant) |
| GET | `/api/v1/hardware` | List known hardware specs |
| GET | `/api/v1/compare?a={id}&b={id}` | Side-by-side comparison |
| GET | `/api/v1/stats` | Aggregate stats (total submissions, unique systems) |
| GET | `/api/v1/models` | Model quality lookup table |
| GET | `/health` | Health check |

### Validation rules for POST /submit:
- `tokens_per_second` must be 0.1–500 (reject outliers)
- `test_duration_secs` must be ≥10
- `prompt_tokens + completion_tokens` must be ≥100
- Rate limit: 10 submissions per IP per hour
- `fingerprint` = SHA256(cpu_model + gpu_model + total_ram + os + engine + model + quant)
- Duplicate fingerprint within 1 hour = reject

## 5. CLI Benchmark Client (`minibench`)

```
pip install minibench
minibench run                    # auto-detect hw, run standard test
minibench run --model qwen2:7b   # specific model
minibench run --engine mlx       # specific engine
minibench results                # show local history
minibench upload                 # POST to API
```

### Auto-detection:
- CPU: `platform.processor()`, `/proc/cpuinfo`, `sysctl` (macOS)
- RAM: `psutil.virtual_memory()`
- GPU: `subprocess` → `nvidia-smi`, `system_profiler` (macOS), `lspci`
- Memory bandwidth: lookup table keyed by CPU/system model
- OS: `platform.system()` + `platform.release()`

### Standard test:
1. Pull model via ollama (fallback: llama.cpp direct)
2. Run 3 warmup prompts (discarded)
3. Run 5 test prompts (standardized, ~200 tokens each)
4. Measure: t/s, TTFT, total time
5. Average across 5 runs, report median + p95

### Standard prompts (consistent across all submissions):
```python
STANDARD_PROMPTS = [
    "Explain quantum computing in simple terms.",
    "Write a Python function that implements binary search.",
    "What are the economic implications of universal basic income?",
    "Describe the process of photosynthesis step by step.",
    "Compare and contrast TCP and UDP protocols.",
]
```

## 6. Frontend (React + Vite + Tailwind + Recharts)

### Pages:
1. **Dashboard** (`/`) — Hero stats + Efficiency Frontier chart + recent submissions
2. **Leaderboard** (`/leaderboard`) — Sortable table, filters by model/quant/system type
3. **Compare** (`/compare`) — Side-by-side hardware comparison
4. **Submit** (`/submit`) — Instructions for CLI tool + manual submission form
5. **Hardware** (`/hardware`) — Known hardware database with specs

### Key components:
- **Efficiency Frontier Chart**: Scatter plot (X=t/s, Y=model quality). Each dot = a benchmark. Color = system type. Size = RAM. Hover = full details. Pareto frontier line drawn.
- **Leaderboard Table**: Columns: Rank, System, CPU, RAM, Model, Quant, t/s, TTFT, HEI, Price, Value. Filterable + searchable.
- **Comparison View**: Two cards side-by-side with bar charts overlaying metrics.

### Memory bandwidth emphasis:
- Prominent "Memory Bandwidth" column in all tables
- Color-coded: <50 GB/s red, 50-100 amber, 100-200 green, 200+ gold
- Correlation chart: memory bandwidth vs t/s (should be near-linear for memory-bound inference)
- Clearly distinguish "System RAM" vs "Dedicated VRAM" in all views

## 7. Google Gemma Optimized Inference (RAM Optimization)

Reference: Google's "Gemma on device" techniques:
- **Weight sharing / pruning** awareness in the schema
- Track `effective_model_size_gb` vs `raw_model_size_gb`
- Flag submissions using optimized runtimes (MLX, GGML with mmap)
- Dashboard filter: "Show optimized only" to compare RAM-efficient configs

## 8. Deployment

| Component | Where | Port |
|-----------|-------|------|
| FastAPI | Docker on DVM | :3070 |
| PostgreSQL | brain-postgres (existing) or new container | :5438 |
| React SPA | Vercel | — |

GitHub repo: `RaapTechllc/minibench`

## 9. Seed Data

Pre-populate `hardware_specs` with:
- Mac Mini M4 (16GB, 100GB/s, $599)
- Mac Mini M4 Pro (24GB, 273GB/s, $1,399)
- Mac Mini M4 Max (64GB, 546GB/s, $2,999)
- Minisforum UM790 Pro (Ryzen 9 7940HS, 32GB DDR5, ~51.2GB/s, $550)
- Minisforum MS-01 (i9-13900H, 64GB DDR5, ~76.8GB/s, $850)
- Beelink SER8 (Ryzen 8945HS, 32GB, $450)
- Intel NUC 14 Pro (Ultra 7 155H, 32GB, $600)
- NVIDIA Jetson AGX Orin (64GB, 204GB/s, $1,999)
- Framework 16 (Ryzen 7 7840HS, 32GB, $1,400)
- Raspberry Pi 5 (8GB LPDDR4X, 34GB/s, $80)

Pre-populate `model_quality` with:
- Llama-3-8B (MMLU 68.4)
- Llama-3-70B (MMLU 82.0)
- Mistral-7B (MMLU 62.5)
- Gemma-2-9B (MMLU 71.3)
- Phi-3-mini (MMLU 68.8)
- Qwen2-7B (MMLU 70.3)
- Qwen2.5-72B (MMLU 85.3)

## 10. Build Phases

**Phase 1:** Database schema + FastAPI backend + seed data (Damien)
**Phase 2:** Python CLI benchmark client (Damien)
**Phase 3:** React dashboard with charts (Damien, Gemini Pro for UI)
**Phase 4:** Deploy: Docker on DVM + Vercel frontend

Git: commit + push to `main` after every phase. GitHub repo created at scaffold.
