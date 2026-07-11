# Era 1 — Recap

**Read this in five minutes.** Protocol: [`eras/GOAL-LOOP.md`](../GOAL-LOOP.md) ·
Mission: [`MISSION.md`](MISSION.md) · Evidence trail: [`LEDGER.md`](LEDGER.md) ·
Adversarial findings: [`RED-TEAM.md`](RED-TEAM.md) · PR:
[#29](https://github.com/RaapTechllc/minibench/pull/29)

## The one-paragraph story

MiniBench had 26 committed, real, live benchmark result artifacts that nobody
could see: the only publish path re-executes suites against OpenRouter, so any
fresh deployment showed empty agent leaderboards — and this environment has no
API key at all. Era 1 closed that loop with an **offline importer** that
replays committed artifacts through the exact live publish path (same payload
builder, same honesty gates), then made the resulting numbers **legible** (a
heatmap leaderboard with an equal-weight composite) and **credible** (a
user-facing methodology page where every claim traces to repo code). The era
process itself is now a first-class, repeatable thing: `eras/GOAL-LOOP.md` +
the `/goal` command, with this recap seeding Era 2.

## What shipped (deliverables map)

| Deliverable | Where | Proof |
|-------------|-------|-------|
| Offline results importer | [`agentbench/import_results.py`](../../agentbench/import_results.py) · docs in [`agentbench/README.md`](../../agentbench/README.md) | 12 tests in [`agentbench/tests/test_import_results.py`](../../agentbench/tests/test_import_results.py); live run: fresh DB → `26 published, 0 refused, 0 failed` → 22 model rows ([`LEDGER.md`](LEDGER.md) Phase 3) |
| Heatmap model leaderboard + Composite | [`frontend/src/pages/Models.tsx`](../../frontend/src/pages/Models.tsx), [`frontend/src/lib/scoreScale.js`](../../frontend/src/lib/scoreScale.js) | 6 node tests; screenshots: [desktop](screenshots/models-desktop.png) · [mobile](screenshots/models-mobile.png), zero console errors |
| Methodology page (`/methodology`) | [`frontend/src/pages/Methodology.tsx`](../../frontend/src/pages/Methodology.tsx) | Screenshots: [desktop](screenshots/methodology-desktop.png) · [mobile](screenshots/methodology-mobile.png); per-section source map in the build agent's report; red team corrected the one factual slip (RT‑1) |
| Goal loop (protocol + command) | [`eras/GOAL-LOOP.md`](../GOAL-LOOP.md), [`.claude/commands/goal.md`](../../.claude/commands/goal.md) | You are reading its output; Era 2 starts with `/goal` |
| Lint gate green | [`frontend/src/lib/legacyNotice.ts`](../../frontend/src/lib/legacyNotice.ts) | `npm run lint` exit 1 → exit 0 ([`gates/lint.txt`](gates/lint.txt)) |
| Gate logs + screenshots as artifacts | [`gates/`](gates/) · [`screenshots/`](screenshots/) | Committed (logs as `.txt`; `*.log` is gitignored) |
| Docs refresh | [`README.md`](../../README.md) (stale routes table fixed, importer), [`CHANGELOG.md`](../../CHANGELOG.md) | In-diff |
| setup-dev fix | [`scripts/setup-dev.sh`](../../scripts/setup-dev.sh) | cli venv now gets pytest — the gate a stranger would hit first |

## Reproduce the demo locally

```bash
./scripts/setup-dev.sh                     # venvs + npm deps
# start Postgres (this VM: sudo pg_ctlcluster 16 main start; or docker compose up -d db)
cd backend && . .venv/bin/activate && uvicorn app.main:app --port 3070 &
python -m agentbench.import_results agentbench/results/*.json --api http://localhost:3070
cd frontend && npm run dev                 # open /models and /methodology
```

## Self-grade vs the definition of done

| Check | Verdict |
|-------|---------|
| Guardrails held (no spending, nothing published off-repo, no invented data) | ✅ — no keys used; branch + draft PR only; dry-run artifacts refused by design, one stray dry-run file deleted, its refusal proving the gate |
| Every goal shipped or cut with rationale | ✅ — G0–G4 all shipped; rejected candidates logged in MISSION.md |
| Four gates green with captured output | ✅ — backend 27 · cli 12 · agentbench **166** · frontend 18, lint 0 errors, build ok ([`gates/`](gates/)) |
| UI screenshot-verified desktop + mobile vs live backend | ✅ — four screenshots, re-taken after red-team fixes |
| Recap claims trace to commands / file:line / URLs | ✅ — this table + LEDGER phase entries |
| Red team ran, objections visible, fixed or answered | ✅ — 3 defects fixed (incl. a factual error on the methodology page); 3 accepted risks documented ([`RED-TEAM.md`](RED-TEAM.md)) |
| Fresh-agent audit | ✅ — ran post-recap; verdict and findings in [`AUDIT.md`](AUDIT.md) |
| Ledger cold-start complete | ✅ — phases 0–4 in handoff format, landmines + verify-first |
| Recap ends with next-era seed | ✅ — below |
| No placeholders posing as finished work | ✅ — the one caveat is honest: leaderboard rows are labeled "Dev slice", exactly what they are |

**Known honest limits:** no live model runs this era (no API key — guardrail);
the imported rows are public dev-slice runs and are badged as such; the
committed artifacts predate grader v3, so `grader_version` is null on those
rows (never guessed).

## Era 2 seed (candidates, with evidence from this era)

1. **score_source / dual-channel scores in the submit schema.** Recon proved
   `to_agent_run_submit` drops `pass_capability`/`pass_format` and the DB has
   no column for them (`run.py:344-385`, `schemas.py`); the methodology page
   now *describes* dual scoring that the leaderboard cannot yet *show*. One
   schema migration + one column + one badge.
2. **Server-side idempotency for `POST /api/v1/agents/runs`.** Red-team
   accepted-risk #1: re-importing duplicates rows. A natural key
   (suite, config name, generated_at or artifact hash) upsert closes it.
3. **Per-suite leaderboard integrity.** Red-team accepted-risk #2: "All
   suites" + best-run-per-model favors the easiest suite a model has run.
   Either rank within suite only, or prefer the *hardest* suite.
4. **Tracker automation.** `tracker.py` still has no caller (recon item #1);
   a scheduled catalog sync (GitHub Actions cron → admin endpoint or
   seed-file PR bot) would make the "New — not yet benchmarked" panel
   self-maintaining. Needs a key decision for live polling.
5. **Per-category Wilson CIs in `category_pass_rates`.** Red-team accepted
   risk #3: heatmap cells over-signal certainty on 15-trial categories.
   Backend already computes overall CIs; extend per category and render as
   cell tooltips.

Advisory, not binding — Era 2's recon re-verifies before building.
