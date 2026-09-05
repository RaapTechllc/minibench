# MiniBench

MiniBench measures whether AI models and agent configurations finish useful work,
with completion, cost, latency, and reproducibility receipts kept together.

The active engineering goal is the **Real-Work Agent Cabinet**. Its task fixtures,
validation gates, API, and UI are implemented. The shipped cabinet runners are
offline reference agents; a real-agent benchmark campaign is still outstanding.

Start with [project status and direction](docs/PROJECT-STATUS.md), then
[domain terms](CONTEXT.md) and the [operator manual](docs/operators/agent-cabinet.md).
Solo model tests and Multiplayer MoA tests remain separate supporting screens.
The OpenRouter Usage Board is a separate source of hosted-model context. Hardware
benchmarks remain available as legacy reference data.

## Architecture

| Component | Stack | Port |
|-----------|-------|------|
| **Backend** | FastAPI + SQLAlchemy (async) + PostgreSQL | 3070 |
| **CLI** | Python package (`minibench`) — Click, psutil, rich, Ollama HTTP API | — |
| **Frontend** | React 19 + Vite + TypeScript + Tailwind v4 + Recharts | 3071 |
| **Deploy** | Docker Compose | — |

## Quick start (Docker)

```bash
docker compose up -d --build

# Frontend:  http://localhost:3071
# API:       http://localhost:3070
# Health:    http://localhost:3070/health
```

## Local dev setup (one command)

```bash
./scripts/setup-dev.sh
```

This creates Python virtualenvs for `backend/`, `cli/`, and `agentbench/`, installs
frontend npm deps, and copies `.env.example` → `.env` if missing.

**OpenRouter** (for agent/MoA benchmarks via `agentbench/`):

