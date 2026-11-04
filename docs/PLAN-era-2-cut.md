# Plan: Era 2 cut (handoff brief)

Reset the product surface to one story without discarding the measurement code. Companion to [PLAN-benchmark-lens.md](PLAN-benchmark-lens.md) and [ADR 0004](adr/0004-benchmark-lens.md). Inventory verified against `main` at `f9e2b31` on 2026-09-14.

## Authority and boundary

- Owner goal, verbatim intent: a tool to keep up with model performance that other engineers also find useful, "not slop charts".
- This is a deletion-heavy series inside the existing repository. It is not a rewrite. Git history and the `archive/2026-09-04/*` tags preserve everything removed.
- Hard invariants stand: no credentials, no dry-run or synthetic data labelled live, no paid model calls, no deploy or publication without owner authorization. The DB drop migration (E2.5) runs in production only on the owner's explicit go.
- Each step is one PR that leaves all CI jobs green. Steps are ordered so keepers never depend on something already deleted.

## Product definition for Era 2

MiniBench answers one question: **which model-plus-harness can finish my work, at what cost and speed, and how much should I trust the number.** Three surfaces, one rule set.

| Surface | Role | Freshness source |
|---|---|---|
| Benchmark Lens `/lens` (new, see Lens plan) | External agentic benchmarks with provenance tiers, saturation, flags, Pareto view, private "my index". This is how you keep up with the frontier weekly. | Curated ledger or OpenRouter poll, `as_of` per row |
| Agent Cabinet `/agent-cabinet` | MiniBench's own stateful real-work measurements with receipts. This is the proof layer. | Published runs, newest first |
| Solo `/models` and Multiplayer `/agents` | Cheap screening and MoA configurations; the model-release feed (`/api/v1/agents/models/new`) lives here. | `known_models` catalog + published runs |
| Usage Board `/usage` | What the market is actually running, priced, cited. | Mode A poll |

### "Not slop" acceptance rules

These apply to every chart, table, and number on every kept or new page, and become a checklist item on the PR template.

1. Every number has a visible source and `as_of` (MiniBench run id, OpenRouter citation, or Lens claim citation). No uncited number ships.
2. No MiniBench-computed composite across benchmarks or surfaces. Third-party indexes appear under their own name with citation.
3. Provenance tier or evaluation class is visible wherever rows are sorted together (`standardized` / `self-reported`, `live-local` / `injected-transport`, `Live poll` / `Fixture / cache`).
4. Saturated benchmarks and ceiling items are collapsed by default and say why.
5. A chart must answer a decision. If the caption cannot name the decision it informs ("pick X over Y when budget is under Z"), the chart is cut.
6. Every leaderboard row links to the evidence (run detail, standardized leaderboard URL, or claim source).
7. Freshness is a first-class element: each surface shows its `as_of` in the header, and the landing page shows "what changed" since the previous snapshot.

## Keep / delete inventory

### Delete

| Area | Items |
|---|---|
| Frontend pages | `Dashboard.tsx` (current `/`), `Hardware.tsx`, `Submit.tsx`, `Compare.tsx`, `BenchmarkDetail.tsx`, `Leaderboard.tsx` (unmounted), `LegacyLeaderboardRedirect.tsx`, `MoaCalculator.tsx` (default decision; see below) |
| Frontend components / libs / tests | `components/BandwidthBadge.tsx`, `components/MemoryLabel.tsx`, `lib/submitForm.js` + `.d.ts`, `lib/bandwidth.ts`, `lib/legacyNotice.ts`, `lib/moaCalculator.js`, `tests/submitForm.test.mjs`, `tests/moaCalculator.test.mjs`; `api.ts` functions `getModels`, `getOpenRouterCompare` (dead), plus all hardware types |
| Nav | Overview `/`, Test Rigs `/hardware`, MoA Calculator |
| Backend routes (`main.py`) | `POST /api/v1/submit`, `GET /api/v1/benchmarks`, `/benchmarks/{id}`, `/leaderboard`, `/hardware`, `/profiles`, `/compare`, `/stats`, `/models` |
| Backend models / schemas | `Benchmark`, `HardwareSpec`, `ReferenceProfile`, `ModelQuality`; schemas `BenchmarkSubmit`, `BenchmarkResponse`, `HardwareSpecResponse`, `ReferenceProfileResponse`, `ModelQualityResponse`, `LeaderboardEntry`, `CompareResponse`, `StatsResponse` |
| Seed | `seed_hardware_specs`, `seed_model_quality`, `seed_reference_profiles`, `seed_benchmarks` |
| Backend tests | `tests/test_api.py` (hardware routes); one assertion in `test_agent_cabinet_api.py` that pokes `/api/v1/leaderboard` |
| CLI | entire `cli/` package, CI job `cli`, the `cli` venv block in `scripts/setup-dev.sh` |
| Root prototype | `benchmarks/` directory and the CI step `pytest -q benchmarks/tests` |
| Root docs | `TSD.md`, `SPRINT-1.md`, `SPRINT-PLAN-FABLE5.md`, `TASK-BRIEF.md`, `tickets.md`, `eras/` → moved to `docs/archive/` with a one-line index, not deleted |

