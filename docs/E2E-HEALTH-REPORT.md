# E2E Health Report — MiniBench

**Date:** 2026-07-15  
**Duration:** ~43s (final green run)  
**Status:** PASSING (13/13 executed specs)  
**Runner:** Playwright Chromium desktop + mobile  
**App under test:** Vite `:5173` → FastAPI `:3070` → Postgres `:5432`

## Summary

| Metric | Value |
|--------|-------|
| Total specs | 26 (13 desktop + 13 mobile project entries) |
| Passed | 13 |
| Skipped | 13 (cross-project skips by design) |
| Failed | 0 (final run) |
| Flaky | 0 after harness fixes |
| Routes exercised | `/`, `/models`, `/agents`, `/moa-calculator`, `/hardware`, `/methodology`, `/submit`, `/compare`, `/leaderboard`→`/models`, run/benchmark detail + not-found |
| Screenshots | `artifacts/e2e/*.png` (also copied under `/opt/cursor/artifacts/e2e-screenshots/`) |
| Failure videos | retained from earlier red runs under `/opt/cursor/artifacts/e2e-failures-round1/` |

## What was swept

- Desktop nav (all 6 primary links + brand home)
- Mobile hamburger open/close + every mobile nav target
- Models: cabinet select, chart Y-axis, sortable headers, drill-down to run detail
- Agents: sort select, quick picks, run detail, Technician mode toggle
- MoA Calculator: all number inputs + quality floor slider
- Hardware / Methodology / Dashboard charts + recent submission links
- Submit: client validation + successful POST `/api/v1/submit`
- Compare: A/B selects + metric comparison
- ErrorState “Try again” recovery (forced hardware API abort)
- Synthetic 404 routes for missing run / benchmark

## Critical findings (pre-fix / environment)

### P0 — Postgres schema drift breaks Agents/Models APIs

`Base.metadata.create_all` does **not** add columns to existing tables. A DB created from an older model lacked:

- `agent_runs`: `grader_version`, `decoding`, `seed_sha256`, `generator_sha256`, `git_commit`, `is_private_split`, `n_infra_errors`, `n_canary_flags`, `calibration_brier`, `robustness_correct`
- `known_models`: `family`, `license`, `snapshot_date`

**Symptom:** `/api/v1/agents/leaderboard` and `/api/v1/agents/models/leaderboard` returned **500**. Seed logged `column known_models.family does not exist`.

**Fix shipped in this PR:** `backend/app/schema_ensure.py` runs on startup after `create_all` (idempotent `ADD COLUMN IF NOT EXISTS`).

**Still recommended:** adopt Alembic (or similar) for non-additive migrations; document `python -m agentbench.import_results …` for local leaderboard data.

### P0 — Missing `backend/.env` in Cloud VM

Startup used default port **5438** while Postgres listens on **5432**, so the API failed to boot until `.env` pointed at 5432. Ensure setup scripts always materialize `backend/.env` from the 5432 example used in this environment.

## Product / UX findings from the sweep

### P1 — Agents latency column formatting

p50 rendered without a unit (`4196 / 8095ms`). **Fixed** in `Agents.tsx` to always show `p50 / p95ms`.

### P2 — Submit duplicate fingerprint (429)

Re-submitting the same hardware/model combo within 1 hour returns 429 with a clear message. Correct anti-spam behavior; E2E now uses a unique `model_name` per run. Consider surfacing the server message more prominently in the form (already shown via `serverError`).

### P2 — Overview dashboard is still “legacy-first”

Dashboard hero/stats emphasize legacy throughput (HEI, t/s) while product focus is Models/Agents scorecards. Works, but first-time users may think hardware throughput is still primary ranking.

### P3 — Dense arcade tables on mobile

Mobile nav works; Models/Agents tables remain horizontally scrollable and dense. Acceptable for data tools, but worth a compact mobile card layout later.

### P3 — Not-found states

`/agents/runs/<unknown>` and `/benchmarks/999999` show EmptyState/ErrorState correctly — no crash.

## Next steps (priority order)

1. **Land schema_ensure + keep E2E in CI** — run `npm run test:e2e` against a booted stack; fail PRs if Agents APIs 500.
2. **Introduce real migrations (Alembic)** — `schema_ensure` covers additive gaps only.
3. **Seed/import agent results in setup-dev** — empty `agent_runs` makes Models/Agents look broken even when the UI is fine.
4. **Dashboard messaging pass** — lead with Models/Agents capability, demote legacy throughput.
5. **Mobile density** — optional card layout for Models/Agents rows.
6. **Latency units audit** — confirm published artifacts store milliseconds (API field names say `_ms`; values look coherent).

## How to re-run

```bash
sudo pg_ctlcluster 16 main start
cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 3070
cd frontend && npm run dev
# optional: python -m agentbench.import_results agentbench/results/*.json --api http://127.0.0.1:3070
cd frontend && npm run test:e2e
```

## Artifacts

- Screenshots: `/opt/cursor/artifacts/e2e-screenshots/`
- Findings JSON: `frontend/artifacts/e2e/findings.json`
- HTML report: `frontend/playwright-report/` (local, gitignored)
- Failure videos (round 1 harness issues): `/opt/cursor/artifacts/e2e-failures-round1/`
