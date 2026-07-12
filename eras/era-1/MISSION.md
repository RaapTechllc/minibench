# Era 1 — Mission

**Protocol:** [`eras/GOAL-LOOP.md`](../GOAL-LOOP.md) · **Ledger:** [`LEDGER.md`](LEDGER.md)
**Branch:** `claude/company-builder-experiment-qaaexr` · **Date:** 2026-07-10

## Mission statement

Make MiniBench's agent-benchmark product **demonstrable and trustworthy without
an API key**, and make this kind of autonomous goal run **repeatable**. The
repo holds 26 committed *live* benchmark result artifacts that no one can see:
the agents leaderboards render empty because the only publish path re-runs
suites against OpenRouter. Close that loop, then make the numbers legible
(heatmap + composite) and credible (methodology page), and encode the era
process itself so the next run starts from a command, not a prompt.

## Goals (selected in Phase 2 — evidence in the ledger)

| # | Goal | Why it wins | Verification plan |
|---|------|-------------|-------------------|
| G1 | **Offline results importer** — `python -m agentbench.import_results` publishes committed `agentbench/results/*.json` (legacy + current schema) to `POST /api/v1/agents/runs`, with the same canary/infra publish gates as `run.py`, refusing dry-run artifacts | The 26 committed result files are real live runs (`"dry_run": false`, real cost/latency/failures) but there is **no import path** — agent tables stay empty without `OPENROUTER_API_KEY`. This single tool makes the whole agents product demoable from the repo alone | Unit tests (legacy→payload mapping, gates); live: start backend, import all files, leaderboard returns rows |
| G2 | **Heatmap model leaderboard** — color-scaled per-category cells + equal-weight composite bar on `/models` | Per-category cells exist but are plain text; scanability is the #1 leaderboard UX pattern from the WOAI research (`docs/research-woaibench.md` §7) | Frontend tests for the scale/composite fns; browser screenshots (desktop + mobile) against imported data |
| G3 | **Methodology page** — user-facing `/methodology` route: graders, dual capability/format scoring, Wilson CI + pass^k, canary/contamination protocol, validity badges | Grading rigor exists only in developer docs (`agentbench/README.md`, `grading.py` docstring); users see bare numbers with no trust surface. WOAI research: methodology-first docs are why people believe a score | Content traces to repo sources; route renders; screenshots; lint/build green |
| G4 | **The goal loop itself** — `eras/GOAL-LOOP.md` protocol + `.claude/commands/goal.md` command; era artifacts under `eras/era-1/` | `.claude/audit-state.md` references `/goal` but no command exists; the owner asked for "a goal run on completion" as a standing loop | A fresh instance can start Era 2 from the command + recap seed alone |
| G0 | Hygiene: fix the red frontend lint gate (pre-existing error on main) | Gates must be green to close an era; lint currently exits 1 | `npm run lint` exits 0 |

## Explicitly rejected this era (logged, seeded for later)

- **Live model runs / tracker sync against OpenRouter** — no key in `.env`; guardrail.
- **Optimized inference (TSD §7)** — touches CLI + schema + UI + seed data at once; too big to land verified alongside G1–G4.
- **score_source / dual-score columns in the submit schema** — real gap (submit drops `pass_capability`/`pass_format`), but schema migration deserves its own era; captured in the Era 2 seed.
- **Side-by-side task output showcase** — requires surfacing `raw_output_ref` in the API first.

## Definition of done

The era-generic checklist in `GOAL-LOOP.md` applies, plus:

- Running `python -m agentbench.import_results agentbench/results/*.json --api <url>`
  against a fresh backend populates the model leaderboard with the committed
  live runs, and `/models` renders them as a heatmap with composite bars.
- `/methodology` explains every number a user can see on `/models`, with each
  claim traceable to code or docs in this repo.
- All four gates green, including the previously-red frontend lint.
- A stranger could open `eras/era-1/RECAP.md`, understand what happened in five
  minutes, reproduce the demo locally, and start Era 2 from the seed.
