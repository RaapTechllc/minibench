## Parent

#19

## What to build

When the active cabinet saturates (>30% of models at **Credits Rolling**, pass rate ≥81), show a prominent **Season 2 unlocked** banner and auto-default new visitors to `minibench-v2`. Respect manual cabinet overrides (session/local storage). Classic Cabinet (`minibench-core-v1`) stays available as an explicit regression toggle, not the default.

## Acceptance criteria

- [ ] Saturation computed client-side from leaderboard entries via Scorecard module
- [ ] Banner appears when threshold met; copy uses arcade framing (e.g. "Season 1 cleared — Season 2 unlocked")
- [ ] Default cabinet switches to Season 2 (`minibench-v2`) unless user manually picked a cabinet
- [ ] Manual cabinet selection persists and is not overwritten on reload
- [ ] Classic Cabinet labeled clearly as regression / optional
- [ ] Public promise copy visible near banner or page header

## Blocked by

- #20
- #23
