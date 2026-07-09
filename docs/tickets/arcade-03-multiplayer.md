## Parent

#19

## What to build

Bring **Multiplayer Cabinet** (`/agents`) to parity with Solo Cabinet arcade presentation. MoA config rows show **tier · score**, cost column is labeled **$/quarter**, and page chrome matches the arcade theme. Solo and Multiplayer remain separate boards — scores are not merged.

## Acceptance criteria

- [ ] Agents leaderboard pass column shows tier · score via Scorecard module
- [ ] Cost column header reads **$/quarter** (value still `cost_usd_per_task`)
- [ ] Page header/eyebrow uses Multiplayer Cabinet framing
- [ ] Arcade chrome tokens from Solo styling applied consistently
- [ ] Quick picks and scatter chart still work
- [ ] No changes to backend API contract

## Blocked by

- #20
- #23
