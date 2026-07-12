## Parent

#19

## What to build

Bring **Multiplayer Cabinet** (`/agents`) to parity with Solo Cabinet arcade presentation. MoA config rows show **tier · score**, cost column is labeled **$/quarter**, and page chrome matches the arcade theme. Solo and Multiplayer remain separate boards — scores are not merged.

## Acceptance criteria

- [x] Agents leaderboard pass column shows tier · score via Scorecard module
- [x] Cost column header reads **$/quarter** (value still `cost_usd_per_task`)
- [x] Page header/eyebrow uses Multiplayer Cabinet framing
- [x] Arcade chrome tokens from Solo styling applied consistently
- [x] Quick picks and scatter chart still work
- [x] No changes to backend API contract

## Blocked by

- #20
- #23
