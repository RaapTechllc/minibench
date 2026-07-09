## Parent

#19

## What to build

Prepare **Season 2** task content for practical surface prompts. Add `scenario_type` metadata (`spreadsheet` | `cursor` | `slack`) to v2 task definitions where missing. Document the **Cursor-paste test** authoring rule in agentbench README so every default-board prompt feels like real work.

## Acceptance criteria

- [x] `scenario_type` field present on minibench-v2 dev-slice tasks (or documented convention for generator output)
- [x] Each v2 dev-slice prompt reviewed against Cursor-paste test
- [x] agentbench README documents authoring checklist and scenario types
- [x] Scenario types align with Arcade manual badges in drill-down ticket
- [x] No change to grader or oracle logic required for metadata-only additions

## Blocked by

None — can start immediately (parallel track).
