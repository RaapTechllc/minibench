# MiniBench — Domain Glossary

Canonical terms for the benchmark product. Use these words consistently in code, UI copy, specs, and ADRs.

## Audience

| Term | Meaning |
|------|---------|
| **Vibe coder** | Primary audience. Uses AI in Cursor/IDE daily; wants a fast model pick without reading papers. |
| **Normal dev** | Secondary audience. Same person, deeper session — wants receipts that scores predict real work. |

## Scorecard

| Term | Meaning |
|------|---------|
| **Tier** | Arcade label derived from pass rate bands (Insert Coin → Credits Rolling). Shown **above** the number. |
| **Score** | Raw pass rate (0–100) on the active cabinet. Shown **beside** the tier, e.g. `High Score · 68`. |
| **Category** | One of four frontend columns. Maps from backend grader categories (see table below). |
| **Cabinet** | A benchmark suite exposed as a leaderboard board. Not the same as a software "component". |
| **Solo Cabinet** | `/models` — single-model, pinned decoding. Homepage product. |
| **Multiplayer Cabinet** | `/agents` — MoA / multi-agent configs. Adds **$/quarter** (cost per task). |
| **Arcade manual** | Default drill-down: scenario badges, plain-English task names, pass/fail by category. |
| **Technician mode** | Optional drill-down: CIs, pass^k, format vs capability split. Backstage stats. |

### Tier bands

| Tier | Pass rate | Notes |
|------|-----------|-------|
| Insert Coin | 0–35 | Not ready for serious use |
| Warm Up | 36–50 | Getting there |
| High Score | 51–65 | Frontier sweet spot on default board |
| Boss Beaten | 66–80 | Strong |
| Credits Rolling | 81+ | Saturation signal — board may be too easy |

### Category mapping (frontend ← backend)

| Frontend | Backend (`agentbench`) |
|----------|------------------------|
| Math & Logic | `reasoning` |
| Data Pull | `tool-use` |
| Follow Rules | `instruction` |
| Write Code | `coding` |

## Boards & seasons

| Term | Meaning |
|------|---------|
| **Hard Cabinet (Season 1)** | Default homepage board today. Suite: `minibench-hard-v1`. |
| **Season 2** | Auto-promoted board when Season 1 saturates. Suite: `minibench-v2`. |
| **Classic Cabinet** | Regression view. Suite: `minibench-core-v1`. Not the vibe-coder front door. |
| **Season rotation** | New cabinet + holdout refresh when models clear the old board. |
| **Item pruning** | Drop tasks that no longer discriminate (90%+ pass across frontier). |
| **$/quarter** | Cost per task on Multiplayer Cabinet. Arcade name for `cost_usd_per_task`. |

## Tasks

| Term | Meaning |
|------|---------|
| **Surface prompt** | What the model (and user on drill-down) sees. Must feel like real work. |
| **Alien grading** | Procedural generation, executable oracles, canaries, private holdouts — never marketed on surface. |
| **Cursor-paste test** | Task authoring rule: "Would I paste this prompt into Cursor?" If no, rewrite surface. |
| **Scenario type** | Surface badge: spreadsheet worker, Cursor session, or Slack message. |

## Anti-patterns (what we refuse)

| Failure | Response |
|---------|----------|
| **Saturation** | 50–75% sweet spot; Credits Rolling triggers Season 2 |
| **Irrelevance** | Practical surface; no abstract puzzle cosplay on default board |
| **Contamination** | Canaries + holdout refresh — backend only, never surfaced |
| **Gaming** | Capability vs format split in grader v3 |

## Public promise

> Scores that spread models apart on work you'd actually do — and if everyone's Credits Rolling, we're on the wrong board.
