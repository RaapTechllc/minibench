# MiniBench — Build Brief for Damien

> Historical hardware build brief. Completed or superseded; do not execute its
> deployment or main-branch instructions as current work. Start with
> [project status](docs/PROJECT-STATUS.md).

## What You're Building
"MiniBench" — a platform that crowdsources benchmarks for Mini PCs running local LLMs. CLI collects data, API stores it, dashboard visualizes it.

## Full Spec
Read: `/home/cbd/projects/minibench/TSD.md` (will be SCP'd alongside this brief)

## Stack
- **Backend:** FastAPI + PostgreSQL (new DB `minibench` on existing postgres or new container on port 5438)
- **CLI:** Python package (`minibench`) using Click, psutil, platform, requests
- **Frontend:** Vite + React + TypeScript + Tailwind CSS + Recharts + shadcn/ui
- **Deploy:** Docker Compose on DVM for API, Vercel for frontend

## Build Order
1. **Phase 1 — DB + API** (~30 min)
   - Create GitHub repo `RaapTechllc/minibench`
   - PostgreSQL schema (3 tables: benchmarks, hardware_specs, model_quality)
   - FastAPI with all endpoints from TSD section 4
   - Seed data from TSD section 9
   - `git add -A && git commit -m "phase 1: api + db" && git push origin main`

2. **Phase 2 — CLI Client** (~20 min)
   - Python package with Click CLI
   - Auto-detect: CPU, GPU, RAM, OS via psutil/platform/subprocess
   - Standard test: 5 prompts via ollama HTTP API (localhost:11434)
   - Measure: t/s, TTFT, duration
   - POST results to API
   - `git add -A && git commit -m "phase 2: cli client" && git push origin main`

3. **Phase 3 — Dashboard** (~30 min)
   - Vite + React + TypeScript + Tailwind + shadcn/ui + Recharts
   - Pages: Dashboard (efficiency frontier scatter), Leaderboard (table), Compare (side-by-side), Hardware DB
   - Memory bandwidth = most prominent metric, color-coded
   - Clearly distinguish System RAM vs VRAM everywhere
   - `git add -A && git commit -m "phase 3: dashboard" && git push origin main`

4. **Phase 4 — Docker + Deploy** (~15 min)
   - Docker Compose for API + DB
   - Deploy to DVM on port :3070
   - Frontend to Vercel
   - `git add -A && git commit -m "phase 4: deploy" && git push origin main`

## Critical Requirements
- Memory bandwidth is THE key variable — make it prominent everywhere
- System RAM vs VRAM must be distinguished in UI and data model
- No hallucinated hardware specs — use the seed data lookup table from TSD
- Validation on submissions: rate limit, fingerprint dedup, range checks
- Hardware Efficiency Index = (t/s × model_quality) / price

## Git
- Repo: `RaapTechllc/minibench`
- Create repo first: `gh repo create RaapTechllc/minibench --public --clone`
- Commit + push after EVERY phase
- Work on `main` branch only

## Credentials
- GitHub: `gh` CLI is authenticated
- Vercel: `vercel` CLI available
- Docker: available on DVM for deployment phase
