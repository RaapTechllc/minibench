# agentbench

A contamination-resistant **agent / Mixture-of-Agents (MoA)** benchmark platform,
built as a clean module alongside the hardware-benchmark product (see
`benchmarks/AGENT-BENCH-BRIEF.md` for the full rationale). It realizes the brief's
first deliverables: MoA-as-a-model, executable grading, real cost accounting, a
new-model tracker, and rigor stats (trials + CIs + pass^k).

## Why this exists

The older `benchmarks/` prototype graded by keyword presence (so nothing could
score below 100%), hardcoded preset names that drifted from its own YAML, and
wrote "live results" to `/tmp` that were never committed. `agentbench` fixes all
three: **executable oracles**, **config validated at load**, and **committed
result artifacts**.

## Suites: core → hard → v2 → pro (+ moa-lite)

Four procedurally-generated capability suites, all deterministically graded
(no LLM judge), all cost-bounded:

- **`minibench-core-v1`** (4 categories) — the fundamentals: math reasoning,
  structured extraction, format adherence, code writing.
- **`minibench-hard-v1`** (4 categories) — compositional variants (search,
  aggregation, chained transforms, a no-`eval` parser) to separate frontier
  models that saturate core.
- **`minibench-v2`** (4 categories) — frontier tier: multi-step composition,
  adversarial distractors, and stricter transforms when hard-v1 still tops out
  ~87%. Featured on the Models leaderboard.
- **`minibench-pro-v1`** (10 categories) — a strategic capability MATRIX plus
  two axes almost no cheap benchmark grades deterministically.
- **`moa-lite-v1`** (4 categories, 12 tasks) — MoA-native disagreement slice
  (doc-conflict, constraint-pack, evidence-gap, proposal-arbitrate). Not under
  the `minibench-*` prefix, so cheap MoA / Self-MoA gates are allowed.

## Arcade task authoring checklist

Season task prompts should feel like work a developer could paste directly into
Cursor, a spreadsheet assistant, or a Slack thread. The grader can stay strict
and synthetic underneath, but the surface prompt should pass this Cursor-paste
test before it ships:

- The prompt names a concrete artifact to produce: a number, JSON object, short
  transformation, or fenced Python block.
- The context sounds like practical work, not benchmark machinery. Do not expose
  gold answers, canaries, hidden tests, seed IDs, McNemar stats, or pruning goals.
- The requested output channel is explicit enough for deterministic grading, and
  any format restriction is phrased as a normal work constraint.
- A human should understand why this would belong on one Arcade manual badge:
  `spreadsheet`, `cursor`, or `slack`.

`scenario_type` is metadata only; it must not change grader or oracle behavior.
The badges use this convention:

- `spreadsheet` — numeric reasoning, account math, table/order aggregation, or
  any task whose natural workspace is rows, formulas, and totals.
- `cursor` — code writing, code repair, debugging, or hidden-unit-test prompts
  that belong in an editor.
- `slack` — instruction-following, text transforms, incident/log triage, and
  other conversational tasks that read like a pasted Slack request.

For the committed v2 dev slices, `minibench-v2` maps reasoning tasks to
`spreadsheet`, coding tasks to `cursor`, order-revenue structured tasks to
`spreadsheet`, and log-batch or text-transform tasks to `slack`. `coding-v2`
uses `cursor` for `code-*`, `spreadsheet` for `reason-*`, and `slack` for
`tooluse-*`.

### Why minibench-pro-v1 is different

Most public evals either grade a narrow slice or lean on an LLM judge (slow,
non-deterministic, gameable). Pro tests the dimensions models are actually used
for — **function-calling, date/time arithmetic, code *debugging*, constrained
generation (format + negative constraints), counting, unit conversion, table
manipulation, self-correction** — every one with an *executable oracle*. On top
of the capability grid it adds two axes that are novel for a cheap, deterministic
benchmark:

