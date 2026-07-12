# Changelog

All notable changes to MiniBench are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- **Offline results importer** — `python -m agentbench.import_results` replays
  committed `agentbench/results/*.json` artifacts to `POST /api/v1/agents/runs`
  with no provider key, applying the same honesty gates as the live publish
  path (dry-run artifacts refused unconditionally; canary-flagged runs
  refused; infra-error runs refused without `--allow-infra-errors`). A fresh
  database can now show the 26 committed live runs instead of empty
  leaderboards.
- **Heatmap model leaderboard** — `/models` category cells now carry a
  five-band color scale (85/70/55/40 boundaries), plus a sortable
  equal-weight **Composite** column with an inline bar and an on-page legend.
  Pure scale/composite logic lives in `src/lib/scoreScale.js` with node tests.
  If the default suite has no published runs, the page auto-widens to "All
  suites" once instead of opening empty (a user's explicit choice is never
  overridden).
- **Methodology page** at `/methodology` — user-facing explanation of the
  grading system: executable graders, dual capability/format scoring (grader
  v3), Wilson CIs and pass^k, contamination and gaming defenses, leaderboard
  validity gates, and an explicit "what we don't do" section. Linked from the
  site nav.
- **Era goal-loop** — `eras/GOAL-LOOP.md` protocol for autonomous,
  self-verifying goal runs that seed their successor on completion;
  `eras/era-1/` holds the first era's mission, ledger, red-team findings, and
  recap; `.claude/commands/goal.md` makes the loop invocable as `/goal`.

### Fixed
- Frontend lint error (`react-refresh/only-export-components`): the legacy
  leaderboard notice helpers moved from `LegacyLeaderboardRedirect.tsx` into
  `src/lib/legacyNotice.ts`; the `/models` page consumes the flag via a lazy
  `useState` initializer instead of a setState-in-effect.

### Added earlier
- **Benchmark detail page** at `/benchmarks/:id` — a full single-benchmark
  breakdown (performance, quality & value, hardware with System RAM vs VRAM,
  and software/run metadata). Uses the existing `GET /api/v1/benchmarks/{id}`
  endpoint and handles loading, invalid-id, and not-found states. Reuses the
  `BandwidthBadge` and (previously unused) `MemoryLabel` components.
- `Benchmark` API type now declares `total_power_watts`, `watts_per_token`,
  `thermal_setting`, and `ambient_temp_c` — fields the API already returned.

### Changed
- The "View →" links in the dashboard's recent-submissions table now open the
  benchmark detail page (previously routed to the leaderboard).
- Leaderboard rows link their system name to the benchmark detail page.

## [0.1.0] - 2026-06-21

Initial complete release: FastAPI + PostgreSQL backend, the `minibench` CLI
(with curated hardware-spec lookup), and a React/Vite dashboard — plus backend
and CLI test suites and GitHub Actions CI. Merged in PR #1.
