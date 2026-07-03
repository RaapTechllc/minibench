# Agent Benchmark Platform — Build Brief (paste into a fresh session)

> **How to use this file:** Open a new session in the `minibench` repo and paste
> everything below the line. It is self-contained — it assumes no prior context.
> It tells the session what exists, what we're building, the technical direction
> (already researched — verify, don't re-derive from scratch), and the guardrails.

---

## Role & goal

You are helping build a **custom agent-benchmark platform** on top of the existing
`minibench` repo. We run **Mixture-of-Agents (MoA)** and agentic setups (OpenClaw-,
Hermes-agent-style, but this must be **harness-agnostic**), pull models from
**OpenRouter** (pay-per-token or BYOK) and **Ollama** (local + cloud), and score
them on **hard, contamination-resistant tasks we author ourselves** — not
public benchmarks the models have already trained on to "bench-max."

The end state is our own benchmark **website + leaderboard**, dedicated to *agent*
usage (coding + tool-use + long-horizon), that we spend our own money to run and
that **tracks new models automatically** as they ship on OpenRouter/Ollama.

Work on a feature branch. Commit in logical slices. Don't push to `main`.

---

## What already exists in this repo

`minibench` is currently **two things sharing one repo**:

1. **The core product (solid, tested):** a crowdsourced **hardware** benchmark for
   Mini PCs running local LLMs.
   - `backend/` — FastAPI + SQLAlchemy (async) + PostgreSQL. Tables: `benchmarks`,
     `hardware_specs`, `model_quality`. Endpoints under `/api/v1/*`. Has a pytest
     suite + GitHub Actions CI (`.github/workflows/ci.yml`).
   - `frontend/` — React 19 + Vite + TypeScript + Tailwind v4 + **Recharts**.
     Pages: Dashboard, Leaderboard, Compare, Hardware, BenchmarkDetail, Submit.
   - `cli/` — Python `minibench` package (Click) — detects hardware, runs Ollama
     benchmarks, uploads results. Has tests.
   - Read `README.md` and `TSD.md` for the full spec.

2. **The `benchmarks/` folder (prototype, has problems):** an attempt at a Hermes
   MoA benchmark. **Before extending it, read these files and understand its state:**
   - `benchmarks/run_moa_benchmark.py` — task runner (shells out to a `hermes` CLI).
   - `benchmarks/run_tool_benchmark.py` — a separate 3-model tool-use comparison.
   - `benchmarks/tasks.json` — 11 tasks across 6 categories.
   - `benchmarks/moa-presets.yaml` — MoA preset definitions.
   - `benchmarks/REPORT.md` — a narrative results report.

### Known problems with the current `benchmarks/` prototype (fix or replace)

A prior review found, by executing the code and fact-checking the report:

- **The runner is broken against its own config.** `run_moa_benchmark.py` hardcodes
  `PRESETS = ["budget-open", "balanced-hybrid", "high-quality"]`, but
  `moa-presets.yaml` was later rewritten to entirely different preset names
  (`glm-tool-moa`, `kimi-tool-moa`, `grok-moa`, `glm-flash-moa`, `m3-experimental`).
  A live run calls a `--model` that no longer exists. **Root cause: config drift with
  no CI guard.**
- **Grading is keyword-presence matching on raw text** (e.g. checking the string
  `"Tokyo"` appears in output). This can't distinguish a correct tool call from a
  model echoing the prompt — it's why all models "scored 100%." **Ceiling effect.**
- **"Live results" aren't reproducible:** `run_tool_benchmark.py` writes output to
  `/tmp/...`, never committed. The report's numbers have no auditable artifact.
- **No CI coverage** for `benchmarks/` at all.
- **Report sourcing is loose:** it presents vendor-reported and unpublished numbers
  (e.g. an unshipped "HermesBench") as settled official data, and compares scores
  across mismatched eval harnesses. The *models* it cites are mostly real, but the
  *comparisons* are not apples-to-apples.

**Decide early:** refactor `benchmarks/` in place, or start a clean `agentbench/`
module and migrate the good parts (the task category ideas, the preset concept).
Recommendation below leans toward a clean module built on a real harness.

---

## Technical direction (researched — verify against current docs, don't re-derive)

### 1. Build on an existing eval harness, not from scratch

**Recommendation: [inspect-ai](https://github.com/UKGovernmentBEIS/inspect_ai)**
(UK AI Safety Institute). It uniquely combines what we need:
- **Swappable model backends** via a `provider/model` string + `get_model()`;
  25+ built-in providers incl. OpenAI-compatible, Ollama, vLLM, Bedrock. Swapping
  models is a flag/config change with zero task changes.
- **Real agent/tool/multi-turn scaffolding** (`Solver`, `Agent`, `@tool`,
  `react()` loop, `TaskState`) — not just single-shot prompting.
- **Docker sandboxing** (`sandbox().exec()`) for coding/terminal tasks — a
  SWE-bench port already exists.
- **Structured, versioned `.eval` logs** viewable in `inspect view`, exportable to
  JSON/DataFrame.
- **MoA fits cleanly:** implement one custom `ModelAPI` subclass whose `generate()`
  fans out to proposers + aggregator and returns a single `ModelOutput`. Then MoA
  is *just another model string* usable in every task, agent, and scorer — exactly
  the "swap 3-4 models, treat the whole MoA as one model" abstraction we want.

Alternative: **[promptfoo](https://www.promptfoo.dev)** is excellent for
"run the same eval across N providers and diff side-by-side," and its custom-provider
hook makes MoA-as-provider trivial — but it lacks agent/sandbox runtime. Use it only
if we stay prompt-level. **A hand-rolled harness is not justified** — it would
reinvent inspect-ai's sandbox, agent loop, and logging.

### 2. OpenRouter + Ollama integration (API shapes verified via docs)

- **One OpenAI-compatible client covers all three backends** — only `base_url` +
  `api_key` + `model` change:
  - OpenRouter: `base_url=https://openrouter.ai/api/v1`, `OPENROUTER_API_KEY`,
    namespaced ids like `anthropic/claude-sonnet-4`.
  - Ollama local: `http://localhost:11434/v1/`, `api_key="ollama"` (ignored).
  - Ollama Cloud: `https://ollama.com/v1`, real `ollama.com` key.
- **Auto-track new models:** `GET https://openrouter.ai/api/v1/models` (no auth)
  returns `{data:[{id, name, created, context_length, pricing, ...}]}`. Poll on a
  schedule, diff `id`s → detect launches. Scrape `ollama.com/library` for local side.
- **Real cost logging:** send `"usage": {"include": true}` in the request body;
  the response `usage` object then includes `cost` (actual $/credits charged),
  `prompt_tokens`, `completion_tokens`, `reasoning_tokens`, `is_byok`. Log
  `usage.cost` directly. (Async audit: `GET /api/v1/generation?id=<gen-id>`.)
- **Billing reality:** OpenRouter has **no subscription** — it's **prepaid credits**
  (pay-per-token at listed prices) or **BYOK** (add your own provider key; OpenRouter
  adds a 5% surcharge). "Use my subscription" most likely means "draw from a shared
  prepaid credit balance." Confirm with the user which they want.
- **Reproducibility (critical):** the *same* model id fans out to multiple upstream
  providers at different price/quantization/latency. **Pin the model snapshot (dated
  id, not a floating alias) AND `provider.order: [...]` with `allow_fallbacks:false`,
  and store the `provider` returned per response.** An unpinned run is
  non-deterministic in cost and quality.

### 3. Swappable MoA config

Express the whole pipeline as data so swapping a model is a one-line edit, and wrap
it behind a single `generate(prompt) -> str` adapter so the harness sees one "model":

```yaml
moa:
  name: moa-v1                 # harness sees this as one "model"
  layers: 2                    # 2 = strong default; a 3rd layer rarely helps
  proposers:                   # swap models by editing this list
    - {model: openrouter/qwen/qwen-2.5-72b-instruct, temperature: 0.7, max_tokens: 2048}
    - {model: openrouter/meta-llama/llama-3.3-70b-instruct, temperature: 0.7, max_tokens: 2048}
    - {model: openrouter/mistralai/mixtral-8x22b-instruct, temperature: 0.7, max_tokens: 2048}
  aggregator:
    model: openrouter/anthropic/claude-opus-4-1
    temperature: 0.3
    max_tokens: 2048
    system_prompt: aggregate_and_synthesize   # canonical Wang et al. 2024 prompt
  parallel: true
```

Reference: Together AI's MoA (`github.com/togethercomputer/MoA`) — proposers answer
in parallel; outputs are concatenated as numbered "references" fed to the aggregator.
Use the canonical **"Aggregate-and-Synthesize"** aggregator system prompt from the
2024 paper (`utils.py` in that repo).

**Test the MoA premise, don't assume it:** the "Self-MoA" paper (arXiv 2502.00674)
shows that sampling the single *best* model N times often **beats** heterogeneous
mixing, because weak proposers drag the aggregate down. So the benchmark **must**
compare `MoA config` vs. `best single model at matched total cost` (tokens/$/latency)
— never MoA vs. one cheap call. Include a Self-MoA baseline.

### 4. Contamination-resistant task design (the "not bench-max" requirement)

**Rule zero: every task needs an executable oracle** (hidden unit tests, exact-match
on a computed value, or file/DB state-diff). No objective grader = not a benchmark.
Then, to keep tasks off the models' training data:

- **Time-gating:** only use problems published *after* a model's cutoff. Pattern
  refs: LiveBench, LiveCodeBench (date-tagged problems), SWE-bench-Live / SWE-rebench
  (fresh merged GitHub PRs → Docker → the repo's own test suite as grader).
- **Private held-out split:** keep the real test set secret; publish only ~10% as a
  public dev set (FrontierMath / GPQA / ARC-AGI-2 pattern).
- **Procedural generation:** emit task *instances* from templates (randomize numbers,
  names, structure) and compute the gold answer with a solver, so no fixed string can
  be memorized (GSM-Symbolic / DyVal pattern).
- **Canary + no-train license:** stamp a canary GUID + a no-index/no-train license on
  anything released, so leakage is later detectable.
- **Contamination audits:** n-gram overlap + Min-K% Prob membership tests before
  trusting a score; re-check on each new model.

**Small-team recipe for ~20–50 genuinely hard tasks:** (a) pull real GitHub issues
merged after cutoff, containerize, use their test suite as grader; (b) author
synthetic-but-verifiable coding tasks = spec + reference implementation +
property-based (Hypothesis) tests; (c) write tasks in a private repo that was never
public; (d) mutate known problems with fresh oracle solutions.

### 5. Leaderboard + data model (extends the existing app, additive)

Don't overload the `benchmarks` table. Add two tables:

```sql
CREATE TABLE agent_runs (
  id SERIAL PRIMARY KEY,
  run_id UUID DEFAULT gen_random_uuid(),
  submitted_at TIMESTAMPTZ DEFAULT NOW(),
  harness VARCHAR(64),            -- OpenClaw, Hermes-agent, inspect-native
  harness_version VARCHAR(32),
  moa_config JSONB,               -- {proposers[], aggregator, layers, ...}
  benchmark_suite VARCHAR(64),    -- our-coding-v1, our-tooluse-v1, swe-live
  provider VARCHAR(32),           -- openrouter, ollama
  model_snapshot_date DATE,
  n_tasks INT, n_trials INT,
  pass_rate DECIMAL(5,2), pass_hat_k DECIMAL(5,2),   -- pass^k = consistency across trials
  cost_usd_per_task DECIMAL(10,4),
  latency_p50_ms INT, latency_p95_ms INT,
  tokens_in BIGINT, tokens_out BIGINT
);
CREATE TABLE agent_task_results (
  id BIGSERIAL PRIMARY KEY,
  run_id UUID REFERENCES agent_runs(run_id),
  task_id VARCHAR(128), category VARCHAR(64),
  trial INT, passed BOOL, score DECIMAL(6,3),
  cost_usd DECIMAL(10,5), latency_ms INT,
  tokens_in INT, tokens_out INT,
  raw_output_ref TEXT             -- object-store key, not an inline blob
);
```

- **Leaderboard columns/visuals that matter for *agents*:** pass rate **with pass^k
  beside it** (agent runs are non-deterministic — a single number hides variance);
  cost_usd/task; latency p50/p95 (not mean); per-category breakdown. **Signature
  chart: an accuracy-vs-cost Pareto frontier** (Recharts `ScatterChart`, x=cost/task,
  y=pass rate, each dot a config, frontier line highlighted) — this is HAL's core
  insight: expensive setups are rarely on the frontier.
- **Auto-tracking:** APScheduler job in FastAPI (daily) → poll OpenRouter `/models`
  + scrape Ollama library → upsert `known_models(provider, model_id, first_seen,
  pricing, benchmarked BOOL)`. Surface `benchmarked=false` rows in a
  "**New — not yet benchmarked**" dashboard panel; optionally fire an alert / kick a run.
- **Keep both products coherent:** one site, two leaderboards. Shared top nav
  (**Hardware | Agents | Models | About**), separate FastAPI routers
  (`/api/v1/hardware/*`, `/api/v1/agents/*`) and React routes, shared chart component
  library and the `model_quality` join table.

---

## Rigor guardrails (apply to everything — these are what separate a real benchmark from vibes)

1. Freeze the task set + expected answers **before** running any model. No tuning the
   rubric until a favored config passes (that's eval p-hacking).
2. Run **≥3–5 trials per task per config**; report **mean ± confidence interval**,
   not a single point. Treat overlapping CIs as "indistinguishable," not a winner.
3. Grade on **structural/executable correctness**, never keyword presence. Pilot each
   grader against a deliberately-bad answer — if it can't fail, it doesn't discriminate.
4. **Pin** model ids, API/snapshot dates, provider, and decoding params.
5. **Commit raw per-trial outputs/transcripts** (or an object-store ref), not just
   summaries — a result you can't re-audit later isn't a result.
6. Report **cost and latency next to accuracy**; compare configs at **matched cost**.
7. If using an LLM judge, use a model **outside the proposer/aggregator family** and
   randomize/anonymize outputs — avoid self-preference bias. Prefer executable graders
   over judges wherever possible.
8. Add a **CI smoke test** (`--dry-run` or a tiny fixture run) so config drift like the
   current runner's preset mismatch is caught immediately.

---

## Suggested first deliverables (propose a plan before coding; confirm scope with the user)

1. **Decide harness:** spike `inspect-ai` — get one trivial task running against an
   OpenRouter model and an Ollama model with the *same* task definition.
2. **MoA-as-a-model:** implement the custom `ModelAPI`/provider wrapper (proposers +
   aggregator from a YAML config) and prove MoA runs as one model string.
3. **One real, contamination-resistant task with an executable grader** end-to-end
   (e.g. a post-cutoff GitHub issue with its test suite, in a Docker sandbox), plus
   real cost/latency logged from `usage.cost`.
4. **Model tracker:** the OpenRouter `/models` poller → `known_models` table → a
   "new, not yet benchmarked" API endpoint.
5. **Leaderboard slice:** `agent_runs` / `agent_task_results` tables + a
   `/api/v1/agents/leaderboard` endpoint + a React page with the pass-rate table and
   the cost-vs-accuracy Pareto scatter.

Confirm: which backend to prioritize (OpenRouter credits vs. BYOK vs. Ollama), which
task categories matter most (coding / tool-use / long-horizon), and whether to
refactor `benchmarks/` in place or start a clean `agentbench/` module.

## Key references
- inspect-ai: https://inspect.aisi.org.uk/ · https://github.com/UKGovernmentBEIS/inspect_ai
- OpenRouter docs (models, usage accounting, provider routing): https://openrouter.ai/docs
- Ollama OpenAI-compat: https://docs.ollama.com
- Together MoA: https://github.com/togethercomputer/MoA · https://www.together.ai/blog/together-moa
- Self-MoA critique: https://arxiv.org/abs/2502.00674
- LiveCodeBench: https://livecodebench.github.io · SWE-bench-Live: https://github.com/microsoft/SWE-bench-Live
- HAL (agent leaderboard methodology): https://arxiv.org/pdf/2510.11977
- promptfoo (alt harness): https://www.promptfoo.dev