- **Calibration (Brier).** Each item states a claim with a *computed* truth
  value and asks for a probability; graded by Brier score `(p − outcome)²`.
  Reported as a suite-level `calibration_brier` (lower is better; 0.25 is the
  always-guess-0.5 baseline). It measures whether a model *knows what it knows* —
  and it's excluded from the binary pass-rate pool so it never distorts it.
- **Robustness (consistency).** Matched `(base, perturbed)` task pairs — reworded,
  reordered, or with an added distractor — share one gold. `robustness_consistency`
  is the fraction of pair-trials where the model's correctness *agrees* (1 − flip
  rate): it exposes brittleness that raw accuracy hides.

`self-correct` items embed a flawed prior answer plus a critique and require the
corrected result — testing recovery, graded by the existing oracles.

Everything stays cheap: prompts are short and answers are a number, a token, a
small JSON object, or a short code fix. The budget guard (`cost_check.py`) is
deliberately worst-case (every call billed at the full completion cap on the
priciest catalog model); pro is a broader suite (10 categories, ~55-task dev
slice), so its guard runs against an explicit higher `--budget 40` ceiling.
Real spend on a normal run is a few dollars at most.

## Layout

| File | Purpose |
|------|---------|
| `config.py` | MoA config schema + YAML loader (proposers, aggregator, layers, Self-MoA). Validates at load. |
| `client.py` | One OpenAI-compatible client for OpenRouter + Ollama. Real `usage.cost`. Network boundary is injectable. |
| `moa.py` | `MoAModel.generate(prompt)` — fans out proposers → aggregator, rolls up cost/latency/tokens. |
| `grading.py` | Executable graders: `exact_match`, `numeric_match`, `json_fields`, `unit_test`, `regex_match`, `calibration`. Each fails a bad answer. |
| `stats.py` | `pass_rate`, `pass_hat_k`, Wilson CI, percentiles — the trials-and-CIs guardrail. |
| `tracker.py` | Poll OpenRouter `/models`, diff against known ids → detect new launches. |
| `run.py` | CLI: run a config against a task suite with N trials, grade, summarize, write a committable artifact. |
| `presets/` | MoA configs: `moa-v1` (production), `moa-dev` (cheap testing), Self-MoA baselines. |
| `tasks/` | `coding-v1` (smoke/CI), `coding-v2` (harder eval), `minibench-core-v1` (canonical capability), `moa-lite-v1` (MoA-native disagreement slice). |
| `minibench_gen.py` | Procedural generator for `minibench-*` suites (core/hard/pro) — computed gold, canary, committed dev slice (seed 20260706); private split regenerated with an uncommitted seed. |
| `moa_lite_gen.py` | MoA-native light suite (`moa-lite-v1`): doc-conflict, constraint-pack, evidence-gap, proposal-arbitrate. Name is not `minibench-*`, so MoA configs are allowed. |
| `compare.py` | Pairwise significance (exact McNemar + task-bootstrap CIs) across a sweep; refuses ordering claims without p<0.05. Calibration excluded from ranking. |
| `item_stats.py` | Item-discrimination audit (point-biserial); prunes by discrimination only. Calibration excluded (continuous). |
| `check_ceiling_items.py` | Season-publish gate that fails a comparable sweep when any item is at or above the ceiling threshold (90% pass by default). |
| `catalog.py` | Master model catalog: joins the strategic-family list against the live OpenRouter feed → `backend/app/data/known_models_seed.json`. |
| `cost_check.py` | Budget guard: tasks x trials x tokens x price against the priciest catalog model. Worst-case (full completion cap). Core/hard ≤ $15; pro ≤ $40 (broader suite). CI-enforced, all three suites. |

## Running

Offline smoke test (no keys, no network — also what CI runs, catches config drift):

```bash
python -m agentbench.run --config agentbench/presets/moa-v1.yaml \
    --tasks agentbench/tasks/coding-v1.json --trials 3 --dry-run
```

