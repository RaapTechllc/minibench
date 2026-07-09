## Parent

#19

## What to build

Introduce the **Scorecard** presentation layer and wire it into the **Solo Cabinet** (`/models`). A visitor landing on Models sees **Hard Cabinet · Season 1** (`minibench-hard-v1`) by default, with each model row showing **tier · score** (e.g. `High Score · 68`) and category columns labeled **Math & Logic**, **Data Pull**, **Follow Rules**, **Write Code**. Raw `pass_rate` from the API is unchanged; tiers and labels are derived client-side per `CONTEXT.md` and ADR 0001.

## Acceptance criteria

- [ ] Pure Scorecard module exports tier mapping, category display names, scorecard formatter, cabinet config constants, and saturation evaluator
- [ ] Unit tests cover tier band boundaries, all four category mappings, unknown-key fallback, and saturation threshold (>30% at ≥81 → promote)
- [ ] Models page default suite is `minibench-hard-v1` (not v2 or core-v1)
- [ ] Leaderboard rows show tier · score instead of raw pass rate as the primary headline metric
- [ ] Category column headers use display names; sorting still works per category
- [ ] Suite selector uses cabinet names (Hard Cabinet / Season 2 / Classic Cabinet)
- [ ] Page header reflects Solo Cabinet framing
- [ ] Existing API `?suite=` query behavior unchanged; CI green

## Blocked by

None — can start immediately.
