# MiniBench — Production Hardening & Hardware Expansion

## Goal

Bring MiniBench from ~90% complete to production-deployable by expanding hardware coverage, reducing frontend bundle size, and seeding the leaderboard with real benchmark data.

## Context

**Project:** Crowdsourced LLM benchmarks for Mini PCs — "What's the best hardware per dollar for running LLMs locally?"
**Repo:** `RaapTechllc/minibench` (public), local at `/Users/timraap/projects/minibench/`
**Branch:** `main`, clean, up to date with origin
**Tech:** FastAPI + SQLAlchemy (async) + Postgres (port 3070) + React 19 + Vite + TypeScript + Tailwind v4
**Tests:** CLI 12/12 pass, Frontend lint+build pass, Backend needs Postgres (CI covers it)
**CI:** GitHub Actions — 3 jobs (backend with PG service, CLI, frontend lint+build)
**PRs:** 1 merged (initial completion). 0 open. 0 issues.

## Current State

- `minibench detect` works (tested on M1 Mac → detected Apple M1, 8 cores, 8GB RAM, Unified memory)
- BUT: M1 shows "Unknown — pass --bandwidth" because only M4-series chips are in `specs.py`
- Frontend builds clean but bundle is 632KB (above 500KB Vite warning)
- Leaderboard database is empty — no real submissions yet
- Docker Compose configured but not deployed

## Tasks

### Phase 1: Hardware Specs Expansion
1. Expand `minibench/specs.py` lookup table to cover Apple Silicon M1–M4 series (all variants: Pro, Max, Ultra)
2. Add Intel/AMD CPU specs (memory bandwidth for common mini PC chips: N100, N5105, Ryzen 7 5800H, etc.)
3. Add tests for new hardware entries in `test_specs.py`
4. Ensure `minibench detect` auto-identifies M1/M2/M3 without requiring `--bandwidth`

### Phase 2: Frontend Optimization
5. Add React.lazy + Suspense code-splitting for Recharts and heavy dashboard components
6. Get bundle size below 500KB (Vite warning threshold)
7. Add a loading state / skeleton for the leaderboard table
8. Verify frontend lint + build still passes after changes

### Phase 3: Backend Hardening
9. Add API rate-limiting for benchmark submission endpoint
10. Add input validation for benchmark results (reject impossible values: >1TB/s bandwidth, negative tokens/s)
11. Add a `/api/health` endpoint for uptime monitoring
12. Ensure backend tests pass with a local Postgres (via docker-compose)

### Phase 4: Deploy & Seed
13. Deploy via Docker Compose to a server (dvm or Tailscale host)
14. Run `minibench benchmark` on available hardware (M1 Mac, any mini PCs on the network)
15. Submit real results to seed the leaderboard
16. Verify the public leaderboard renders real data

## Guardrails

- Run `pytest tests/` and `npm run lint && npm run build` after each phase
- Keep the public repo clean — no secrets, no internal URLs
- All new code must have tests
- Backend tests need Postgres: `docker-compose up -d postgres` then `pytest`
- Commit messages: explain WHY, not WHAT

## Success Criteria

- [ ] M1/M2/M3 series in specs.py with tests
- [ ] `minibench detect` works on Apple Silicon without `--bandwidth` flag
- [ ] Frontend bundle < 500KB
- [ ] At least 5 new hardware entries in specs.py
- [ ] Backend tests pass with local Postgres
- [ ] Deployed and accessible via Tailscale
- [ ] Leaderboard has ≥3 real benchmark entries