# MiniBench — Audit / Build State

_Lightweight state for `/audit` and `/goal`. Source-backed; keep it small._

- **last_build_sha:** `50950b3` (branch `claude/benchmark-detail-page`)
- **last_audit_sha:** _none — no `/audit` has been run. Baseline before this run
  was the merged `main` (`0ad6944`, PR #1, green CI). Treat history as
  build-verified but not formally audited._
- **baseline gates:** backend `pytest` 12/12 · frontend `eslint` clean ·
  frontend `vite build` (tsc) ✓

## Delivered this run (slice)
**Capability pivot, slices 1–5** (branch `cursor/capability-pivot-4ffb`,
2026-07-06; spec in `docs/PIVOT-PLAN.md` — deliverable 1, for sign-off on the PR).
- **Docs:** PIVOT-PLAN.md (defaults chosen for budget/provider/categories/
  profiles; dictated model names resolved against the live OpenRouter feed) +
  SPRINT-PLAN-FABLE5.md landed in docs/.
- **W1:** `reference_profiles` table/seed/`GET /api/v1/profiles` + Hardware-page
  "How we run models" panel — hardware demoted to the fixed test rig.
- **W2:** `agentbench/catalog.py` → committed
  `backend/app/data/known_models_seed.json` (42 pinned ids, family/license/
  snapshot_date columns added to known_models). Yi/InternLM absent from the
  feed, recorded not invented.
- **W3:** `minibench_gen.py` (procedural, computed gold, canary; committed dev
  slice `tasks/minibench-core-v1.json`, seed 20260706), `single: true` config
  mode + `run.py --model`, `cost_check.py` budget guard ($3.14 est. worst case
  vs $5 budget), CI dry-run + budget steps.
- **W4:** `GET /api/v1/agents/models/leaderboard` (best single-model run per
  model, catalog join, per-category pass rates, Pareto) + Models page + nav.
- Verified end-to-end: fresh seed → publish dry run via `run.py --model
  --publish` → model leaderboard row with catalog join → Models page rendering.
- Gates: backend 26/26 · agentbench 60/60 · frontend lint/test(12)/build green.

## Delivered previously (slice)
**Manual submission form on `/submit`** (branch
`cursor/manual-submit-form-4ffb`, 2026-07-06). TSD §6 — the page now offers
CLI instructions *and* a form.
- Pure validation/payload logic in `frontend/src/lib/submitForm.js` (+ `.d.ts`),
  mirroring the server rules (required fields, t/s 0.1–500, duration ≥10,
  prompt+completion ≥100); 8 node tests in `frontend/tests/submitForm.test.mjs`
  (suite 12/12).
- `api.ts`: new `postJSON` that surfaces FastAPI `detail` errors (string and
  422-list forms) + `api.submitBenchmark`.
- `Submit.tsx`: Hardware/Software/Performance field groups, inline errors,
  server-error banner, success panel linking to `/benchmarks/{id}`.
- Verified end-to-end: form-built payload → live `POST /api/v1/submit` 200,
  duplicate-fingerprint 429 detail surfaced; browser walkthrough (empty submit
  shows 10 inline errors; valid submit → success panel → detail page).
- No backend changes.

## Delivered previously (slice)
**Pagination metadata for `GET /api/v1/benchmarks`** (branch
`cursor/benchmarks-total-count-4ffb`, 2026-07-06).
- `X-Total-Count` response header carries the filtered total (count query runs
  the same filters, before offset/limit); exposed via CORS `expose_headers`.
- Non-breaking: body stays `list[BenchmarkResponse]`; frontend untouched.
- 3 new tests in `backend/tests/test_api.py` (first coverage for the list
  endpoint): header equals seed total, unaffected by limit/offset, tracks
  filters. Backend suite 23/23 locally.
- Documented in README API table. Header (vs body envelope) chosen so existing
  clients keep working; per SPRINT-PLAN-FABLE5 Theme A.

## Delivered previously (slice)
**Benchmark detail page.**
- New `frontend/src/pages/BenchmarkDetail.tsx` at route `/benchmarks/:id`
  (registered in `App.tsx`) — full single-benchmark breakdown; reuses
  `BandwidthBadge` and the previously-unused `MemoryLabel`; loading /
  invalid-id / 404 states.
- Wired the dead "View →" links (`Dashboard.tsx`) and leaderboard system names
  (`Leaderboard.tsx`) to the detail route.
- Completed the `Benchmark` API type (`api.ts`) with `total_power_watts`,
  `watts_per_token`, `thermal_setting`, `ambient_temp_c` (API already returned
  them).
- **Done-criteria:** all met — valid id renders full detail; invalid/missing id
  handled gracefully; links navigate; eslint + build green; `GET
  /benchmarks/{id}` contract (full payload + 404) verified against a live API.
- No backend changes.

## Gates / sign-off
- ADRs written: none (routine SPA route; repo has no ADR system).
- Sign-off gate: none crossed; nothing halted.

## Open / deferred (from project spec, not yet built)
- **Optimized-inference tracking** (TSD §7): `effective_model_size_gb` vs raw,
  "optimized only" filter — larger, touches the data model.
- **Frontend test runner** (Vitest + React Testing Library) — the FE unit-test
  gate is plain `node --test` over pure lib modules; no component tests.
- **Frontend pagination UI** consuming the `X-Total-Count` header on the
  Leaderboard/Dashboard tables.

## Next recommended step
Frontend pagination UI (consume `X-Total-Count`), or move to sprint-plan
Theme C (model tracker sync) if hardware-side polish is deprioritized.
