# Era 1 — Ledger

Single source of truth for this era. Handoff format: a fresh instance with only
this file must reach full speed. Protocol: [`eras/GOAL-LOOP.md`](../GOAL-LOOP.md).

**Branch:** `claude/company-builder-experiment-qaaexr` · **Started:** 2026-07-10
**Environment:** Claude Code remote container (linux). Postgres 16 native (no
Docker). Node 22.22.2, Python 3.11.15. **No `.env` exists → no
`OPENROUTER_API_KEY` → no live model runs this era; everything ships
offline-verified and labeled.**

---

## Phase 0 — Bootstrap (complete)

### State proven by commands

- Postgres 16 cluster started (`sudo pg_ctlcluster 16 main start`), role
  `minibench` (password `minibench`, CREATEDB) + databases `minibench`,
  `minibench_test` created on **localhost:5432** (not the README's 5438).
- `./scripts/setup-dev.sh` → SETUP_OK: venvs at `backend/.venv`, `cli/.venv`,
  `agentbench/.venv`; `frontend/node_modules` via npm ci; `.env`,
  `backend/.env`, `agentbench/.env` created from examples (keys empty).
- Baseline gates: see table below; raw logs committed at
  [`gates/`](gates/) (`.txt` because the frontend `.gitignore` ignores `*.log`).

### Baseline gates (run 2026-07-10; logs in session scratchpad `gate-*.log`)

| Gate | Command | Status |
|------|---------|--------|
| backend | `cd backend && MINIBENCH_TEST_PG_HOST=127.0.0.1 MINIBENCH_TEST_PG_PORT=5432 .venv/bin/pytest` | ✅ exit 0 |
| cli | `cd cli && .venv/bin/pytest` (pytest had to be pip-installed into `cli/.venv` — setup script installs only `-e .`) | ✅ exit 0 |
| agentbench | `agentbench/.venv/bin/pytest agentbench` (from repo root) | ✅ exit 0 |
| agentbench dry-run | `agentbench/.venv/bin/python -m agentbench.run --config agentbench/presets/moa-v1.yaml --tasks agentbench/tasks/coding-v1.json --trials 2 --dry-run` (repo root) | ✅ exit 0 |
| frontend test/build | `cd frontend && npm test && npm run build` | ✅ exit 0 |
| frontend lint | `cd frontend && npm run lint` | ❌ **exit 1 — pre-existing on main**: 1 error (`react-refresh/only-export-components`, `LegacyLeaderboardRedirect.tsx:15`) + 5 `react-hooks/set-state-in-effect` warnings. Fixing the error is goal G0. |

### Landmines

- Backend tests default to Postgres port **5438**; always override with
  `MINIBENCH_TEST_PG_HOST=127.0.0.1 MINIBENCH_TEST_PG_PORT=5432`.
- Postgres is **not** auto-started; restart with `sudo pg_ctlcluster 16 main start`.
- agentbench must run as a module **from the repo root** with
  `agentbench/.venv/bin/python -m agentbench.run ...`.
- `benchmarks/` is legacy — do not build on it; `agentbench/` is the path.
- No Ollama daemon here → `minibench run` can't execute; create hardware data
  via `POST /api/v1/submit`.

## Phase 1 — Recon (complete; 2 parallel scout agents, findings verified against code)

**Gap verifier findings (file:line evidence in agent report):**

- Tracker automation: PARTIAL — `--publish` *does* flip `benchmarked`
  (`agents_router.py:113-128`, tested), but `tracker.py` has no caller/DB
  writer; catalog sync is a manual seed-file regen.
- Methodology docs: PARTIAL — developer docs exist (`agentbench/README.md`,
  `grading.py:1-41` docstring); **no user-facing page or route**.
- Heatmap leaderboard: PARTIAL — `Models.tsx:297-301` renders per-category
  cells as plain text; no color scale, no composite bar.
- score_source / dual-score in UI: OPEN — `to_agent_run_submit`
  (`run.py:344-385`) **drops** `pass_capability`/`pass_format`; schema has no
  such fields; only `is_private_split` badge exists (`ui.tsx:81-86`).
- Custom weights, optimized inference (TSD §7), side-by-side showcase: OPEN.
- Frontend tests: two pure-lib node tests only; no component tests.
- `.claude/`: only `audit-state.md`; the `/audit` & `/goal` commands it
  references **do not exist**.

**Pipeline mapper findings (the decisive ones):**

- All 26 committed `agentbench/results/*.json` are **real live runs**
  (`"dry_run": false`, real cost/latency, model-specific failure details) in
  the **legacy schema** (no `grader_version`/`provenance`/`passed_format`).
- **No offline import path exists**: `--publish` only fires after executing a
  run; nothing reads `results/*.json` back. Key-free `--dry-run --publish`
  would publish meaningless StubModel numbers. The backend POST itself needs
  no provider key → a standalone importer is feasible and is the missing link.
- `agent_runs`/`agent_task_results` are **never seeded**; leaderboards are
  empty out of the box. `known_models` *is* seeded (42 ids, `benchmarked=False`).
- Publish gates in `run.py:554-563`: refuse on canary flags; refuse on infra
  errors without `--allow-infra-errors`. Importer must mirror these.
- Suites `minibench-core-v1` / `minibench-v2`: 20 tasks each, 4 categories × 5
  (reasoning, tool-use, instruction, coding).

## Phase 2 — Goal selection (complete)

Goals G0–G4 locked in [`MISSION.md`](MISSION.md) with per-goal evidence, value
case, and verification plan. Rejected candidates + reasons also in MISSION.md;
the score_source schema gap and tracker sync go into the Era 2 seed.

## Phase 3 — Build (complete; all gates green)

**G1 — importer** (`agentbench/import_results.py` + `agentbench/tests/test_import_results.py`):
reuses `to_agent_run_submit`/`publish_run` from `run.py` (single source of
payload truth); honesty gates mirrored (dry-run refused with *no* override,
canary refused, infra refused sans `--allow-infra-errors`); legacy artifacts
fill grader-v3 fields with dataclass defaults, unknown future keys dropped.
**Verified live:** backend on :3070 (fresh DB) → `26 published, 0 refused, 0
failed` → `GET /api/v1/agents/models/leaderboard` returns 22 rows with
per-category rates. The one refusal during development was my own untracked
dry-run artifact from the baseline gate — the gate caught it (deleted; the
drift-guard test now filters local dry-run files explicitly).

**G2 — heatmap** (`frontend/src/lib/scoreScale.js` + `.d.ts`, tests, `Models.tsx`,
`ui.tsx` SortableTh `title` prop): five bands (85/70/55/40 boundaries — adapted
from the WOAI heatmap pattern, `docs/research-woaibench.md`), missing data gets
no tint; sortable equal-weight Composite column with inline bar; legend row.
**Screenshot-verified** desktop 1440px + mobile 390px, zero console errors.

**G3 — methodology page** (`frontend/src/pages/Methodology.tsx`, route + nav in
`App.tsx`; built by a delegated agent with a source-map requirement): every
section traces to repo sources (agentbench README/grading/stats/run, agents_router,
ui.tsx, TSD.md, README.md). Screenshot-verified desktop + mobile.

**G4 — goal loop** (`eras/GOAL-LOOP.md`, `.claude/commands/goal.md`): protocol +
invocable `/goal` command; closes the recon finding that `audit-state.md`
references commands that never existed.

**G0 — lint fix**: notice helpers → `frontend/src/lib/legacyNotice.ts`;
`Models.tsx` consumes via lazy `useState` initializer. Lint: **exit 0** (was
exit 1 on main), 4 pre-existing warnings remain in untouched files (Agents,
Compare, Dashboard, Hardware).

**Docs:** README (importer + refreshed stale routes table), agentbench/README
(re-publishing section), CHANGELOG (Unreleased).

### Final gates (all exit 0)

backend 27 passed · cli 12 passed · agentbench **165 passed** (incl. 11 new
importer tests) · dry-run smoke ok (artifact deleted after) · frontend lint 0
errors · frontend tests **18 passed** (incl. 6 new scoreScale) · build ok.

### Phase-3 decisions

| # | Question | Decision | Why |
|---|----------|----------|-----|
| D5 | Default suite `minibench-v2` has no published runs → `/models` opens empty even after import. Change the default? | Keep the default, add a **one-shot auto-widen** to "All suites" when the default returns 0 rows and the user hasn't touched the filter. | The v2-first default was a deliberate prior choice (frontier tier + core saturation notice); overriding a user's explicit selection would be worse than an empty page, but an empty first paint with 22 importable runs is worst of all. |
| D6 | Importer: block re-imports (backend has no dedup)? | No client-side dedup this era; documented the duplication behavior in agentbench/README. | No list-runs endpoint exists to check against; the model leaderboard takes best-run-per-model so duplicates don't corrupt rankings. Server-side idempotency belongs in the Era 2 seed. |
| D7 | Allow importing dry-run artifacts behind a flag? | No — refuse unconditionally, no override flag. | Stub data on a public leaderboard is exactly the "silent bad data" failure the product exists to avoid; run.py's own gate philosophy extended. |

## Decisions log (questions I would have asked, answered myself)

| # | Question | Decision | Why |
|---|----------|----------|-----|
| D1 | What does "apply this mentality to Minibench / goal run on completion" mean concretely? | Build a reusable era protocol (`eras/GOAL-LOOP.md`) **and** execute Era 1 under it end-to-end, closing with a seeded Era 2. | The inspiration brief's core mechanics are: autonomous goal run, ledger, adversarial verification, definition of done, recap. "Goal run on completion" = each era's recap seeds the next — encoded as protocol step, not a one-off. |
| D2 | Where do era artifacts live? | Top-level `eras/era-N/`. | Mirrors the brief's `run-N` convention; `docs/` is user-facing product docs, `.claude/` is tool state — a first-class process deserves a first-class directory. |
| D3 | Can this era include live model benchmark runs? | No. | No `OPENROUTER_API_KEY` in any `.env`; guardrail forbids new signups/spending. Everything demonstrable must work from committed result artifacts, seeds, and dry-runs — labeled as such. |
| D4 | Which branch? | `claude/company-builder-experiment-qaaexr` (assigned). | Session instruction; never push elsewhere. |

## Phase 4 — Red team (complete; findings + resolutions in [RED-TEAM.md](RED-TEAM.md))

Two adversarial agents launched in parallel after the build commit:

1. **Code skeptic** — instructed to refute 8 claims (importer honesty gates,
   payload fidelity, heatBand/composite correctness, auto-widen safety, lint-fix
   behavior parity, methodology accuracy, era-doc facts, CI compatibility) with
   REFUTED as the default verdict. **This agent was killed mid-run by a session
   usage limit**; the same claim list was then re-run inline (direct code reads
   + commands) — 3 defects found and fixed (RT-1..RT-3 in RED-TEAM.md), plus a
   regression test (agentbench suite 165 → 166).
2. **Completeness critic** — graded the era against both definition-of-done
   checklists; produced an 11-item punch list and committed the mechanical
   fixes itself (gate artifacts, setup-dev pytest, audit-state cleanup, push +
   draft PR #29).

Punch-list items fixed immediately: screenshots + gate logs moved from a
wrong-cwd `frontend/eras/` into `eras/era-1/` (logs renamed `.txt` — the
frontend `.gitignore` swallows `*.log`); branch pushed; draft PR #29 opened;
`scripts/setup-dev.sh` now installs pytest into `cli/.venv` (the gate landmine
a stranger would hit); this in-flight section refreshed. Remaining items
(RECAP.md, RED-TEAM.md, era index flip, fresh-agent audit) close in Phase 5/6.

## In-flight

- Code-skeptic red-team agent (Phase 4, claim-by-claim verdicts) — findings
  land in RED-TEAM.md when it returns.
- Draft PR: https://github.com/RaapTechllc/minibench/pull/29 (subscribed to CI
  + review events).

## Verify-first (for a resuming instance)

1. `pg_isready` — if down, start Postgres (see landmines).
2. `git status` on branch `claude/company-builder-experiment-qaaexr`.
3. Read this ledger top to bottom, then `eras/era-1/MISSION.md` (written after
   Phase 2 goal selection).
