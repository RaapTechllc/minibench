# MiniBench — Continuation Plan (for Claude Code Fable 5)

> Historical July 6 handoff. Its open work and verification counts describe that
> date. Use [project status](PROJECT-STATUS.md) and current GitHub issues now.

**Last reviewed:** 2026-07-06  
**Repo:** `RaapTechllc/minibench`  
**Baseline:** `main` @ `20e78f5`

This document is a **handoff brief**, not a spec. Read the linked sources, form your own judgment, and propose sensible slices before large changes. Prefer small PRs with green CI over big-bang rewrites.

---

## What we're building

MiniBench answers two related questions on one site:

1. **Hardware** — What's the best Mini PC per dollar for running local LLMs? Memory bandwidth is the thesis metric; HEI `(t/s × model quality) / price` is the headline score.
2. **Agents** — How do MoA and agentic configs perform on **hard, contamination-resistant tasks** we author ourselves — with cost and latency reported honestly?

The repo already supports both products end-to-end at a prototype/production-hybrid level. The work ahead is mostly **closing spec gaps**, **hardening rigor**, and **making the agent product self-maintaining** — not greenfield scaffolding.

---

## Where things stand (honest snapshot)

### Solid

| Area | Notes |
|------|-------|
| **Backend (hardware)** | FastAPI + async SQLAlchemy + Postgres. Submit validation, dedup, rate limits, leaderboard, compare, stats. Good pytest coverage. |
| **CLI** | `minibench detect/run/upload` with curated bandwidth lookup. Tested. |
| **Frontend (hardware)** | Dashboard, Leaderboard, Compare, Hardware, Benchmark detail, Submit (CLI docs). Recharts + Tailwind v4. CI runs lint, tests, build. |
| **agentbench module** | Clean replacement for the broken `benchmarks/` prototype. MoA runner, executable graders, stats (CI + pass^k), dry-run for CI, `--publish` to API. |
| **Agents product slice** | `agent_runs` / `agent_task_results` / `known_models` tables, `/api/v1/agents/*`, Agents + Run detail pages, MoA calculator, quick-pick badges. |

### Incomplete or deferred (from spec + `.claude/audit-state.md`)

These are **known gaps**, not an ordered mandate. Use judgment on sequencing.

- **Manual submit form** on `/submit` — TSD calls for CLI instructions *and* a form; today it's instructions only. API already exists.
- **Pagination metadata** — `GET /api/v1/benchmarks` has offset/limit but no total-count signal for clients.
- **Optimized inference** (TSD §7) — no `effective_model_size_gb` / raw size / "optimized only" filter yet.
- **Model tracker automation** — `agentbench/tracker.py` can poll OpenRouter; backend has `known_models` + `GET /models/new`, but nothing routinely syncs the catalog or flips `benchmarked` after a run.
- **Task breadth** — `coding-v1` (smoke) and `coding-v2` (~8 harder tasks). Brief envisioned more categories and scale.
- **Production deploy** — Docker Compose works; Vercel frontend and hardened production ops are aspirational in TSD.
- **Frontend test depth** — one Node test for MoA calculator; no page-level RTL suite yet.
- **SPRINT-1 UI polish** — partially landed (medals, regression line, relative times, etc.). Worth a pass against `SPRINT-1.md` rather than assuming it's done.

### Intentionally out of scope (unless product says otherwise)

- Full user authentication / accounts
- Convex (this stack is FastAPI + Postgres)
- Extending `benchmarks/` — treat as legacy; `agentbench/` is the path forward (CI already guards preset drift)

---

## Architecture (orientation)

```
backend/       → FastAPI :3070, hardware + agents routers
frontend/      → React 19 + Vite :3071 (nginx proxies /api in Docker)
cli/           → hardware benchmark package
agentbench/    → MoA eval engine, tasks, presets, publish hook
benchmarks/    → legacy prototype — do not build on
```

**CI:** backend · agentbench (unit + dry-run smoke) · cli · frontend (lint + test + build)

**Key docs to read before coding:**

| Doc | Why |
|-----|-----|
| `TSD.md` | Hardware product contract |
| `benchmarks/AGENT-BENCH-BRIEF.md` | Agent product vision + rigor guardrails |
| `.claude/audit-state.md` | Recent deliverables + deferred list |
| `agentbench/README.md` | How to run/publish evals today |
| `SPRINT-1.md` | UI quality bar for dashboard/leaderboard |

---

## Strategic themes (pick your own order)

These are **themes**, not sprints with fixed scope. Combine or split based on what you learn in the codebase.

### Theme A — Hardware product completeness

**Intent:** Make crowdsourced hardware data easy to submit and explore.

Consider:

- A manual submit path on `/submit` that reuses `POST /api/v1/submit` and `BenchmarkSubmit` — UX should match existing page patterns (`BenchmarkDetail`, form styling in Tailwind).
- Pagination that clients can actually use — header vs body is your call; document whatever you ship.
- Compare / Hardware pages — functional today; room for clarity (HEI deltas, RAM vs VRAM, bandwidth emphasis).
- SPRINT-1 checklist — walk it; fix what's still generic rather than adding decoration.

**Guardrails:** Don't break the CLI path. Don't add heavy UI libraries (project deliberately skipped shadcn). Match existing component style.

### Theme B — Optimized inference (TSD §7)

**Intent:** Surface RAM-efficient configs (MLX, mmap, pruning-aware runtimes).

