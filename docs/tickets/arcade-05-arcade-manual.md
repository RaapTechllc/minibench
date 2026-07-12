## Parent

#19

## What to build

Upgrade run drill-down into an **Arcade manual**: default view shows scenario type badges (spreadsheet / Cursor / Slack), tasks grouped by display category with plain descriptions, pass/fail per task. **Technician mode** toggle ("HOLD START") reveals CIs, pass^k, and format vs capability split in a clean terminal aesthetic. Never surface canaries, seed IDs, or McNemar.

## Acceptance criteria

- [x] Run detail default view groups tasks by display category names (Math & Logic, etc.)
- [x] Scenario badge shown per task when `scenario_type` metadata present; sensible fallback by category
- [x] Technician mode hidden by default; toggle reveals backstage stats already in API payload
- [x] Technician mode styling contrasts with arcade surface (terminal/clean)
- [x] Canaries, seed IDs, McNemar absent from all UI modes
- [x] Navigation back to appropriate cabinet (Solo or Multiplayer) preserved

## Blocked by

- #20
