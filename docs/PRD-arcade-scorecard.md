# Spec: Arcade Scorecard — Practical Benchmarks, Alien Grading

**Status:** ready-for-agent  
**Date:** 2026-07-09  
**ADR:** `docs/adr/0001-arcade-scorecard-vision.md`  
**Glossary:** `CONTEXT.md`

---

## Problem Statement

MiniBench's capability leaderboard shows raw pass rates that saturate near 100% on the default suite (`minibench-core-v1`), making frontier models indistinguishable. The measurement backend is rigorous, but the presentation reads like a research dashboard — pass %, CI bars, backend category slugs (`reasoning`, `tool-use`) — which vibe coders and normal developers cannot interpret in five seconds. Users cannot tell which model to use, whether scores mean anything, or when the benchmark itself has been outgrown. This creates a "false benchmark" feeling similar to saturated public leaderboards: numbers look precise but do not spread models apart on work that feels real.

## Solution

Present model capability as an **80s arcade scorecard**: a tier label plus pass-rate number on a **living cabinet** (benchmark suite) that advances when models saturate. Keep alien-tech grading underneath (procedural tasks, executable oracles, contamination controls); translate only what users see. Default the Solo Cabinet to **Hard Cabinet (Season 1 / `minibench-hard-v1`)**, where frontier models already land in the 50–75% band. When too many models hit **Credits Rolling** (81%+), auto-promote the default board to **Season 2 (`minibench-v2`)** with a loud banner. Offer Classic Cabinet (`minibench-core-v1`) as a regression toggle, not the homepage. Apply the same tier vocabulary to Multiplayer Cabinet (`/agents`) with an added **$/quarter** (cost per task) column.

---

## User Stories

### Vibe coder — Solo Cabinet

1. As a vibe coder, I want to see a tier name and score at a glance (e.g. `High Score · 68`), so that I can pick a model without reading benchmark papers.
2. As a vibe coder, I want category columns named in plain English (Math & Logic, Data Pull, Follow Rules, Write Code), so that I understand what the model is good at.
3. As a vibe coder, I want the homepage to default to a board where top models score 50–75%, so that the leaderboard spreads models apart instead of showing everyone at 99%.
4. As a vibe coder, I want a neon "Season 2" banner when the current board is saturated, so that I trust MiniBench is still honest as models improve.
5. As a vibe coder, I want drill-down to show scenario badges and plain task descriptions, so that scores feel connected to work I'd paste into Cursor.
6. As a vibe coder, I want arcade-styled visuals (dark/neon, high-score table) without sacrificing readability, so that the product has personality but remains trustworthy.
7. As a vibe coder, I want to switch to Classic Cabinet only if I explicitly choose it, so that I am not misled by easy scores on the default view.

### Normal dev — receipts

8. As a normal dev, I want the numeric pass rate visible beside the tier, so that I can compare models precisely when the label alone is not enough.
9. As a normal dev, I want a Technician mode toggle on drill-down showing CIs, pass^k, and format vs capability split, so that I can verify scores without cluttering the default view.
10. As a normal dev, I want saturation explained as "wrong board" not "models are perfect", so that I understand methodology rather than suspect marketing.
11. As a normal dev, I want category breakdowns to map cleanly to backend grader categories, so that I can trace a displayed score to measurement logic.
12. As a normal dev, I want confidence intervals still available in Technician mode, so that sample-size uncertainty is not hidden.

### Power user — Multiplayer Cabinet

13. As a power user, I want MoA configs on a separate Multiplayer Cabinet with the same tier vocabulary, so that solo and multi-agent scores are not confused.
14. As a power user, I want cost per task labeled **$/quarter** on Multiplayer Cabinet, so that I can optimize accuracy per dollar in the same arcade framing.
15. As a power user, I want to navigate between Solo and Multiplayer cabinets without losing the arcade chrome, so that the product feels cohesive.

### Operator — living benchmark

16. As an operator, I want Season 1 to use `minibench-hard-v1` until v2 is populated, so that we ship a honest board immediately.
17. As an operator, I want auto-promotion to Season 2 when >30% of models on the active board are Credits Rolling, so that saturation triggers action not disclaimers.
18. As an operator, I want item-pruning stats (`item_stats.py`) as a release gate before publishing a new season, so that tasks that 90%+ of frontier models ace do not ship.
19. As an operator, I want private holdout refresh each season, so that contamination cannot accumulate across seasons.
20. As an operator, I want v2 task prompts to pass the Cursor-paste test, so that surface prompts feel like spreadsheet, Cursor, or Slack work.

### Trust & anti-patterns

