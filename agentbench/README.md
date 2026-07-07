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

## Suites: core → hard → pro

Three procedurally-generated capability suites, all deterministically graded
(no LLM judge), all cost-bounded:

- **`minibench-core-v1`** (4 categories) — the fundamentals: math reasoning,
  structured extraction, format adherence, code writing.
- **`minibench-hard-v1`** (4 categories) — compositional variants (search,
  aggregation, chained transforms, a no-`eval` parser) to separate frontier
  models that saturate core.
- **`minibench-pro-v1`** (10 categories) — a strategic capability MATRIX plus
  two axes almost no cheap benchmark grades deterministically.

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
| `tasks/` | `coding-v1` (smoke/CI), `coding-v2` (harder eval), `minibench-core-v1` (canonical capability dev slice). |
| `minibench_gen.py` | Procedural generator for `minibench-*` suites (core/hard/pro) — computed gold, canary, committed dev slice (seed 20260706); private split regenerated with an uncommitted seed. |
| `compare.py` | Pairwise significance (exact McNemar + task-bootstrap CIs) across a sweep; refuses ordering claims without p<0.05. Calibration excluded from ranking. |
| `item_stats.py` | Item-discrimination audit (point-biserial); prunes by discrimination only. Calibration excluded (continuous). |
| `catalog.py` | Master model catalog: joins the strategic-family list against the live OpenRouter feed → `backend/app/data/known_models_seed.json`. |
| `cost_check.py` | Budget guard: tasks x trials x tokens x price against the priciest catalog model. Worst-case (full completion cap). Core/hard ≤ $15; pro ≤ $40 (broader suite). CI-enforced, all three suites. |

## Running

Offline smoke test (no keys, no network — also what CI runs, catches config drift):

```bash
python -m agentbench.run --config agentbench/presets/moa-v1.yaml \
    --tasks agentbench/tasks/coding-v1.json --trials 3 --dry-run
```

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

Tests:

```bash
cd agentbench && pip install -r requirements-dev.txt && pytest
```

## Anti-gaming hardening (grader v2)

Scores must reflect capability, not prompt-maxing. The defenses, and what each
one closes:

| Threat | Defense |
|---|---|
| Training contamination of the public dev slice | Private-seed splits (`--generate`), per-task canary strings, grade-time canary echo detection, dev-vs-private seed-delta comparison |
| Decoy-burying / answer-spraying | Strict graders (`grader_version 2`): only an isolated final answer counts; 2000-char verbosity cap |
| Test-file peeking in coding tasks | AST purity check before the solution touches disk, randomized test filename, minimal subprocess env |
| Provider luck scored as capability | Retry/backoff on 429/5xx/timeouts; exhausted retries recorded as `infra_error` and EXCLUDED from every denominator; publish refused while any exist |
| Sampling/prompt advantages | Pinned decoding (temperature 0.0, top_p 1.0, max_tokens 1024), no system prompt, MoA configs rejected for `minibench-*` suites |
| Noise sold as ranking | Task-level bootstrap CIs, exact McNemar pairwise tests (`compare.py`); no p < 0.05, no ordering claim |
| Benchmark tuned to a desired ranking | Items pruned by discrimination only (`item_stats.py`); expected orderings are checked LAST, as a sanity signal |

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
