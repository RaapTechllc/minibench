## Parent

#19

## What to build

Add an **item pruning release gate** before publishing a new cabinet season. Wire `item_stats.py` ceiling/floor/discrimination output into a documented release checklist (and optional CI script) so tasks that 90%+ of frontier models ace do not ship in a new season.

## Acceptance criteria

- [ ] Release checklist document exists for "publish new season"
- [ ] Checklist requires running item discrimination audit and resolving ceiling items
- [ ] Optional: script or CI job fails when new season task set contains flagged ceiling items
- [ ] Holdout refresh step documented per season rotation policy in ADR 0001
- [ ] No change to live leaderboard until a season is explicitly published

## Blocked by

None — can start immediately (parallel track).