Real-Work Agent Cabinet lifecycle smoke (fresh fixture per trial, deterministic
fake agent, hidden verification, and cleanup; no keys or network):

```bash
python -m agentbench.agent_tasks \
    --manifest agentbench/tasks/minibench-agent-v1-offline.json \
    --trials 2 --out /tmp/minibench-agent-smoke.json
```

Terminal-operation smoke uses Docker for real CPU, memory, PID, filesystem, and
network isolation. Pull the immutable fixture image once, then both task
containers run with `--network none`; when Docker or the image is unavailable,
the command exits successfully with an explicit `SKIP` reason.

Phase 1 accepts only frozen declarative procedures for offline gold and negative
regressions. Arbitrary Python/provider adapters are rejected rather than treated
as sandboxed; a real provider terminal adapter is deferred until it can preserve
the same container-only untrusted execution boundary.

```bash
docker pull busybox@sha256:3c6ae8008e2c2eedd141725c30b20d9c36b026eb796688f88205845ef17aa213
python -m agentbench.terminal_operations \
    --manifest agentbench/tasks/minibench-terminal-http-banner.json \
    --manifest agentbench/tasks/minibench-terminal-health-endpoint.json \
    --out /tmp/minibench-terminal-smoke.json
```

Generated repository-repair smoke is also deterministic and fully offline. It
creates a fresh repository-shaped fixture, runs the reference repair adapter,
and writes a sanitized artifact without a model or API key:

```bash
agentbench/.venv/bin/python -m agentbench.generated_repairs \
    --seed 20260717 --trials 2 --out /tmp/minibench-generated-repair.json
```

Artifacts retain only the seed fingerprint, fixture version, mutation-template
hash, budgets, harness, and terminal outcome.

Generated data/SQL-repair tasks use the same Agent Cabinet lifecycle with an
in-memory SQLite verifier and no network or API key. Seeds select join,
aggregation/null, or incremental-processing defects:

```bash
agentbench/.venv/bin/python -m agentbench.generated_sql_repairs \
    --seed 20260719 --trials 2 --out /tmp/minibench-generated-sql-repair.json
```

A paired self-review smoke reuses the same generated fixture and hidden oracle
for a normal first attempt plus one independently budgeted correction. The
correction receives only fixed, classified feedback; verifier detail and gold
changes are never placed in the prompt or artifact:

```bash
agentbench/.venv/bin/python -m agentbench.self_review \
    --seed 20260717 --trials 2 --out /tmp/minibench-self-review.json
```

The compatible result artifact reports first-pass and final completion,
corrected failures, introduced regressions, no-change outcomes, and lift. An
infrastructure failure in either phase leaves lift undefined for that pair.
First-pass completion and first-attempt usage include every non-infrastructure
first attempt; final completion and lift use completed pairs only. Token and
cost totals remain null whenever any contributing phase did not report them.

Cheap live testing (7B-class models, harder tasks — expect <100% pass rate):

```bash
python -m agentbench.run --config agentbench/presets/moa-dev.yaml \
    --tasks agentbench/tasks/coding-v2.json --trials 2 --provider openrouter
```

Production eval (expensive 70B+ MoA, easy smoke tasks — use only when comparing top configs):

```bash
export OPENROUTER_API_KEY=sk-or-...
python -m agentbench.run --config agentbench/presets/moa-v1.yaml \
    --tasks agentbench/tasks/coding-v2.json --trials 5 --provider openrouter
```

Score one catalog model as one model string (single call per prompt, no aggregator):

```bash
python -m agentbench.run --model openrouter/moonshotai/kimi-k2.7-code \
    --tasks agentbench/tasks/minibench-core-v1.json --trials 3 --provider openrouter
```

Regenerate the master catalog seed / check a suite budget:

```bash
python -m agentbench.catalog --fetch
python -m agentbench.cost_check --tasks agentbench/tasks/minibench-core-v1.json --trials 3
```

