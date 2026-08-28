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
| **Real-Work Agent Cabinet** | Distinct board for published agent-harness runs (`/api/v1/agent-cabinet`). Completion, category completion, cost, and latency — never mixed with Solo or Multiplayer scores and never folded into a composite. |
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

## OpenRouter Usage Board (Mode A)

A daily-fresh **republisher** of OpenRouter's public Data API. Not a Mini PC hardware board, not an Arena clone, not a live inference proxy.

| Term | Meaning |
|------|---------|
| **Usage Board** | Joined view of usage, price, official eval, and task share for OpenRouter models. Headline product for "what should I call today?" |
| **Mode A** | GET-only poll of documented Data API paths. No `/chat/completions`, no `/analytics`, no live agentbench runs. |
| **Mode B** | Hermes / paid live bench. **Parked.** Do not start. |
| **as_of** | Timestamp from OpenRouter response `meta.as_of` (or the poll's cited equivalent). Every published number carries it. |
| **Citation** | Exact string: `Source: OpenRouter (openrouter.ai/rankings), as of {as_of}. CC BY 4.0.` |
| **Recommend** | Read-only compare over the **cached** Usage Board. Inputs: `task`, `budget`, `max_latency_ms`. Returns one cited pick. Never live-calls OpenRouter. Never accepts a client-supplied key. |
| **Board path** | Runtime location of a live joined Usage Board snapshot (`OPENROUTER_BOARD_PATH`). Off the git tree. When unset or the file is missing, readers serve the committed fixture and must not label it live. |
| **Data API paths** | Only `/models`, `/datasets/rankings-daily`, `/benchmarks`, `/classifications/task`. |
| **Compare routes** | Usage Board views: **best-by-$**, **best-by-task**, **best-by-latency**. Deep-link each row to the OpenRouter model page. |
| **Blended price** | Prompt + completion token prices from `/models`, expressed per 1M tokens at a 1:3 in:out mix unless a row already publishes a single price. Used only for ranking, still cited as OpenRouter pricing. |
| **Official eval** | A score from OpenRouter `/benchmarks` (Artificial Analysis, Design Arena, or OpenRouter's own evals). Not MiniBench cabinet pass rate. |
| **Task share** | Market-share fraction from `/classifications/task` for a classification tag (e.g. `code:general_impl`). Sampled; not an absolute volume. |

## Anti-patterns (what we refuse)

| Failure | Response |
|---------|----------|
| **Saturation** | 50–75% sweet spot; Credits Rolling triggers Season 2 |
| **Irrelevance** | Practical surface; no abstract puzzle cosplay on default board |
| **Contamination** | Canaries + holdout refresh — backend only, never surfaced |
| **Gaming** | Capability vs format split in grader v3 |

## Public promise

> Scores that spread models apart on work you'd actually do — and if everyone's Credits Rolling, we're on the wrong board.
