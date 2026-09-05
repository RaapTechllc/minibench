# MiniBench Pivot — Capability-First "Minibenchmarks" + Master Model Catalog

> Historical plan implemented through PR #17. The original sign-off language
> below is retained as history. See [current project status](PROJECT-STATUS.md).

**Date:** 2026-07-06 · **Status:** proposed (this doc is deliverable 1, for sign-off)
**Source brief:** the `/goal` pivot directive; guardrails inherited verbatim from
`benchmarks/AGENT-BENCH-BRIEF.md` §"Rigor guardrails".

## Why we're pivoting

The crowdsourced hardware benchmark measures tokens/sec-per-dollar across an open
matrix of machines × engines × quantizations × models. That matrix is too
combinatorial to control, so results aren't comparable — two submissions rarely
differ in only one variable. The fix:

1. **Demote hardware to a controlled variable.** A small fixed set of
   *reference profiles* pins engine, quantization, context, and decoding defaults.
   Hardware becomes the test rig; the existing crowdsourced data stays as a
   secondary reference view, not the headline.
2. **Promote model capability to the primary axis.** A master catalog of models
   (frontier + open-weight), scored with cheap, capability-revealing
   *minibenchmarks* that stay affordable even against the most expensive models.

## Decisions (defaults chosen; flag disagreement on the PR)

| Open question | Decision | Rationale |
|---|---|---|
| Budget ceiling | **≤ $5 per model per full public suite run** (3 trials); dev slice ≤ $0.50 | 40 tasks × 3 trials × ~600 in/700 out tokens ≈ 72k in + 84k out ≈ **$4.92** on `anthropic/claude-fable-5` ($10/$50 per M) — the priciest standard-tier model we'd run. "Pro" tiers ($30/$180 per M) are excluded from the standard sweep and only run on request. |
| Provider for paid runs | **OpenRouter prepaid credits** (existing integration, real `usage.cost`); Ollama on reference profiles for open-weight local runs (phase 2) | BYOK adds 5% + key sprawl; tracker.py + client.py already speak OpenRouter. Pin dated ids + `provider.order` + `allow_fallbacks:false`. |
| Priority categories v1 | **reasoning/math (numeric), structured-output/tool-use (json_fields), coding (unit_test), instruction/format adherence (exact/json)** | All four have executable oracles today in `agentbench/grading.py` — zero new grader code. **Long-context retrieval is deferred to v2**: it needs its own token budget (large prompts break the $5 ceiling math) and a dedicated generator. |
| Reference profiles v1 | 3 profiles: `consumer-gpu-24gb`, `apple-unified-32gb`, `cpu-only-mini-pc` — plus `provider-api` for closed models | Covers the three real local deployment shapes we have data for; closed models can't pin quant/engine, so their "profile" is the pinned provider route. |
| Dictated model names | Resolved against the **live** OpenRouter `/models` feed (341 models, fetched 2026-07-06): "QEM" → `qwen/qwen3.7-max`, "MIMO" → `xiaomi/mimo-v2.5(-pro)`, "K2/K2.7" → `moonshotai/kimi-k2.7-code` (+`k2.6`, `k2.5`, `k2-thinking`), MiniMax → `minimax/minimax-m3`, GLM → `z-ai/glm-5.2`, DeepSeek → `deepseek/deepseek-v4-pro`/`-flash` | **Yi (01-ai) and InternLM are not on the OpenRouter feed at all** — they enter the catalog only if/when they appear (or via the Ollama library in phase 2). We do not invent ids. |

## Workstreams

### W1 — Reference profiles (hardware as fixed rig)

- New `reference_profiles` seed data + `GET /api/v1/profiles`: each profile pins
  `engine`, `engine_version_min`, `quantization` (Q4_K_M default), `context_length`,
  `temperature/top_p` decoding defaults, and the representative `hardware_specs` rows
  it maps to (e.g. apple-unified-32gb ↔ Mac Mini M4 Pro).