21. As a visitor, I want the public promise visible in product copy — scores spread models on real work; Credits Rolling means wrong board — so that I trust MiniBench over saturated leaderboards.
22. As a visitor, I want canaries, seed IDs, and McNemar stats never shown in the UI, so that rigor exists without nerd intimidation.
23. As a visitor, I want format-gaming separated from capability in Technician mode, so that models cannot score well by tricks alone.
24. As a maintainer, I want tier bands defined in one place, so that Solo Cabinet, Multiplayer Cabinet, and future surfaces stay consistent.
25. As a maintainer, I want cabinet config (suite id, season label, saturation threshold) centralized, so that Season 3 does not require hunting magic strings across pages.

### Arcade manual drill-down

26. As a user clicking a model row, I want an Arcade manual view with scenario type badges, so that I see whether a task was spreadsheet, Cursor, or Slack shaped.
27. As a user, I want per-task pass/fail grouped by display category, so that I can see where a model failed in plain language.
28. As a user, I want Technician mode hidden behind an explicit toggle ("HOLD START for Technician mode"), so that backstage stats are opt-in.

### Season migration

29. As a returning user, I want Classic Cabinet available as a toggle labeled clearly (regression / Season 0), so that historians can compare without polluting the default.
30. As a returning user, I want the active season name shown in the page header (e.g. "Hard Cabinet · Season 1"), so that I know which board I am viewing.
31. As a returning user, I want Season 2 promotion to preserve tier names and score semantics, so that scores remain comparable across seasons in meaning if not in absolute value.

### Accessibility & polish

32. As a user, I want body text in a readable font with arcade display font only on tier/score, so that neon styling does not hurt legibility.
33. As a user, I want no autoplay sound, so that the arcade theme works in open offices.
34. As a user with color-only vision constraints, I want tier conveyed by label text not color alone, so that Insert Coin vs High Score does not rely on hue.

### API & data (minimal change)

35. As a frontend consumer, I want to derive tiers client-side from raw `pass_rate`, so that the backend API contract stays stable and ADR 0001 is honored.
36. As a backend maintainer, I want leaderboard endpoints to continue returning raw pass rates and backend category keys, so that agentbench artifacts need not change for phase 1.
37. As a publisher, I want suite selection in the UI to map to existing `benchmark_suite` query params, so that published runs appear on the correct cabinet without migration.

### Future-facing (documented, not built here)

38. As a future contributor, I want generator hardness drift documented as Season 3 tooling, so that the living-benchmark path is clear.
39. As a future contributor, I want community task ingestion documented as phase 3, so that crowdsourced MiniBench brand can extend tasks without blocking Season 2.

---

## Implementation Decisions

### Proposed seam (single primary test boundary)

Introduce a **Scorecard module** in the frontend — pure functions + constants, no React. All arcade presentation flows through it:

| Input | Output |
|-------|--------|
| `pass_rate` (0–100) | `tier` (Insert Coin … Credits Rolling) |
| Backend category key | Display category label |
| Leaderboard entries + active cabinet config | `saturationState` (ok / warning / promote) |
| Cabinet id | Season label, display name (Hard Cabinet, etc.) |

**Pages consume Scorecard; pages do not embed tier logic.** This is the highest seam: one module, unit-tested, shared by Solo Cabinet, Multiplayer Cabinet, and RunDetail drill-down.

No backend schema changes in phase 1. Optional phase 2: `GET /api/v1/cabinets/active` returning default suite + season metadata — out of scope until client-side saturation proves insufficient.

### Tier mapping

- Five tiers per `CONTEXT.md` bands; boundary inclusive on lower bound (e.g. 51–65 → High Score).
- Score displayed as integer or one-decimal pass %; tier derived independently (68% → Boss Beaten, not High Score).
- Export `tierFromPassRate(n: number): Tier` and `formatScorecard(passRate: number): { tier: string; score: number }`.

### Category mapping

- Fixed map: `reasoning` → Math & Logic, `tool-use` → Data Pull, `instruction` → Follow Rules, `coding` → Write Code.
- Unknown backend keys pass through title-cased or grouped under "Other" — should not occur on minibench suites.
- Sort/display order fixed: Math & Logic, Data Pull, Follow Rules, Write Code.

### Cabinet configuration

- **Default active cabinet:** `minibench-hard-v1` (Hard Cabinet · Season 1).
- **Season 2 cabinet:** `minibench-v2` — promoted when saturation threshold met.
- **Classic cabinet:** `minibench-core-v1` — manual toggle only.
- **Saturation rule:** >30% of entries on active cabinet have `pass_rate >= 81` → set default cabinet to Season 2 and show banner. Banner copy: "Season 1 cleared — Season 2 unlocked" (or equivalent arcade framing).
- Persist user's manual cabinet override in session/local storage; do not fight explicit user choice.

### Solo Cabinet (`/models`)