1. Get an API key at [openrouter.ai/keys](https://openrouter.ai/keys)
2. Add it to `.env`: `OPENROUTER_API_KEY=sk-or-v1-...`
3. Dry-run offline (no key): `python -m agentbench.run --config agentbench/presets/moa-v1.yaml --tasks agentbench/tasks/coding-v1.json --trials 2 --dry-run`
4. Live run: `export OPENROUTER_API_KEY=sk-or-... && python -m agentbench.run --config agentbench/presets/moa-v1.yaml --tasks agentbench/tasks/coding-v1.json --trials 3 --provider openrouter`

See `agentbench/README.md` for MoA presets, grading, and publishing to `/api/v1/agents/*`.

**No key? Populate the leaderboards anyway** — replay the committed live result
artifacts into your local backend:

```bash
python -m agentbench.import_results agentbench/results/*.json --api http://localhost:3070
```

The frontend is served by nginx and reverse-proxies `/api` and `/health` to the
API container, so it works unchanged whether you run it on localhost or deploy
it elsewhere.

## Run locally without Docker

**Postgres:** The Docker example below uses port **5438**. If you use Homebrew Postgres on the
default **5432**, point both the app and tests at `localhost:5432` instead (see Testing).

**Env files:** Put `OPENROUTER_API_KEY` in the repo-root `.env` (loaded by `agentbench/run.py`).
Backend secrets live in `backend/.env` (copy from `backend/.env.example`).

```bash
# 1. Postgres (any instance works; match the URL below)
#    Homebrew default: localhost:5432  |  Docker example:
#    docker run -e POSTGRES_USER=minibench -e POSTGRES_PASSWORD=minibench \
#                    -e POSTGRES_DB=minibench -p 5438:5432 postgres:16

# 2. Backend
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+asyncpg://minibench:minibench@localhost:5432/minibench
export DATABASE_URL_SYNC=postgresql+psycopg2://minibench:minibench@localhost:5432/minibench
uvicorn app.main:app --reload --port 3070   # creates tables + seeds on startup

# 3. Frontend (separate terminal)
cd frontend
npm install
npm run dev                                  # http://localhost:5173 (proxies to :3070)
```

`create_all` creates new schemas but does not alter existing tables. Upgrade an
existing database using the committed migrations before starting the updated
backend. Back up the target database first. For the documented Docker database
on host port 5438, apply them in filename order:

```bash
PGPASSWORD=minibench psql -h localhost -p 5438 -U minibench -d minibench \
  -f backend/migrations/20260720_01_agent_task_arcade_fields.sql
PGPASSWORD=minibench psql -h localhost -p 5438 -U minibench -d minibench \
  -f backend/migrations/20260828_01_agent_cabinet.sql
PGPASSWORD=minibench psql -h localhost -p 5438 -U minibench -d minibench \
  -f backend/migrations/20260904_01_legacy_provenance.sql
```

## CLI

```bash
cd cli && pip install -e .

minibench detect          # Detected hardware + curated memory bandwidth
minibench run             # Run the standard benchmark via Ollama
minibench results         # View local history
minibench upload          # Submit the latest result to the API
```

`detect` and `run` resolve **memory bandwidth, price, memory type, and system
name** from a curated lookup table (`minibench/specs.py`) keyed by the detected
CPU — the headline metric can't be read reliably at runtime, so it is looked up
rather than guessed. Override anything explicitly:

```bash
minibench run --model llama3:8b --system-type "Mac Mini M4 Pro" --bandwidth 273 --price 1399
minibench run --no-lookup        # disable the lookup entirely
```

Set the API target with `MINIBENCH_API_URL` (default `http://localhost:3070`).

## Legacy hardware metrics

- **Hardware Efficiency Index (HEI)** = `(tokens/sec × model_quality) / price` — value per dollar.
- **Memory Bandwidth** — color-coded everywhere: `<50` red, `50–100` amber, `100–200` green, `200+` gold.
- **System RAM vs VRAM** — distinguished in the data model and every view.

## Frontend routes

| Route | Page |
|-------|------|
| `/` | Dashboard — efficiency frontier, bandwidth vs throughput, recent submissions |
| `/models` | Model capability leaderboard — heatmap category cells, equal-weight composite, CI bars, capability-vs-cost frontier |
| `/agents` | Agent/MoA config leaderboard (published `agentbench` runs) |
| `/agents/runs/:runId` | Single published run detail (per-task results) |
| `/agent-cabinet` | Real-Work Agent Cabinet: valid published runs, unranked and newest-first |
| `/agent-cabinet/runs/:runId` | Agent completion, category breakdown, cost, latency, and Technician receipts |
| `/methodology` | How the numbers are made — graders, dual scoring, CIs, contamination defenses |
| `/benchmarks/:id` | Single-benchmark detail (full hardware/software/performance breakdown) |
| `/compare` | Side-by-side comparison of two benchmarks |
| `/moa-calculator` | MoA cost calculator |
| `/usage/cost` `/usage/task` `/usage/latency` | OpenRouter Usage Board — best-by-$, best-by-task, best-by-latency (CC BY 4.0) |
| `/hardware` | Test-rig reference profiles + hardware specs |
| `/submit` | Submit results — CLI instructions and manual form |
| `/leaderboard` | Legacy route — redirects to `/models` |

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/submit` | Submit a benchmark (validated, rate-limited, dedup'd) |
| GET | `/api/v1/benchmarks` | List (paginated, filterable, sortable); `X-Total-Count` header carries the filtered total |
| GET | `/api/v1/benchmarks/{id}` | Single benchmark detail |
| GET | `/api/v1/leaderboard` | Ranked by HEI / t/s / bandwidth |
| GET | `/api/v1/hardware` | Hardware specs database |
| GET | `/api/v1/compare?a={id}&b={id}` | Side-by-side comparison |
| GET | `/api/v1/stats` | Aggregate stats |
| GET | `/api/v1/models` | Model quality table |
| POST | `/api/v1/agent-cabinet/runs` | Ingest a genuine agent-run artifact after publication gates pass |
| GET | `/api/v1/agent-cabinet/runs` | Valid agent runs, deduplicated only within exact comparison identities |
| GET | `/api/v1/agent-cabinet/runs/{run_id}` | Agent run details and provenance |
| GET | `/api/v1/agent-cabinet/compare?a={id}&b={id}` | Pairwise comparison; incompatible runs return 409 |
| GET | `/api/v1/openrouter/board` | Cached OpenRouter Usage Board snapshot (no live hop, no recommend) |
| GET | `/api/v1/openrouter/compare/best-by-cost` | Snapshot rows cheapest-first |
| GET | `/api/v1/openrouter/compare/best-by-task?task=` | Snapshot rows by task share |
| GET | `/api/v1/openrouter/compare/best-by-latency` | Snapshot rows fastest-first |
| GET | `/health` | Health check |

Recommend is **not** on this API (CORS includes `*`). Local compare:

```bash
python -m agentbench.recommend --dogfood --task code --budget 5
python -m agentbench.mcp_recommend   # stdio MCP
python -m agentbench.recommend_http  # GET http://127.0.0.1:3072/recommend?task=code
```

Poll (GET-only Data API; fixture if `OPENROUTER_API_KEY` is unset).
A live write goes to `OPENROUTER_BOARD_PATH` when that env is set (not a
durable `/tmp` file). Unset or missing path serves the committed fixture
and is never labelled live.

```bash
python -m agentbench.poll_openrouter --fixture --out /tmp/board.json
OPENROUTER_BOARD_PATH=/var/lib/minibench/openrouter-board.json python -m agentbench.poll_openrouter
```

Every Usage Board number is cited: `Source: OpenRouter (openrouter.ai/rankings), as of {as_of}. CC BY 4.0.`

### Submission validation
- `tokens_per_second` in `0.1–500`, `test_duration_secs ≥ 10`, `prompt + completion tokens ≥ 100`.
- Rate limit: 10 submissions per IP per hour.
- Fingerprint = `SHA256(cpu + gpu + ram + os + engine + model + quant)`; duplicate within 1 hour is rejected.
- Client IP is hashed, never stored raw.

## Testing

```bash
# Backend (needs a reachable Postgres; defaults to localhost:5438)
cd backend && pip install -r requirements-dev.txt && pytest

# Homebrew Postgres on :5432:
# MINIBENCH_TEST_PG_HOST=127.0.0.1 MINIBENCH_TEST_PG_PORT=5432 pytest
# Create the test DB once if needed:
#   createdb -h 127.0.0.1 -p 5432 -U $(whoami) minibench_test -O minibench

# CLI
cd cli && pip install -e . && pip install pytest && pytest

# Agent/model evaluation (offline)
cd agentbench && pip install -r requirements-dev.txt && pytest -q

# Frontend
cd frontend && npm run lint && npm test && npm run build
```

Run each component command from the repository root in its own shell. For the
Agent Cabinet lifecycle smoke, also run from the root:

```bash
python -m agentbench.agent_tasks --manifest agentbench/tasks/minibench-agent-v1-offline.json \
  --trials 2 --out /tmp/minibench-agent-smoke.json
```

Dry runs are test evidence only. Both the runner's `--publish` path and the
artifact importer refuse dry-run model/MoA results. Agent Cabinet publication
has its own stricter validation gates.

The backend suite spins up an isolated `minibench_test` database and resets its
schema per test. Override connection details with `MINIBENCH_TEST_PG_HOST` /
`_PORT` / `_USER` / `_PASSWORD` / `_DB`.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs four jobs on pushes to `main`
and pull requests: backend tests against Postgres, agentbench tests and offline
smokes, CLI tests, and frontend lint, tests, and production build.
The separate Usage Board workflow can succeed on fixtures with no API key;
green status alone does not prove a live poll or a deployed snapshot.

## License

[MIT](./LICENSE) © RaapTech LLC