- UI: a "How we run models" panel on the Hardware page. Hardware page stops being
  "the competition" and becomes the rig documentation + legacy crowdsourced view.

### W2 — Master model catalog

- `scripts` module in `agentbench` (reuses `tracker.ModelInfo`) converts the live
  OpenRouter feed into seed-ready rows for `known_models` (provider, pinned id,
  display name, context, prices, `benchmarked=false`).
- A curated **strategic families** list (ids verified against the live feed, dated
  snapshot over floating alias wherever the feed offers one) is committed as data:
  Qwen 3.5/3.6/3.7 (incl. flash/plus/max), Xiaomi MiMo v2.5, MiniMax M3/M2.x,
  Moonshot Kimi K2.5/K2.6/K2.7-code/K2-thinking, DeepSeek V4/V3.2/R1, Zhipu GLM
  5.x/4.7, NVIDIA Nemotron 3, OpenAI GPT-5.x, Anthropic Claude (Sonnet 5, Fable 5,
  Opus 4.x, Haiku 4.5), Google Gemini 3.x + Gemma 4, Meta Llama 4/3.x,
  Mistral Medium/Small/Devstral, xAI Grok 4.x, Microsoft Phi-4, Cohere Command A.
- `model_quality` keeps its published-score role (MMLU/Elo where citable) but gains
  rows only with sources; our own capability scores live in `agent_runs`, never
  faked into `model_quality`.
- New rows surface in the existing "New — not yet benchmarked" panel
  (`GET /api/v1/agents/models/new`).

### W3 — Minibenchmarks (`minibench-*` suites)

- `agentbench/tasks/minibench-core-v1.json` — the public **dev slice** (~10% pattern):
  20–24 tasks across the four v1 categories, every task with an executable oracle
  (`unit_test | numeric_match | json_fields | exact_match`), canary GUID, capped
  `max_tokens`, short prompts. The full private split stays out of the repo
  (documented placeholder + generator, not the instances).
- **Procedural generation:** a `minibench_gen.py` that emits task instances from
  templates with computed gold answers (GSM-Symbolic pattern), so refreshing the
  private split is a command, not an authoring session.
- Per-suite **cost math committed next to the suite**: expected cost =
  tasks × trials × (tokens_in + tokens_out) × price, evaluated against the catalog's
  priciest standard model. Fails loudly (script exit 1) if a suite breaks its budget.
- **Single-model presets** so each catalog model is one "model string"
  (`presets/single/<provider>-<model>.yaml`, self_moa off, 1 proposer = aggregator
  passthrough — same shape the existing config loader validates).
- Rigor (inherited, non-negotiable): freeze before comparing; ≥3 trials; Wilson CI +
  pass^k; overlapping CIs = tie; matched-cost Self-MoA baseline; committed artifacts;
  CI `--dry-run` smoke extended to the new suites.

### W4 — Model-centric leaderboard

- Backend: `GET /api/v1/agents/models/leaderboard` — best published run per model
  string on a given suite, with per-category pass rates, pass^k, cost/task, latency
  p50/p95, and the reference profile / provider used.
- Frontend: **Models** page — capability-vs-cost Pareto scatter (Recharts, existing
  pattern from the Agents page) + table. Nav becomes
  **Models | Agents | Hardware | Compare | Submit** (Models first = new headline).

## Sequencing (each a PR-able slice)

1. This plan + `docs/SPRINT-PLAN-FABLE5.md` landed (no more branch-orphaned docs).
2. W1 reference profiles (backend seed + endpoint + Hardware-page panel).
3. W2 catalog (generator script + committed seed data + tests).
4. W3 suites + presets + cost check + CI dry-run.
5. W4 model leaderboard endpoint + Models page + nav.

## Out of scope (unchanged from the brief)

Full user auth; extending legacy `benchmarks/` (drift-guard only); long-context
suite (v2); Ollama-library scraping (phase 2 of W2); production deploy.
