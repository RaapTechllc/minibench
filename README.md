# MiniBench

Crowdsourced LLM benchmarks for Mini PCs. Answers: **"What's the best hardware per dollar for running LLMs locally?"**

**Memory bandwidth is the critical metric.**

## Architecture

- **Backend:** FastAPI + PostgreSQL (port 3070)
- **CLI:** Python package (`minibench`) — auto-detect hardware, run standard benchmarks via Ollama
- **Frontend:** React + Vite + TypeScript + Tailwind + Recharts
- **Deploy:** Docker Compose

## Quick Start

```bash
# Start everything
docker compose up -d

# API: http://localhost:3070
# Frontend: http://localhost:3071
# Health: http://localhost:3070/health
```

## CLI

```bash
cd cli && pip install -e .

minibench detect          # Show detected hardware
minibench run             # Run standard benchmark
minibench results         # View local history
minibench upload          # Submit to API
```

## Key Metrics

- **Hardware Efficiency Index (HEI)** = (tokens/sec x MMLU) / price
- **Memory Bandwidth** — color-coded: <50 red, 50-100 amber, 100-200 green, 200+ gold
- **System RAM vs VRAM** — clearly distinguished everywhere

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/submit` | Submit benchmark |
| GET | `/api/v1/benchmarks` | List (paginated, filterable) |
| GET | `/api/v1/benchmarks/{id}` | Single detail |
| GET | `/api/v1/leaderboard` | Ranked by HEI |
| GET | `/api/v1/hardware` | Hardware specs DB |
| GET | `/api/v1/compare?a={id}&b={id}` | Side-by-side |
| GET | `/api/v1/stats` | Aggregate stats |
| GET | `/api/v1/models` | Model quality table |
| GET | `/health` | Health check |