- Replace default suite state from `minibench-v2` to `minibench-hard-v1`.
- Replace "Overall pass rate" column with **Tier · Score** presentation; keep CI bar in Technician mode or subordinate row.
- Rename suite selector labels to cabinet names (Hard Cabinet, Season 2, Classic Cabinet).
- Update page header eyebrow/title to arcade framing ("Solo Cabinet" / "Hard Cabinet · Season 1").
- Retain Pareto scatter; Y-axis may show pass rate or tier ordinal — prefer pass rate for chart accuracy.
- Remove or replace core-v1 saturation banner logic with cabinet-aware saturation from Scorecard module.

### Multiplayer Cabinet (`/agents`)

- Apply tier · score formatting to pass rate column.
- Rename cost column header to **$/quarter**.
- Align page chrome with Solo Cabinet (arcade palette, cabinet naming).
- Do not merge leaderboards.

### Arcade manual + Technician mode (RunDetail / model drill-down)

- Default view: scenario badge per task (derive from task metadata when present; fallback icon by category).
- Group tasks by **display** category names.
- Technician mode toggle reveals: CI, pass^k, `pass_format` vs capability if available in run detail payload, trial counts.
- Technician mode uses terminal/clean styling contrasted with arcade surface.

### Arcade chrome (visual)

- Dark background, neon accent (cyan/magenta or existing frontier accent evolved), subtle scanline or grid optional.
- High-score table row styling for leaderboard.
- Display font for tier + score only; body remains current sans stack.
- No sound.

### Task authoring (Season 2 / v2 — separate implementation track)

- Add `scenario_type` metadata to task definitions where missing: `spreadsheet` | `cursor` | `slack`.
- Authoring checklist: Cursor-paste test documented in agentbench README.
- Item pruning gate: document in release checklist; wire `item_stats.py` ceiling report as blocking step before season publish.

### Backend

- **No API contract changes phase 1.** Leaderboard continues returning `pass_rate`, `category_pass_rates` with backend keys, `benchmark_suite`.
- Ensure `minibench-hard-v1` runs exist in DB or document seed/publish path for demo data.

---

## Testing Decisions

**Principle:** Test external behavior of the Scorecard module only — not React component internals or CSS.

### Scorecard module unit tests (new)

- `tierFromPassRate` at band boundaries: 35→Insert Coin, 36→Warm Up, 50→Warm Up, 51→High Score, 65→High Score, 66→Boss Beaten, 80→Boss Beaten, 81→Credits Rolling, 100→Credits Rolling.
- `categoryDisplayName` for all four known keys + unknown fallback.
- `evaluateSaturation(entries, threshold)` returns `promote` when >30% at ≥81, `ok` otherwise.
- `formatScorecard(68)` → `{ tier: 'Boss Beaten', score: 68 }` (or rounded per display rule).

**Prior art:** `frontend/tests/moaCalculator.test.mjs`, `frontend/tests/submitForm.test.mjs` — Vitest or node test runner pattern already in frontend.

### Integration / smoke

- Models page loads with default suite `minibench-hard-v1` (manual or Playwright later).
- Suite toggle still fetches correct API `?suite=` param.

### Not tested in phase 1

- Pixel-perfect arcade styling.
- Season 2 auto-promote E2E (until v2 entries exist in test DB).

### Backend tests

- No changes expected; existing `test_agents_api.py` leaderboard tests remain valid.

---

## Out of Scope

- Composite scores across suites.
- Backend-computed tiers in API responses.
- Community task submission pipeline.
- Generator auto-hardness drift (Season 3 tooling).
- Full cabinet cosplay UI (animated CRT, sound).
- Merging Solo and Multiplayer into one leaderboard.
- Rewriting agentbench graders or task generators (except v2 metadata/scenario_type as follow-on).
- McNemar, canary, or seed ID surfacing in any UI mode.
- Hardware benchmark page restyling (tokens/sec leaderboard remains separate product).

---

## Further Notes

### Build order (tracer bullets for `/to-tickets`)

1. **Scorecard module + unit tests** — tier, categories, saturation, formatters.
2. **Solo Cabinet default + presentation** — Models page consumes Scorecard; default hard-v1.
3. **Arcade chrome pass** — shared theme tokens, table styling, fonts.
4. **Multiplayer Cabinet parity** — Agents page tier + $/quarter.
5. **Saturation banner + Season 2 auto-default** — client-side promotion logic.
6. **Arcade manual drill-down** — RunDetail scenario badges + Technician toggle.
7. **v2 task metadata + authoring checklist** — scenario_type, Cursor-paste test docs.
8. **Item pruning release gate** — item_stats integration in docs/CI.

### Public promise (copy)

> Scores that spread models apart on work you'd actually do — and if everyone's Credits Rolling, we're on the wrong board.

### Related docs

- `docs/PIVOT-PLAN.md` — capability-first pivot (complementary, not superseded).
- `agentbench/README.md` — measurement backend reference.