Season release item-pruning gate:

```bash
python -m agentbench.item_stats agentbench/results/<season-sweep-*.json>
python -m agentbench.check_ceiling_items agentbench/results/<season-sweep-*.json>
```

`check_ceiling_items.py` exits `1` when any comparable-sweep item is at or above
90% pass, and exits `2` when the input runs are not comparable or too small for a
meaningful gate. See `docs/release-checklist-season.md` before changing the live
default cabinet.

Tests:

```bash
cd agentbench && pip install -r requirements-dev.txt && pytest
```

## Anti-gaming hardening (grader v3)

Scores must reflect capability, not prompt-maxing. The defenses, and what each
one closes:

| Threat | Defense |
|---|---|
| Training contamination of the public dev slice | Private-seed splits (`--generate`), per-task canary strings, grade-time canary echo detection, dev-vs-private seed-delta comparison |
| Decoy-burying / answer-spraying | Strict *format* channel (`pass_format`): isolated final answer + 2000-char verbosity cap |
| Format pedantry scored as intelligence | Dual metrics (`grader_version 3`): `pass_rate` / `pass_capability` = extractable answer; `pass_format` = strict channel. Rank capability, diagnose format separately |
| Ambiguous float gold / empty exact_match | Decimal line-then-sum + `json_fields` `tol`; generator bans empty exact_match |
| Test-file peeking in coding tasks | AST purity check before the solution touches disk, randomized test filename, minimal subprocess env |
| Provider luck scored as capability | Retry/backoff on 429/5xx/timeouts; exhausted retries recorded as `infra_error` and EXCLUDED from every denominator; publish refused while any exist |
| Sampling/prompt advantages | Pinned decoding (temperature 0.0, top_p 1.0, max_tokens 1024), no system prompt, MoA configs rejected for `minibench-*` suites |
| Noise sold as ranking | Task-level bootstrap CIs, exact McNemar pairwise tests (`compare.py`); no p < 0.05, no ordering claim |
| Benchmark tuned to a desired ranking | Items pruned by discrimination only (`item_stats.py`); expected orderings are checked LAST, as a sanity signal |

v2-scored rows are not comparable to v3. Cheap validation gate: see
`agentbench/presets/cheap-gate-roster.yaml` (flash/small singles on minibench-v2;
MoA / Self-MoA on `moa-lite-v1` via `moa-cheap-gate` / `self-moa-cheap-gate`).
Do not burn frontier tokens until that gate passes.

## Legitimacy sweep protocol

1. **Freeze.** Commit everything; `git status --porcelain` must be empty.
2. **Seed.** Generate a secret HIGH-ENTROPY seed and set it ONLY in the sweep
   shell: `MINIBENCH_SEED` from `python -c "import secrets; print(secrets.randbits(63))"`.
   Use ≥ 2⁶³ — a small seed (e.g. 2³¹) is brute-forceable in minutes against
   the published `seed_sha256`, which would reveal the private split. Never
   echo the seed into a committed file or published log. One seed per sweep,
   the SAME seed for every model (comparability); rotate next sweep.
3. **Budget + pre-flight.**
   `python -m agentbench.cost_check --generate core --per-category 10 --trials 5 --budget 12`
   (worst-case tokens against the priciest catalog model — real answer-only
   runs cost cents), then a dry-run smoke:
   `python -m agentbench.run --model x/y --generate core --dry-run` — which
   also exercises the **gold self-check gate** (every generated task must
   grade its own gold answer as a pass, catching generator/grader drift on a
   fresh seed).
4. **Run every model with identical flags**, same seed, same window:
   `python -m agentbench.run --model <m> --generate core --per-category 10 --trials 5`
   then `--generate hard`. Results land in `agentbench/results/` under a
   seed-hash + timestamp filename (never overwrites a previous sweep).
