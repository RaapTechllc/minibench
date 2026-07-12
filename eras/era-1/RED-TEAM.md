# Era 1 — Red Team

**Process note.** The dedicated adversarial agent was killed mid-run by a
session usage limit (external, not a repo failure). Per the goal-loop rule
(same obstacle → different approach, never stall), the red team re-ran
**inline**: same claim list, evidence gathered by direct code reads and
commands. A parallel completeness-critic agent covered the definition-of-done
sweep. Findings below; every defect was fixed in-branch and re-gated before
ship.

## Defects found (all fixed)

| # | Severity | Finding | Evidence | Fix |
|---|----------|---------|----------|-----|
| RT‑1 | should‑fix (factual error) | `/methodology` claimed decoding pins `max_tokens 1024`; the actual pinned value is **4096** (`agentbench/config.py:173-187`, chosen deliberately for reasoning-model headroom). A methodology page with a wrong number defeats its own purpose. | `single_model_config(..., max_tokens: int = 4096)` vs page text | Page now states 4096 and explains the 2,000-char gradable-text cap alongside it |
| RT‑2 | should‑fix (data honesty) | The importer trusted `summary.n_canary_flags` / `n_infra_errors` when the keys were **present**, falling back to per-trial flags only when absent — so an artifact whose summary said `0` while a trial carried `canary_flag: true` would import cleanly (laundering) | `import_results.py` used `summary.get(key, computed)` | Now takes `max(summary counter, computed-from-trials)`; regression test `test_lying_summary_cannot_launder_flagged_trials` covers both canary and infra |
| RT‑3 | should‑fix (race) | Auto-widen on `/models` used state captured in a stale closure: if the user picked a suite while the initial empty-default response was in flight, the late response could override the user's choice with "All suites" | `Models.tsx` load callback closed over `suite`/`autoWidened` | Replaced the state flag with a `suitePinned` ref set synchronously on any user choice and read at response time; a stale response can no longer override |

## Attacked and confirmed safe

- **Importer dry-run gate** — refused unconditionally, no override flag exists;
  drove it with a real dry-run artifact during development and it refused
  (`REFUSED ... dry_run artifact`). Residual risk, accepted and documented: an
  artifact *missing* the `dry_run` key imports as live. The gate defends
  against accidents, not against a forger — a forger could equally write
  `"dry_run": false`, so a hard-fail on a missing key would add friction, not
  security. Provenance fields exist for authenticity questions.
- **Payload fidelity** — importer reuses `to_agent_run_submit` + `publish_run`
  from `run.py` (single source of truth), so fraction→percent scaling, CI
  bounds, latency ints, and token sums cannot drift from the live path.
  Verified live: 26/26 artifacts published; leaderboard values match artifact
  summaries (e.g. `pass_rate 0.9833 → 98.33`).
- **Trials containing `infra_error`** — included in `results[]` exactly as the
  live publish path does; runs containing them are refused by default anyway.
- **scoreScale correctness** — band boundaries (85/70/55/40), clamping, and
  null-in/null-out covered by 6 node tests; missing category data renders
  untinted `—`, never a fake color.
- **CI compatibility** — agentbench CI job runs `pytest -q` *before* the
  dry-run smokes (`.github/workflows/ci.yml`), and the drift-guard test
  filters `dry_run` artifacts anyway; test imports follow the same
  `from agentbench.x import y` pattern as every existing test (CI-proven);
  frontend lint has no `--max-warnings`, and errors are at 0.
- **Legacy-notice behavior** — `/leaderboard` still sets the one-shot flag,
  `/models` consumes it exactly once (lazy `useState` initializer); only the
  file layout changed.
- **Era-doc factual claims** — spot-checked counts against command output: 26
  committed live artifacts (26 published / 0 refused / 0 failed), 22 model
  leaderboard rows, 165→166 agentbench tests after the regression test,
  gate exit codes in `gates/*.txt`.

## Accepted risks (documented, seeded for Era 2)

1. **No server-side idempotency** on `POST /api/v1/agents/runs`: re-importing
   duplicates rows (model leaderboard unaffected — best run per model).
2. **"All suites" mixes tiers**: best-run-per-model preference favors the
   easier suite when a model has runs on several (pre-existing endpoint
   behavior, now more visible because the page can auto-widen).
3. **Category cells are single-trial-set pass rates** without per-category CIs;
   the heatmap could over-signal certainty on 15-trial categories.