### Keep untouched

`agentbench/` entire package (including `catalog.py` and `resources.py`, which are not hardware code), `KnownModel` + `seed_known_models` + `backend/app/data/known_models_seed.json`, `AgentRun` / `AgentTaskResult`, all `AgentCabinet*`, all three existing migrations, `/health`, `openrouter_board.py`, `docker-compose.yml`, `.github/workflows/openrouter-board.yml`.

### Keep with edits

`Models.tsx` (remove retired-hardware notice and Test Rigs link), `Methodology.tsx` (replace hardware section with Lens tiers and the "not slop" rules), `UsageBoard.tsx` (drop the "Not the Mini PC hardware board" wording), `README.md`, `AGENTS.md`, `CONTEXT.md`, `CHANGELOG.md` (edit, never wipe), `docs/PROJECT-STATUS.md`.

## Sequence

Every step ends with the CI-equivalent commands from `AGENTS.md` passing and `git diff --check` clean. One PR per step.

**E2.1 Frontend cut and new landing.** Delete the pages, components, libs, tests and nav entries above. Replace `/` with a landing that has four blocks: a "what changed" feed (new `known_models` since last visit via `/api/v1/agents/models/new`, newest Agent Cabinet runs, Usage Board `as_of`), and one entry card per surface with its `as_of`. No charts on the landing until the Lens exists. `/leaderboard` becomes a plain `Navigate` to `/models`. Acceptance: `npm run lint && npm test && npm run build` green; `rg -i "hardware|tok/s|bandwidth|mini pc|rig" frontend/src` returns only the Methodology copy being rewritten in E2.7.

**E2.2 Remove the CLI.** Delete `cli/`, the `cli` CI job, and the `setup-dev.sh` block. Acceptance: `ci.yml` has three jobs; `./scripts/setup-dev.sh` completes.

**E2.3 Remove hardware routes.** Delete the nine `main.py` routes, `test_api.py`, and the cabinet test assertion that hits `/api/v1/leaderboard`. Keep `/health`. Add a minimal `test_health.py`. Acceptance: `cd backend && pytest` green; `curl /api/v1/hardware` returns 404.

**E2.4 Remove legacy models, schemas, seed.** Drop the four models and eight schemas; trim `seed.py` to `seed_known_models`; update `conftest.py`. Acceptance: backend tests green; `Base.metadata.tables` contains only `agent_runs`, `agent_task_results`, `known_models`, `agent_cabinet_runs`, `agent_cabinet_task_results`.

**E2.5 Drop migration.** Add `backend/migrations/2026MMDD_01_drop_legacy_hardware_tables.sql` dropping `benchmarks`, `hardware_specs`, `reference_profiles`, `model_quality` with `IF EXISTS`; extend `test_migrations.py`. Ship the file; run it in production only on owner go.

**E2.6 Remove the `benchmarks/` prototype.** Delete the directory and the CI drift step. Move `benchmarks/AGENT-BENCH-BRIEF.md` and `REPORT.md` to `docs/archive/benchmarks-prototype/`. Acceptance: agentbench CI job green; `rg "benchmarks/" agentbench docs README.md` shows only archive references.

**E2.7 Docs and copy.** Move the five root markdown files and `eras/` to `docs/archive/` with `docs/archive/README.md` listing each with one line and its era. Rewrite `README.md` around the three surfaces (delete CLI, Legacy hardware metrics, Submission validation sections; add the missing `/api/v1/agents/*` rows to the API table). Rewrite the `Methodology.tsx` hardware section. Trim `AGENTS.md` (`minibench run` line), `CONTEXT.md` (hardware glossary rows), and add the seven "not slop" rules to `CONTEXT.md` under Anti-patterns. Update `PROJECT-STATUS.md` so the surface table matches the tree. Acceptance: `rg -i "mini pc|tok/s|HEI|bandwidth" README.md AGENTS.md CONTEXT.md` empty.

**E2.8 PR template.** Add `.github/PULL_REQUEST_TEMPLATE.md` with the seven rules as a checklist plus "which decision does each new chart inform?". This is the mechanism that keeps slop from returning.

Then the Lens plan Phases 1 through 3 land on the cleaned tree, and the landing page gains its first chart: the Pareto scatter from `/api/v1/lens/front`.

## Owner decisions

1. **MoA Calculator.** Default: delete. It is a pure client-side calculator with no cited data behind it, which fails rule 1. Keep it only if you use it; if kept, it must show the pricing `as_of` from the Usage Board.
2. **`/leaderboard` redirect.** Default: keep a redirect to `/models` for six months for inbound links, then remove.
3. **Production drop migration timing (E2.5).** File ships with the series; execution needs your go.
4. **Archive vs delete for root docs.** Default: move to `docs/archive/`. Say so if you prefer outright deletion and reliance on git history.

## What this does not do

It does not change any measured result, receipt, grader, or statistic. It does not touch `agentbench/`. It does not deploy. It does not start the Lens; it clears the ground so the Lens is the first new thing users see rather than the ninth tab.