5. **Mechanical validity gates** (ordering-blind, per run):
   - `n_infra_errors == 0` — otherwise rerun; publishing is refused.
   - `n_canary_flags == 0` — otherwise the model echoed a benchmark canary:
     quarantine the run as contaminated; publishing is refused.
   - `seed_sha256`, `grader_version`, `decoding` identical across the sweep
     (`compare.py` refuses to compare otherwise).
6. **Contamination probe.** Also run each model on the committed dev slice
   (`--tasks agentbench/tasks/minibench-core-v1.json`) and compare dev vs
   private pass rates. A fleet-relative positive outlier on the public slice
   is flagged contaminated/overfit — an asterisk, never a score edit.
7. **Ranking claims only via**
   `python -m agentbench.compare results/<a>.json results/<b>.json ...` —
   A > B requires McNemar p < 0.05; everything else is reported as
   **indistinguishable**. Ceiling ties on hard-v1 are ties (the signal to
   design hard-v2, not to tweak graders).
8. **Last, sanity only:** compare against expectations. If the ordering
   surprises you, the allowed responses are (a) run
   `python -m agentbench.item_stats results/*.json`, inspect flagged items,
   and fix a broken ITEM for all models, or (b) accept the result. Never
   re-grade, re-seed, or selectively rerun to move one model.

Every results JSON records `seed_sha256` (proves same-sweep without revealing
the seed), `generator_sha256`, `git_commit`, `is_private_split`,
`grader_version`, and the pinned decoding params. The backend stores all of
these; leaderboards exclude runs with canary flags or infra errors, and a
model's private-split run always supersedes its dev-slice run. (Backend note:
no migration framework — adding the provenance columns to an existing database
needs a recreate or manual `ALTER TABLE agent_runs ADD COLUMN ...`.)

## Reproducibility notes (from the brief — verify before a real run)

- **Pin dated model snapshots**, not floating aliases. On OpenRouter also pin
  `provider.order` + `allow_fallbacks:false` and store the returned `provider`,
  because the same id fans out to different price/quantization upstreams.
- **Always run a matched-cost Self-MoA baseline** (`presets/self-moa-baseline.yaml`).
  A mixed MoA that doesn't beat sampling the best single model N times isn't buying
  anything (arXiv 2502.00674).
- **Keep the real test split private**; publish only a dev slice. Task files carry a
  `canary` string so later leakage is detectable.
- Grade only on executable oracles. If a grader can't fail a deliberately-bad
  answer, it doesn't discriminate.

## Publishing to the leaderboard

After a live run, publish to the backend Agents API:

```bash
python -m agentbench.run --config agentbench/presets/moa-dev.yaml \
    --tasks agentbench/tasks/coding-v2.json --trials 3 --provider openrouter \
    --publish http://localhost:3070
```

`--publish` transforms the summary (pass rates as 0–100, `ci95_low`/`ci95_high`, per-task
`results`) and POSTs to `/api/v1/agents/runs`. The React **Agents** page renders the
pass-rate table plus the cost-vs-accuracy Pareto frontier.

### Re-publishing committed artifacts (no API key needed)

A fresh database starts with empty leaderboards, and `--publish` only fires
after executing a live run. To replay the committed, auditable artifacts in
`agentbench/results/` into a local backend instead:

```bash
# Validate without POSTing:
python -m agentbench.import_results agentbench/results/*.json --check

# Publish to a running backend:
python -m agentbench.import_results agentbench/results/*.json --api http://localhost:3070
```

The importer reuses the exact live-path payload builder and applies the same
honesty gates: `dry_run` artifacts are refused unconditionally (no override),
canary-flagged runs are refused, and infra-error runs are refused unless
`--allow-infra-errors`. Legacy pre-grader-v3 artifacts import with absent
fields left null — never guessed. Note the endpoint does not deduplicate:
importing the same artifact twice creates two runs (the model leaderboard
still shows only the best run per model).
