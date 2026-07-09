# Tickets: Arcade Scorecard

Tracer bullets for the Arcade Scorecard vision. Parent spec: #19 · `docs/PRD-arcade-scorecard.md`.

Work the **frontier**: any ticket whose blockers are all done.

---

## Arcade: Scorecard module + Solo Cabinet presentation — #20

**What to build:** Scorecard presentation layer + Solo Cabinet (`/models`) with tier · score, display categories, default Hard Cabinet (`minibench-hard-v1`).

**Blocked by:** None — can start immediately.

- [ ] Scorecard module + unit tests
- [ ] Models page wired; default hard-v1; cabinet selector labels

## Arcade: v2 task scenario metadata + authoring checklist — #21

**What to build:** `scenario_type` on v2 tasks; Cursor-paste test documented in agentbench README.

**Blocked by:** None — can start immediately (parallel).

- [ ] scenario_type metadata on v2 dev slice
- [ ] Authoring checklist in README

## Arcade: item pruning release gate — #22

**What to build:** Release checklist + optional CI gate using `item_stats.py` before new season publish.

**Blocked by:** None — can start immediately (parallel).

- [ ] Release checklist document
- [ ] Optional CI/script for ceiling items

## Arcade: Solo Cabinet arcade chrome — #23

**What to build:** Dark/neon arcade styling on Models — high-score table, display font on tier/score.

**Blocked by:** #20

- [ ] Shared theme tokens
- [ ] Models leaderboard arcade chrome

## Arcade: Arcade manual + Technician mode drill-down — #24

**What to build:** Run detail as Arcade manual; Technician mode for backstage stats.

**Blocked by:** #20

- [ ] Scenario badges + display category grouping
- [ ] Technician mode toggle

## Arcade: Multiplayer Cabinet scorecard parity — #25

**What to build:** Agents page tier · score, $/quarter, arcade chrome.

**Blocked by:** #20, #23

- [ ] Tier · score on Agents
- [ ] $/quarter column label

## Arcade: Season saturation banner + Season 2 auto-promote — #26

**What to build:** Saturation banner; auto-default to v2; Classic Cabinet toggle.

**Blocked by:** #20, #23

- [ ] Saturation banner when >30% Credits Rolling
- [ ] Auto-promote default cabinet; persist manual override

---

## Dependency graph

```
#20 ──┬── #23 ──┬── #25
      │         └── #26
      ├── #24
#21 (parallel)
#22 (parallel)
```

**Start now:** #20, #21, #22
