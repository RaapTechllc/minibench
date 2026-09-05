# ADR 0001: Arcade Scorecard Vision

Scope clarification, September 4: these presentation rules apply to Solo and
Multiplayer. The original homepage priority below is historical. See
[project status](../PROJECT-STATUS.md) for the active Agent Cabinet workstream.

**Status:** accepted  
**Date:** 2026-07-09  
**Context:** Grilling session (grill-with-docs) — benchmark product direction

## Decision

MiniBench presents model capability as an **80s arcade scorecard**: tier label + pass-rate number, on a **living cabinet** that advances when models saturate.

### Score presentation

- Primary: **tier** (Insert Coin → Credits Rolling)
- Secondary: **raw pass %** on the active cabinet
- Four categories with plain names: Math & Logic, Data Pull, Follow Rules, Write Code

### Default board

- **Now:** Hard Cabinet (Season 1) = `minibench-hard-v1`
- **On saturation (>30% Credits Rolling):** auto-promote to Season 2 (`minibench-v2`) with prominent banner
- **Regression only:** Classic Cabinet = `minibench-core-v1` (toggle, not homepage)

### Living benchmark (phase 1)

1. Season rotation
2. Item pruning via discrimination stats (`item_stats.py` as release gate)
3. Private holdout refresh each season

Phase 2: generator hardness drift. Phase 3: community task pipeline.

### Task design

- Surface: rotate spreadsheet / Cursor / Slack scenarios
- Every default-board prompt passes the **Cursor-paste test**
- Grading stays alien-tech underneath; never surfaced

### UI layers

| Layer | Content |
|-------|---------|
| Surface | Tier · score + category bars |
| Arcade manual | Scenario badges, plain task names, pass/fail |
| Technician mode | CIs, pass^k, format vs capability |
| Never surfaced | Canaries, seed IDs, McNemar |

### Two cabinets, one arcade

- **Solo** (`/models`) — vibe-coder homepage
- **Multiplayer** (`/agents`) — MoA configs + $/quarter

### Aesthetic

**Arcade chrome (B):** dark/neon palette, high-score table layout, display font on scores only, readable body. No sound by default. Technician mode uses terminal/clean aesthetic.

## Rationale

- **core-v1 saturates** at 95–100% for frontier models — violates anti-saturation promise
- **hard-v1** already lands 58–87% — matches 50–75% target band
- Backend rigor (grader v3, CIs, contamination protocol) exceeds what UI exposes; gap is **translation layer**, not measurement
- Arcade framing makes difficulty evolution (Season 2) feel intentional, not embarrassing

## Consequences

### Build order

1. Tier mapping + category rename on frontend (presentation layer)
2. Default leaderboard → hard-v1
3. Arcade chrome on `Models.tsx`
4. Saturation detection → Season 2 auto-promote
5. v2 task authoring with Cursor-paste test
6. Item pruning release gate

### Out of scope (for now)

- Composite scores across suites
- Community task ingestion (phase 3)
- Full "cabinet cosplay" UI (option C aesthetic)
- Merging Solo and Multiplayer into one score

## References

- `CONTEXT.md` — glossary
- `agentbench/README.md` — measurement backend
- `docs/PIVOT-PLAN.md` — capability-first pivot (complementary)