This touches the schema. If you take it on:

- New nullable fields on `benchmarks` are probably fine; think through CLI + API + detail page together.
- A dashboard filter for "optimized only" only matters if seed/sample data can demonstrate it.

Worth a quick design note in the PR if the shape differs from TSD.

### Theme C — Agent platform that runs itself

**Intent:** New models on OpenRouter should appear in the UI without manual DB inserts; published runs should update catalog state.

`tracker.py` and `known_models` are the starting point. Reasonable directions (not prescriptions):

- Periodic sync (in-process scheduler vs external cron + CLI) — trade ops simplicity vs coupling.
- Upsert logic that preserves `benchmarked` on conflict.
- After `--publish`, mark implicated model IDs as benchmarked.
- Agents UI: the "new — not yet benchmarked" panel could gain a sync action or copy-paste run commands — keep it useful, not busy.

**Open question for product:** OpenRouter prepaid credits vs BYOK affects how you interpret `usage.cost`. Check `.env.example` and brief §2.

### Theme D — Benchmark credibility (agent tasks)

**Intent:** More tasks, harder oracles, honest discrimination between configs.

The brief's rules matter more than feature count:

- Executable oracles only; pilot graders against bad answers.
- Freeze tasks before comparing models; ≥3 trials; report CIs; overlapping CIs → "indistinguishable."
- Compare MoA to **matched-cost Self-MoA** — presets exist (`self-moa-baseline.yaml`, `self-moa-dev.yaml`); surfacing that in UI is optional but high value.
- New suites might be `tooluse`, `reasoning`, etc. — follow patterns in `coding-v2.json`.
- Commit redacted result artifacts when you run live evals; don't commit secrets.

inspect-ai was recommended in the brief as a possible harness. The repo chose a custom `agentbench` module instead. **Spike before migrate** — Docker sandbox and agent loops are real wins, but a rewrite is expensive. A short spike + written recommendation beats an silent pivot.

### Theme E — Ship it (deploy + confidence)

**Intent:** Move from "works on localhost Docker" to something deployable and trustworthy.

Consider:

- Vercel for frontend with a configurable API base URL; CORS updates on the API.
- Richer `/health` (DB reachable?).
- Light E2E smoke (even one happy path) if flakiness can be controlled.
- Vitest + RTL for high-value frontend logic (quick picks, form validation, formatters) — quality over coverage %.

---

## What "done enough" might look like

Use this as a north star, not a checkbox audit:

- Someone can submit hardware results via CLI **or** web without reading source code.
- Dashboard and leaderboard feel intentional (SPRINT-1 bar), not template-generated.
- Agent leaderboard reflects real published runs; new models surface automatically; MoA vs Self-MoA comparisons are possible.
- CI stays green; config drift is caught by dry-run smoke.
- README and CHANGELOG reflect what actually shipped.

---

## Rigor guardrails (agent product — treat as constraints)

From `AGENT-BENCH-BRIEF.md`, paraphrased:

1. No keyword grading for objective tasks.
2. Pin models and provider routing on OpenRouter for reproducibility.
3. Store auditable outputs (DB ref or committed JSON), not just aggregate scores.
4. Report cost and latency next to accuracy.
5. CI dry-run on presets/tasks — keep it passing when you edit YAML/JSON.

---

## Suggested working style for Fable 5

1. **Read** `TSD.md`, audit state, and the files you'll touch.
2. **Propose** a short plan (3–6 bullets) if the theme is large; confirm assumptions only when blocked.
3. **Branch** `cursor/<short-description>-4ffb`, slice commits logically.
4. **Test** the relevant suites — full CI before PR.
5. **Document** non-obvious choices in PR description, not long inline comments.

### Useful commands

```bash
./scripts/setup-dev.sh

# Backend
cd backend && uvicorn app.main:app --reload --port 3070

# Frontend
cd frontend && npm run dev

# Agent offline smoke (CI parity)
python -m agentbench.run \
  --config agentbench/presets/moa-v1.yaml \
  --tasks agentbench/tasks/coding-v1.json \
  --trials 2 --dry-run

# Publish (needs OPENROUTER_API_KEY in .env)
python -m agentbench.run \
  --config agentbench/presets/moa-dev.yaml \
  --tasks agentbench/tasks/coding-v2.json \
  --trials 3 --provider openrouter \
  --publish http://localhost:3070
```

---

## Open questions (resolve with product when blocked)

| Question | Why it matters |
|----------|----------------|
| Production URLs (API + frontend) | CORS, env vars, docs |
| Auth for sync/submit endpoints | Public forever vs API key |
| inspect-ai vs custom agentbench | Sandbox/agent loop vs migration cost |
| Task category priority | coding vs tool-use vs long-horizon |
| Fate of `benchmarks/` folder | Archive vs keep as drift guard only |

---

## Entry points by area

| If you're working on… | Start here |
|----------------------|------------|
| Hardware API | `backend/app/main.py`, `schemas.py`, `models.py` |
| Agents API | `backend/app/agents_router.py` |
| Agent runner | `agentbench/run.py`, `moa.py`, `grading.py` |
| Frontend pages | `frontend/src/pages/`, `frontend/src/api.ts` |
| CLI | `cli/minibench/` |
| CI | `.github/workflows/ci.yml` |

---

*This plan will drift as the codebase evolves — update this file when major assumptions change.*
