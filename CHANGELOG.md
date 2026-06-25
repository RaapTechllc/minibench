# Changelog

All notable changes to MiniBench are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
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
