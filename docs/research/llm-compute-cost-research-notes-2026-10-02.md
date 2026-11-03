# LLM cost-efficiency benchmark — frozen research notes

- Status: FROZEN 2026-10-02 (America/Chicago). Research only. No code, no repo changes, no PRs.
- Idea owner: Kyle Raap (RaapTech). Proposed home: `RaapTechllc/minibench`.
- Labels: **FACT** (URL + access date), **ASSUMPTION** (my reasoning, not sourced), **UNKNOWN** (not found or not verified).
- Every URL below was accessed 2026-10-02 unless noted. Prices are cited examples tied to their source date. They are not current quotes.
- **Addenda (folded in 10:18 CT, same day):** (1) output-weighted cost, §8. (2) **Reframe:** the project is now mainly an *investigation of what labs actually pay for inference compute*. The size-over-price ratio and the Pareto chart become estimation tools, not the product. See §9–§12.
- Model names such as "GPT-6 Astra", "Claude Fable 5.1" and "GPT-5.6 Luna" are reproduced exactly as the cited pages print them. I did not check them against vendor pages.

---

## §0 TL;DR

1. **FACT:** Capability-per-dollar Pareto charts already exist at Artificial Analysis (intelligence vs cost per task), LMArena (Arena score vs blended $/1M), Epoch AI (cost frontier per benchmark) and MIT FutureTech (Gundlach et al.). Plotting price against capability is not a new idea. Dividing parameters by price is uncommon. I found no public board that does it (**UNKNOWN** whether one exists).
2. **ASSUMPTION, supported by the FACTs in §3:** "params ÷ price" is a poor capability proxy. MoE total vs active counts alone can differ by about 18–23× (DeepSeek-V3, gpt-oss-120b). Distillation, quantization, provider margins, and reasoning-token volume also break the link between size and either capability or cost.
3. **FACT:** Closed labs (OpenAI, Google, xAI, Amazon, Mistral) score zero on FMTI's model-information indicators, which include model size. Anthropic does not publish counts either (§2). Published estimators of hidden size are wide: Epoch's inference-economics estimates are "off by a factor of 2", IKP's 90% prediction interval is about 3.2×, and NightVision's parameter error is about 53%.
4. **FACT (repo inspection):** minibench already ships a cost-vs-pass-rate Pareto frontier (`_pareto_frontier` in `backend/app/agents_router.py`, "Capability vs. cost" chart in `frontend/src/pages/Models.tsx`) and a 1:3 in:out blended price. The brief says minibench has "no cost or Pareto work yet". That is wrong. What it lacks is parameter counts.
5. **Verdict:** minibench is a good home for a score-per-dollar view with size shown as a secondary channel. The price-to-size inverse estimator belongs in a separate research repo or notebook (§4.5).
6. **Addendum 1 (FACT §8):** Kyle's premise is that agentic work is output-heavy. By *token count* the opposite holds: OpenRouter averages about 6K prompt vs 400 completion tokens per request, and code requests "routinely exceed 20K input tokens". By *dollars*, output and reasoning can still dominate: published output prices run 1–5× input, and in AA's own example payload reasoning cost exceeds input cost. AA itself moved from a 3:1 blend to a 7:2:1 cache-hit:input:output blend. Use a configurable workload profile, not output-only.
7. **Addendum 2 (FACT §9–§11):** API price ≠ lab cost, and the gap differs by lab. Google owns its silicon (TPUs). xAI owns Colossus and now *leases* it to Anthropic for $1.25B/month (SpaceX S-1, via TechCrunch). Anthropic rents (AWS Trainium, Google TPUs, xAI Colossus). OpenAI rents across Azure, Oracle, AWS and Cerebras, with its own Broadcom chip arriving from late 2026. Hardware ownership is a first-order methodology risk for any price-to-size inversion.
8. **Kyle's hypotheses (§11):** (a) OpenAI uses Cerebras = FACT. "Keeps most of it for itself" is UNKNOWN; the only evidence is a Pro-only Cerebras model. "Cerebras released a $500 plan" is **not supported**: the $500 plan is *OpenAI's* ChatGPT Pro 500 (2026-09-29), and OpenAI does not name the hardware behind it. Cerebras Code plans cost $50 and $200. (b) FACT for both parts: xAI owns its data centres and sells compute to Anthropic. (c) The general principle is supported in direction. Its magnitude is UNKNOWN.

---

## §1 Existing public work on price-performance

| # | Source | What it measures | Gap vs Kyle's idea |
|---|---|---|---|
| 1.1 | Artificial Analysis (AA) | Intelligence Index plus **cost per task** and cost to run the index, built from input, cache-hit, cache-write, reasoning and answer token prices. Pareto chart of intelligence vs cost per task. | Measured cost × score, not size. Shows open-weights intelligence vs total and active params as a separate chart, never params ÷ price. Closed models have no size. |
| 1.2 | LMArena / Arena | Pareto frontier of Arena score vs **blended $/1M at a 3:1 ratio** (added April 2026). Agent Arena adds cost per task at p25/p50/p95. | Preference Elo, not size. A public comment on the launch post asks for token-normalized cost. |
| 1.3 | Epoch AI | Cost frontier per benchmark over time ("price of thought"), plus parameter and compute database with confidence tiers. | Research outputs, not a live leaderboard. Size is often "Unknown" for closed models. |
| 1.4 | MIT FutureTech (Gundlach et al.) | Benchmark-level price trends (5–10×/yr). Open vs closed and MoE vs dense frontiers. | Academic, snapshot-based. Splits by architecture but does not normalize by size. |
| 1.5 | HF Open LLM Leaderboard | Open models only. Recorded `#Params (B)`, an MoE flag, and an evaluation CO₂ cost. **Retired** in 2025. | No API price. Archived. |
| 1.6 | OpenRouter `/api/v1/models` | Per-token prices (prompt, completion, cache, reasoning), sort by price, throughput, latency, AA intelligence index. | **No parameter field** in the documented schema. |
| 1.7 | the-frontier.app | LMArena Elo vs OpenRouter $/1M, adjustable token ratio and caching. | Third-party mashup. No size. |
| 1.8 | Densing Law (Huang et al. 2025) | Capability per parameter ("capability density") over time. | Per parameter, not per dollar. Contested by IKP for factual knowledge (§2.4). |
| 1.9 | Cost-of-pass (Erol et al. 2025) | Expected $ to get one correct answer. | Closest to a principled score-per-$ metric. Not a live board. |

Evidence:
- 1.1 **FACT:** AA "Cost per Intelligence Index Task" is a "weighted average cost … calculated from input, cache hit, cache write, reasoning, and answer token prices" — https://artificialanalysis.ai/articles/artificial-analysis-intelligence-index-v4-3 (accessed 2026-10-02). AA reports a 4-lab Pareto frontier and gives an example: "GPT-6 Astra (max) and Claude Fable 5.1 … both score 53, but … $3.26 and $7.63" per task (same URL).
- 1.1 **FACT:** AA has open-weights charts of intelligence vs total parameters and vs active parameters — https://artificialanalysis.ai/models/open-source (accessed 2026-10-02, via search summary. I did not render the chart myself).
- 1.1 **FACT:** AA v4.1 added cost, time and tokens per task, plus cached-input reporting — https://artificialanalysis.ai/articles/artificial-analysis-intelligence-index-v4-1 (accessed 2026-10-02).
- 1.2 **FACT:** "Arena score vs. a blended price per 1M tokens (3:1 Ratio)" Pareto, posted 2026-04-01 — https://www.linkedin.com/posts/arenaai_weve-added-pareto-frontier-charts-to-the-activity-7445144386054828033-jYa1 (accessed 2026-10-02). Agent cost per task with p25/p50/p95 — https://arena.ai/blog/agent-categories-and-cost (accessed 2026-10-02).
- 1.2 **UNKNOWN:** whether Arena's "3:1" means input:output or the reverse. The post does not say.
- 1.3 **FACT:** Epoch, "The plunging price of thought" (2026-09-22): the cost of a fixed performance level fell about 47%/quarter (13×/yr). It uses the CAISI truncation method to trace cost-performance curves — https://epoch.ai/publications/the-plunging-price-of-thought (accessed 2026-10-02).
- 1.3 **FACT:** Epoch's database confidence tiers: "Confident" within 3×, "Likely" within 10×, "Speculative" within 30× — https://epoch.ai/data/ai-models (accessed 2026-10-02).
- 1.4 **FACT:** Gundlach et al. find 5–10×/yr price declines at fixed performance. Frontier-run cost rises 3–18×/yr. Open models dominate the low and mid-cost GPQA frontier — https://arxiv.org/abs/2511.23455 (accessed 2026-10-02).
- 1.5 **FACT:** Retirement announcement — https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard/discussions/1135. Dataset columns include `#Params (B)`, `MoE`, `CO₂ cost (kg)` — https://huggingface.co/datasets/open-llm-leaderboard/contents. CO₂ is evaluation-time only (8×H100 at 5.6 kW, Virginia grid) — https://huggingface.co/docs/leaderboards/open_llm_leaderboard/emissions (all accessed 2026-10-02).
- 1.6 **FACT:** The OpenRouter models schema shows `pricing`, `context_length`, `architecture` (modality, tokenizer), sort by price, throughput, latency or intelligence. It has no parameter-count field — https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties (accessed 2026-10-02).
- 1.7 **FACT:** https://the-frontier.app/ (accessed 2026-10-02).
- 1.8/1.9 **FACT (secondary citation):** Densing Law, Huang et al. 2025, *Nature Machine Intelligence*, as cited in arXiv 2604.24827. Cost-of-pass, Erol et al., arXiv 2504.13359, as cited in arXiv 2511.23455. I did not open either primary paper (**UNKNOWN** details).
- **UNKNOWN:** a public board that plots parameters ÷ $/token. One targeted search found none: https://llmprice.gitlab.io/ and similar sites are price-only.

**Gap summary (ASSUMPTION):** Nobody shows on one chart (a) measured score per $, (b) disclosed size for open weights, and (c) *banded* size estimates for closed models with provenance labels. Charts that mix open and closed models either drop size altogether (AA main chart, Arena) or restrict themselves to open weights (AA size charts, HF).

---

## §2 Parameter disclosure and hidden-size estimation

### 2.1 How open models publish size
- **FACT:** DeepSeek-V3 has 671B total and 37B activated per token. The HF checkpoint is 685B because it adds a 14B MTP module — https://github.com/deepseek-ai/DeepSeek-V3/blob/main/README.md (accessed 2026-10-02).
- **FACT:** gpt-oss-120b has 116.83B total (≈117B) and 5.13B active per token. Unembedding counts as active, embeddings do not — https://arxiv.org/html/2508.10925 (accessed 2026-10-02).
- **FACT:** Grok-1 (xAI, open-weight 2024-03-17) has 314B MoE parameters, 8 experts with 2 active per token — https://x.ai/news/grok-os and https://github.com/xai-org/grok-1 (accessed 2026-10-02).
- **FACT:** NightVision Appendix C tabulates config-derived total and active counts (e.g. Qwen3-30B-A3B is 30.5B / 3.4B) — https://arxiv.org/abs/2607.01313 (accessed 2026-10-02).
- **ASSUMPTION:** Conventions differ between vendors: embeddings in or out, MTP or vision towers in or out, and "active" defined differently. The DeepSeek 671 vs 685 and gpt-oss embedding rule above are examples. A benchmark must store `total_params`, `active_params`, `count_convention`, and `source_url`.

### 2.2 How closed labs withhold size
- **FACT:** The GPT-4 Technical Report says it gives "no further details about the architecture (including model size)" — https://arxiv.org/abs/2303.08774 (accessed 2026-10-02).
- **FACT:** FMTI 2025: "Amazon, Google, Midjourney, Mistral, OpenAI and xAI do not score any indicators in the model information subdomain … (which includes … model size …)" — https://crfm.stanford.edu/fmti/December-2025/index.html (accessed 2026-10-02).
- **FACT:** Epoch lists Claude 3.5 Sonnet parameters as "Unknown", training compute 2.7e25 FLOP, and price $3 / $15 per 1M in/out — https://epoch.ai/models/claude-3-5-sonnet (accessed 2026-10-02). This is a cited example only.
- **FACT:** xAI open-sourced Grok-1 (above) but scores 14 on FMTI 2025, tied for lowest (FMTI URL above). Opening an old model does not mean disclosing current ones.
- **UNKNOWN:** whether Anthropic or Google have disclosed a parameter count for any current frontier API model. I found none.

### 2.3 Published methods for inferring size

| Method | Signal | Reported accuracy | Source |
|---|---|---|---|
| Inference economics (Epoch) | price + tokens/s + assumed GPU markup | "could easily be off by a factor of 2" | Epoch Gradient Update (2024-12) |
| Logit-bias / softmax-bottleneck attack (Carlini et al., ICML 2024) | full or top-k logprobs + logit bias | exact hidden dim for ada/babbage (1024/2048), gpt-3.5-turbo hidden dim recovered | PMLR v235 |
| NightVision (CMU, arXiv 2607.01313) | single-token logprob + TTFT timing | hidden dim ~23% mean rel. err.; params ~53% for ≥3B models; needs >2×10¹¹ tokens | arXiv |
| IKP — Incompressible Knowledge Probes (arXiv 2604.24827) | accuracy on 1,311 obscure facts | LOO median 1.48×; 72% within 2×; 90% PI ≈3.2× | arXiv |
| Press/"mined" estimates (e.g., MEDEC paper) | secondary reporting | none; authors say unverified | arXiv 2412.19260 |
| LeakyLMs per-token timing | timing side channel | recovers layers/dims, not total params | arXiv 2607.20723 |

Evidence and critique:
- **FACT:** Epoch estimated GPT-4o at about 200B total parameters and Claude 3.5 Sonnet at about 400B. The inputs were serving speed (GPT-4o at 100–150 tok/s vs GPT-4 Turbo at ~55) and price (GPT-4o at $10/1M output in Nov 2024). The authors call it "rough" and possibly "off by a factor of 2" — https://epoch.ai/gradient-updates/frontier-language-models-have-become-much-smaller (accessed 2026-10-02).
- **FACT:** Carlini et al.: "For under $20 … extracts the entire projection matrix of … ada and babbage … hidden dimension of 1024 and 2048." After disclosure, providers added defenses — https://proceedings.mlr.press/v235/carlini24a.html and https://arxiv.org/pdf/2403.06634 (accessed 2026-10-02).
- **FACT:** NightVision notes that providers now expose only single-token logprobs with no logit bias. The paper estimates params using a LLaMA-style formula and was evaluated on models from 135M to 30B. Error exceeds 100% below 3B. MoE serving deployments are untested. The authors put the cost at 12–190× Carlini's — https://arxiv.org/abs/2607.01313 (accessed 2026-10-02).
- **FACT:** IKP calibrates on 93 open models (135M–1.6T, R²=0.910). Total parameters predict MoE knowledge better than active (R² 0.67 vs 0.41). Refusal-heavy models read as lower bounds. Above 1T there are only 2 calibration anchors. It gives banded estimates for 97 proprietary models, e.g. "GPT-5.5 ~4.7T [1.5T–15.1T]" — https://arxiv.org/abs/2604.24827 (accessed 2026-10-02). Code: https://github.com/19PINE-AI/ikp (not opened, **UNKNOWN** license).
- **FACT:** The IKP paper itself describes inference economics as carrying "2×+ uncertainty from hardware, batching, and serving-stack assumptions" (same URL).
- **FACT:** MEDEC lists GPT-4o-mini at about 8B and Claude 3.5 Sonnet at about 175B, mined from public articles and described as unverified — https://arxiv.org/abs/2412.19260 (accessed 2026-10-02, via search summary). Note that this contradicts Epoch's ~400B Sonnet guess, which shows how widely estimates spread.
- **FACT (secondary):** "Inference economics of language models", Erdil 2025, arXiv 2506.04645, as cited in arXiv 2511.23455. I did not open it.

### 2.4 Reliability critique
- **ASSUMPTION:** Every method above produces a *band*, not a number. At 2–3× error, a closed model's "params ÷ price" value can move by up to about 10× end to end, enough to move it from one end of the Pareto to the other.
- **ASSUMPTION:** Estimating size *from price*, then dividing size *by price*, is circular. The output becomes mostly a function of price plus the assumed markup. This is the main methodological trap in Kyle's "second pass".
- **FACT-based caution:** IKP (knowledge capacity) and NightVision or Epoch (serving cost) measure different things. IKP effective capacity could exceed the compute actually served per token: total vs active, R² 0.67 vs 0.41.
- **ASSUMPTION:** The IKP and NightVision papers are 2026 preprints (April and July). Neither has been independently replicated as far as I found. IKP's own acknowledgements cite an external sanity check that forced a scoring revision.

---

## §3 Metric validity: problems with "params ÷ price"

Define Kyle's raw metric as `V = P / price` for one value per model. Problems:

| # | Problem | Evidence | Effect on V |
|---|---|---|---|
| 3.1 | MoE: which P? | DeepSeek-V3 671B/37B (≈18× ratio); gpt-oss-120b 117B/5.1B (≈23× ratio) — FACT counts in §2.1; ratios are my arithmetic | V swings ~20× on a definitional choice |
| 3.2 | Capability per param is not constant over time | Densing Law (reasoning density rising) vs IKP (factual capacity flat, +0.0013/mo, p=0.19) — FACT, arXiv 2604.24827 | Newer small models look "worse value" under V despite being better |
| 3.3 | Distillation / post-training | IKP: refusal tuning cuts scores by tens of pp (Sonnet 4 vs 3.7 Sonnet: 21.5 pp) — FACT, same URL | Same P, very different capability |
| 3.4 | Quantization | NightVision notes production bf16 / reduced precision; Cai et al. 2025 (via IKP) say text tests detect quantization only ~50% of the time — FACT (secondary) | Provider can serve P at lower cost and quality; V can't see it |
| 3.5 | Provider margins / subsidies | DeepSeek reported a *theoretical* 545% daily margin (2025-02-27/28) — FACT, https://github.com/deepseek-ai/open-infra-index/blob/main/202502OpenSourceWeek/day_6_one_more_thing_deepseekV3R1_inference_system_overview.md (accessed 2026-10-02); Gundlach et al. treat closed vs open price gap as partly competitive/markup — FACT | Price ≠ cost; V measures pricing strategy |
| 3.6 | Price falls fast | ~13×/yr at fixed performance (Epoch, 2026-09-22) — FACT | V for a model drifts with time; must be timestamped |
| 3.7 | Reasoning tokens / verbosity | Grok 4.6 cost per AA task $0.48 (low) → $2.32 (xhigh) for one model; avg output 10.3k vs 37.6k tokens — FACT, https://aiagentstore.ai/data/model-effort/grok-4-6/aa-intelligence-v4-3-2.csv (third-party mirror of AA data, accessed 2026-10-02) | Same $/token, ~5× cost/task spread across efforts |
| 3.8 | Cached / batch pricing | AA prices cache hit and cache write separately — FACT (§1.1). AA comparison example cache-hit $0.25 vs $1.00 for two models at the same $10 input — FACT, https://artificialanalysis.ai/models/comparisons (accessed 2026-10-02) | Workload-dependent; one "price" is a fiction |
| 3.9 | Input/output blend | Arena uses "3:1"; minibench Usage Board uses **1:3 in:out** — FACT (§1.2, §4) | Ranking order flips with the ratio (worked example §8.3). AA now uses 7:2:1 cache:in:out (FACT, §8.2) |
| 3.10 | Same model, many prices | OpenRouter `/models/{author}/{slug}/endpoints` returns per-provider price/latency/throughput — FACT, OpenRouter docs (§1.6) | Which provider's price? Cheapest vs first-party differ |
| 3.11 | Bigger isn't the goal | ASSUMPTION: maximising P/$ rewards buying the *most weights* per dollar, not the most work done | Wrong objective for the "vibe coder" audience (minibench CONTEXT.md) |

**Better formulations (ranked by validity, all ASSUMPTION unless cited):**
1. **Score per dollar on a fixed task set:** `pass_rate` (or AA, Arena or minibench score) on the y axis against **measured $ per task** on the x axis, then the Pareto frontier. This is what AA, Arena-Agent and minibench `/models` already do. Matches cost-of-pass (Erol et al.).
2. **Cost to reach a threshold:** cheapest $ at which a model reaches X% (Epoch's cost frontier `C(t,a)`, FACT, §1.3). Stable across blend ratios because it uses actual token counts.
3. **Effort-curve frontier:** use one run per reasoning effort, or the CAISI truncation method, to trace each model's whole cost-score curve rather than a single point (Epoch, FACT §1.3).
4. **Parameters as a secondary channel only:** marker size or colour = `active_params` (open models, FACT tier) or an IKP or NightVision band (closed models, ESTIMATE tier, drawn as an interval). Never on an axis.
5. **Where params ÷ price *is* valid:** for **open-weight models with known P**, `$ per 1M tokens ÷ active_params` across *hosting providers* measures **provider markup and serving efficiency**, not model capability. It answers "who hosts model X cheapest per unit of compute", and it is a defensible use of Kyle's ratio.
6. Always store `as_of`, `blend_ratio`, `price_source`, `cache_assumption`, and `provider`.

---

## §4 RaapTech fit — `RaapTechllc/minibench` (read-only inspection)

Inspected main @ `f9e2b313d1c103743faa57a5a75adcfc511b683a` (commit time 2026-09-14 10:46 CT), using the GitHub MCP tools and a throwaway read-only shallow clone in `/tmp/mb` on the box. Nothing was pushed. Repo: https://github.com/RaapTechllc/minibench (accessed 2026-10-02).

### 4.1 Structure (FACT)
- Monorepo: `backend/` (FastAPI + async SQLAlchemy + Postgres, port 3070), `frontend/` (React 19, Vite, TS, Tailwind v4, **Recharts**, port 3071), `cli/` (legacy hardware bench via Ollama), `agentbench/` (Python evaluation runners, graders, MoA, OpenRouter poller), `docs/` (PRDs, ADRs 0001–0004), Docker Compose, 4-job CI. Source: README.md.
- The project describes itself as measuring "whether AI models and agent configurations finish useful work, with completion, cost, latency, and reproducibility receipts". The active focus is the **Real-Work Agent Cabinet** (docs/PROJECT-STATUS.md, reviewed 2026-09-04).
- Surfaces: Solo Cabinet `/models`, Multiplayer `/agents` (cost per task, "$/quarter"), Agent Cabinet, and the OpenRouter **Usage Board** `/usage/cost|task|latency`. The README says they share no composite score by design.

### 4.2 Existing cost / Pareto work (FACT, contradicts the brief)
- `backend/app/agents_router.py::_pareto_frontier()` computes the "accuracy-vs-cost Pareto frontier", flags each row with `on_pareto_frontier`, and is used on `/api/v1/agents/leaderboard` and `/api/v1/agents/models/leaderboard`.
- `frontend/src/pages/Models.tsx` renders a "Capability vs. cost" scatter (cost per task × pass rate) with "Gold = Pareto-optimal".
- `agentbench/board.py::blended_per_million()`: "USD per 1M tokens at a 1:3 in:out mix". CONTEXT.md defines "Blended price" the same way.
- `agentbench/cost_check.py`: a CI budget guard that caps a suite's worst-case cost on the priciest catalog model (default $15).
- `backend/app/data/known_models_seed.json`: 42 OpenRouter models. Fields: `provider, model_id, display_name, family, license, context_length, prompt_price, completion_price, snapshot_date`. **No parameter fields.** Generated 2026-07-06 from `openrouter.ai/api/v1/models`.
- `agentbench/results/`: 26 committed result artifacts, e.g. `minibench-core-v1-anthropic-claude-haiku-4.5.json`.
- docs/PROJECT-STATUS.md mentions an unfinished July "Value Terminal" proposal on a local branch. It was not accepted. **UNKNOWN** whether its content overlaps this idea.
- Proposed **Benchmark Lens** (ADR 0004, not implemented): "republishes cited external agentic benchmark claims with provenance tiers … adds no composite."

### 4.3 The three open PRs (FACT, all opened 2026-09-14, all UTC-stamped and converted to CT)
| PR | Title | State | Summary | Interaction with this idea |
|---|---|---|---|---|
| #68 | E2.1: cut legacy hardware/dashboard frontend, add landing page | open, ready (not draft), opened 11:06 CT | Deletes Dashboard, Hardware, Submit, Compare, Leaderboard, and MoaCalculator pages. Adds `Home.tsx`. Nav becomes Home / Agent Cabinet / Models / Agents / Usage / Methodology. | Removes the legacy HEI = (tok/s × quality)/price "value per dollar" chart. Any new value chart should live on `/models` or `/usage`. |
| #69 | E2.2: cut legacy hardware API, make backend run on SQLite | draft, opened 12:13 CT | Deletes `Benchmark`, `HardwareSpec`, `ModelQuality` models and `/api/v1/{leaderboard,hardware,models,…}` routes. Adds SQLite dev support. | Removes legacy `/api/v1/models` (quality table). A parameter catalog would extend `KnownModel` and the seed JSON instead. Merge conflicts are likely if built before #69 lands (ASSUMPTION). |
| #70 | Propose oddball task categories (data security and constrained creative writing) | draft, docs only, opened 12:15 CT | New categories, a `constraint_pack` grader, and a separate "Taste" human-vote evidence class. | No direct overlap. Its rule that each evidence class stays separate and never enters a score supports keeping size estimates in a separate tier. |

### 4.4 How it could slot in (ASSUMPTION — design sketch, not a change)
- **Data:** add optional `total_params_b`, `active_params_b`, `params_source_url`, `params_tier` (`disclosed` | `estimated:<method>` | `unknown`), and `params_band_low/high` to the `KnownModel` seed. Open models get `disclosed` with a model-card URL. Closed models get `unknown` by default, or an `estimated:ikp` band with citation.
- **Surface A, low risk:** on `/models` "Capability vs. cost", encode marker size or opacity by `active_params` when the tier is `disclosed`. Closed or unknown models get a hollow marker. Axes and Pareto logic stay as they are.
- **Surface B:** in the Usage Board, add a "best-by-$-per-active-param" compare route for open weights only. This is the provider-markup view from §3 item 5. It fits Mode A because it needs only `/models` plus a static param table.
- **Surface C:** the Benchmark Lens (ADR 0004) is the natural place to republish external size *estimates* (Epoch, IKP) with provenance tiers. Its stated design is cited, tiered and never merged into a composite.
- **Sequencing:** wait for #68 and #69 to land (or be closed) before touching the frontend or the backend models.

### 4.5 Fit verdict
- **Good fit** for score-per-dollar with size as an annotation (sparks 1 and 2). The Pareto code, blended price, OpenRouter catalog and provenance culture (citations, `as_of`, fixture-vs-live labels) already exist.
- **Poor fit** for "infer hidden params from price" as a headline metric. It conflicts with the repo's "no composite" and provenance rules, and §2.4 shows it is circular. Alternatives: a standalone `RaapTechllc/price-implied-size` research repo or notebook, or a blog post. Its outputs can then be fed into minibench's Benchmark Lens as an `estimated` tier.

---

## §5 Idea sparks (ranked; see §12 for the re-rank under the reframe)

**#1 — "Value Frontier with Size Lens" inside minibench (recommended)**
- Score per $ (measured cost per task) Pareto. Marker encodes `active_params` for disclosed open weights and a hollow or banded marker for closed models. Toggles for blend ratio and cache assumption.
- Why first: reuses `_pareto_frontier`, Recharts and the seed catalog. It is valid under §3 and visibly different from AA and Arena because size is shown with provenance.
- Risk: limited novelty (ASSUMPTION). The size channel is the differentiator.

**#2 — Open-Weight Provider Markup Index**
- For each open model with disclosed P, compute `$ per 1M tokens / active_params` for each OpenRouter provider endpoint. Rank providers and track over time.
- Why: Kyle's ratio on the one population where it is valid (P is a FACT). It answers a real buyer question: who is overcharging for the same weights?
- Gaps: the endpoints API needs live polling (Mode A allows only the listed Data API paths, so `/models/{id}/endpoints` would need an ADR change, **UNKNOWN** whether permitted). Quantization differences between providers confound results (§3.4).

**#3 — Price-Implied Size estimator, published as research (not a leaderboard)**
- Fit `log(price)` against `log(active_params)` on open-weight models using cheapest-provider prices. Invert the fit for closed models and report 90% intervals. Cross-check against IKP bands and Epoch's guesses, and publish the disagreement.
- Why: a novel, shareable artifact for RaapTech. It is honest only if presented as "what the price implies under assumption X".
- Risk: circular (§2.4). Closed-lab markup is unobservable. Expect at least 2–3× error. Keep it separate from minibench scores.

---

## §6 Known gaps and unverified items

- **UNKNOWN:** whether any public site plots params ÷ price directly. One search found none. A broader search, including GitHub, was not done.
- **RESOLVED (addendum work):** AA's blended price is now 7:2:1 cache-hit:input:output (§8.2). That explains the $7.175 figure. **Still UNKNOWN:** whether Arena's "3:1" means input:output. It probably mirrors AA's legacy 3:1 input:output (ASSUMPTION).
- **Unverified:** AA open-weights parameter charts (search summary only, not rendered). AA's per-task figures come partly from a third-party CSV mirror (aiagentstore.ai), not AA's own export.
- **Unverified:** MEDEC estimate details (search summary only). The Densing Law and Cost-of-pass primary papers were not opened (secondary citations).
- **Unverified:** IKP code license and probe availability. The paper says probes are released, but the Limitations section says they "should remain private", which is internally inconsistent.
- **UNKNOWN:** current disclosed parameter counts for any Anthropic, Google, OpenAI or xAI frontier API model as of 2026-10. None found.
- **UNKNOWN:** whether OpenRouter's per-provider endpoint data records quantization, and whether minibench's Mode A policy (ADR 0002/0003) can be extended to `/endpoints`.
- **UNKNOWN:** the status and contents of PR #67 (the "era 2 cut" plan referenced by #68 and #69). I did not open it. Also the content of the unaccepted "Value Terminal" branch, which exists only locally per PROJECT-STATUS.md.
- **Not done:** I did not use the `grok` CLI. WebSearch and WebFetch were enough. I fetched no vendor pricing pages, so no current per-token prices are asserted here beyond the cited, dated examples.
- **Addenda gaps:** Many deal figures come from search summaries or secondary press (Reuters/The Information, TechCrunch reading the S-1). I did not read the S-1 itself.
  - **UNKNOWN:** per-token costs of TPU, Trainium, Cerebras or Broadcom silicon.
  - **UNKNOWN:** OpenAI's internal routing of Cerebras capacity.
  - **UNKNOWN:** any Microsoft/Azure–OpenAI or Anthropic–Azure terms (not researched).
  - **UNKNOWN:** a per-category in:out token ratio for agentic loops.
  - The §10.1 GPU-hour figure is illustrative arithmetic.
- **Caveat:** many 2026 model names and figures come from single sources (AA, Epoch, the IKP preprint) and were not cross-checked against vendor announcements.

## §8 Addendum 1: output-weighted cost

### 8.1 Published input:output price ratios (cited examples, each dated)
| Model / offer | In $/1M | Out $/1M | Out÷In | Source & date |
|---|---|---|---|---|
| Claude 3.5 Sonnet | 3 | 15 | 5× | Epoch model page, accessed 2026-10-02 — https://epoch.ai/models/claude-3-5-sonnet |
| GPT-4 (OpenRouter docs sample) | 30 | 60 | 2× | OpenRouter API docs example payload, accessed 2026-10-02 (§1.6 URL) |
| "Claude Fable 5.1" / "GPT-6 Astra" (AA comparison) | 10 | 50 | 5× | https://artificialanalysis.ai/models/comparisons, accessed 2026-10-02 |
| Third model on same AA page (name not captured) | 1.25 | 4.25 | 3.4× | same |
| AA Data API example payload (model unnamed) | 0.06 | 0.20 | 3.3× | https://artificialanalysis.ai/data-api/docs, accessed 2026-10-02 |
| Qwen3.7 Max (OpenRouter snapshot) | 1.25 | 3.75 | 3× | minibench `known_models_seed.json`, snapshot_date 2026-05-21 |
| Cerebras Qwen3-Coder at Cerebras Code launch | 2 | 2 | 1× | secondary: https://tomrochette.com/agents/model-access/cerebras-code/ (says launch price 2025-08; current Cerebras rate card not extractable, **unverified**) |
- **FACT:** Cache-hit prices are far below input prices: $0.25 vs $1.00 for two models that both charge $10 input (AA comparisons). AA Data API example: cache hit $0.015, input $0.06, cache write $0.075.
- **ASSUMPTION:** Across these examples output costs 1–5× input. Output-weighting therefore matters most for 5× vendors and least for flat-priced fast-silicon hosts.

### 8.2 Token-mix evidence
- **FACT:** AA methodology: "we calculate a blended price assuming a 7:2:1 ratio of cache hit, input, and output tokens" — https://artificialanalysis.ai/methodology (accessed 2026-10-02). The Data API still exposes `price_1m_blended_3_to_1` alongside `price_1m_blended_7_to_2_to_1` — https://artificialanalysis.ai/data-api/docs (accessed 2026-10-02). Check: (7×0.25 + 2×10 + 50)/10 = 7.175, which matches the AA comparisons figure in §1.
- **FACT:** OpenRouter/a16z "State of AI" (100T tokens): average prompt tokens per request rose from about 1.5K to over 6K, and completions from about 150 to 400. Programming "routinely exceed[s] 20K input tokens". Completion growth comes "mostly due to reasoning tokens". OpenRouter counts reasoning tokens within completion tokens — https://arxiv.org/abs/2601.10088 (PDF read 2026-10-02).
- **ASSUMPTION (arithmetic on the FACT above):** 6K:400 is about 15:1 input:output *by tokens*. Agentic and code traffic is input-heavy in volume, contrary to the addendum's premise.
- **FACT:** AA Data API example payload (one unnamed model, full Intelligence Index): input 140.3M tokens and output 61.3M, of which reasoning is 58.3M and answer 3.0M. Cost fields in that payload show reasoning about $11.66 and input about $8.42 of a $20.69 total. The cost field names were partly truncated in the fetch, so treat the breakdown as **unverified** — https://artificialanalysis.ai/data-api/docs (accessed 2026-10-02).
- **ASSUMPTION (arithmetic):** In that example, reasoning is about 95% of output tokens. Input:output is about 2.3:1 by tokens, yet output still makes up about 56% of cost. So Kyle's intuition holds *in dollars* for reasoning-heavy evaluations even though tokens are input-heavy.
- **FACT:** Effort setting alone moves output volume about 3.7× for one model (Grok 4.6: about 10.3K output tokens per task at low, 37.6K at xhigh; cost per task $0.48 to $2.32). Source: third-party mirror of AA data (§3.7 URL).
- **UNKNOWN:** a public token-mix breakdown specifically for *agentic tool-call loops*, meaning per-turn input re-reads vs output. OpenRouter's study reports a rising tool-call share but no per-category in:out ratio that I could extract.

### 8.3 Candidate weightings and ranking effects
Define `cost = w_cache·p_cache + w_in·p_in + w_out·p_out` (weights sum to 1), or use measured tokens per task.

| Weighting | Formula | Who it favours (ASSUMPTION) |
|---|---|---|
| Output-only | `p_out` | Flat-priced or fast-silicon hosts (1×). Penalises 5× vendors. |
| Legacy 3:1 in:out (AA legacy; Arena "3:1") | `(3p_in+p_out)/4` | Cheap-input vendors |
| minibench current 1:3 in:out | `(p_in+3p_out)/4` | Between the two above. Already in `agentbench/board.py` |
| AA 7:2:1 cache:in:out | `(7p_c+2p_in+p_out)/10` | Vendors with deep cache discounts |
| OpenRouter observed ~15:1 in:out | `(15p_in+p_out)/16` | Cheap-input vendors (strongest) |
| **Measured** tokens/task × prices (recommended) | Σ tokens_type × price_type | Reflects verbosity and reasoning. Already how AA and minibench cost per task work |

- **Worked flip (ASSUMPTION, arithmetic on dated cited prices from different dates, illustration only):** Cerebras-launch Qwen3-Coder ($2/$2) vs Qwen3.7 Max ($1.25/$3.75):
  - 3:1 → 2.00 vs 1.875 (Qwen Max cheaper)
  - 15:1 → 2.00 vs 1.41 (Qwen Max cheaper)
  - 1:3 → 2.00 vs 3.125 (Cerebras cheaper)
  - output-only → 2.00 vs 3.75 (Cerebras cheaper)
  - **The ranking flips with the weighting.**
- **Recommendation (ASSUMPTION):** make a **workload profile** a first-class, labelled parameter with presets: `chat-3:1`, `aa-7:2:1`, `agentic-measured`, `output-only`. Default the headline to *measured* cost per task. Show rank stability across profiles, e.g. "rank changes under N of 4 profiles". Output-only is a useful stress test but should not be the default, given the token-volume evidence in §8.2.

---

## §9 Addendum 2: reframe as an investigation of what labs actually pay

**New question (Kyle):** what does each lab actually pay per token or per parameter for inference? Estimate it from disclosed sizes (open weights), API prices, and evidence about hardware and deals.

**Method sketch (ASSUMPTION):**
1. **Calibrate on open weights served by competitive third-party hosts.** P is known (FACT tier) and markups are competitive. Gundlach et al. assume open models are "not priced at a significant markup relative to the necessary GPU resources" (FACT, arXiv 2511.23455). Epoch reports direct rented-hardware costs within 30% of API prices for 5 open models (FACT, §1.3 URL). Fit `$/1M out` against `active_params` and hardware class to get a **cost curve**.
2. **Anchor dollar-per-hardware-hour from disclosed deals** (§10). Examples: DeepSeek's H800 rental assumption and the Anthropic→xAI lease.
3. **For each closed lab,** compare API price against the calibrated cost curve evaluated at an *external* size band (IKP, Epoch). Never use a size inferred from the same price, which is circular (§2.4). The residual is markup ± hardware advantage ± subsidy. Report it as a **range** (§12).
4. **Throughput cross-check:** tokens/s per user constrains size *given* a hardware class. On Cerebras or Groq-class silicon, the same size runs much faster, so hardware must be identified first (§10).

---

## §10 Compute deals, ownership and silicon: public evidence

### 10.1 By lab
**OpenAI: mostly rented, diversifying into custom and alternative silicon**
- **FACT:** Cerebras. 750 MW over three years: 250 MW by end-2026, 500 MW by end-2027, 750 MW by end-2028. Cerebras-hosted, "dedicated low-latency inference". Initial value over $10B (Reuters). The SEC-filed master agreement gives OpenAI an option on more capacity on equal or better terms. Later reporting (The Information, via Reuters, 2026-04-17) says over $20B plus warrants for up to about 10% equity. Sources:
  - https://www.cerebras.ai/blog/openai-partners-with-cerebras-to-bring-high-speed-inference-to-the-mainstream
  - https://www.reuters.com/technology/openai-buy-compute-capacity-startup-cerebras-around-10-billion-wsj-reports-2026-01-14/
  - https://www.sec.gov/Archives/edgar/data/2021728/000162828026029503/exhibit1011-sx1a.htm
  - https://www.reuters.com/technology/openai-spend-more-than-20-billion-cerebras-chips-receive-equity-stake-2026-04-17/
  - All accessed 2026-10-02.
- **FACT:** GPT-5.3-Codex-Spark runs on Cerebras at over 1,000 tok/s. It is a research preview for ChatGPT Pro users. API access is limited to "select design partners" — https://openai.com/index/introducing-gpt-5-3-codex-spark/ (accessed 2026-10-02, via search summary).
- **FACT:** Other deals (all via search summaries of first-party pages, accessed 2026-10-02):
  - Oracle/Stargate, up to 4.5 GW: https://openai.com/index/five-new-stargate-sites/
  - AMD, 6 GW, first 1 GW of MI450 in late 2026: https://newsroom.amd.com/news/amd-and-openai-announce-strategic-partnership-to-d/
  - Broadcom, 10 GW of *OpenAI-designed* accelerators, late 2026 to 2029: https://openai.com/index/openai-and-broadcom-announce-strategic-collaboration/
  - AWS, $38B over 7 years: https://openai.com/index/aws-and-openai-partnership/
  - Nvidia, at least 10 GW
- **FACT:** Paid priority. OpenAI sells a Scale Tier (committed TPM, minimum 30 days, 99.9% uptime) and "Fast mode" / `service_tier="priority"` at premium per-token prices — https://openai.com/api-scale-tier/ and https://developers.openai.com/api/docs/guides/fast-mode (accessed 2026-10-02, via search summary). Consumer side: ChatGPT **Pro 500** ($500/month, launched 2026-09-29) includes "Astra Ultrafast", up to 8× faster in Codex — https://www.businessinsider.com/chatgpt-new-plan-pro-500-cost-compute-allowance-2026-9 (accessed 2026-10-02).

**Anthropic: renter on multiple silicon types, no owned fleet found**
- **FACT:** Google Cloud TPUs, "up to one million", tens of billions of dollars, well over 1 GW in 2026 — https://www.anthropic.com/news/expanding-our-use-of-google-cloud-tpus-and-services. AWS Trainium2 via Project Rainier — https://www.aboutamazon.com/news/aws/aws-project-rainier-ai-trainium-chips-compute-cluster. Expanded Google+Broadcom and Amazon (up to 5 GW) deals — https://www.anthropic.com/news/google-broadcom-partnership-compute and https://www.anthropic.com/news/anthropic-amazon-compute (all accessed 2026-10-02; headlines and search summaries only).
- **FACT:** xAI lease. Access to Colossus 1 (over 220k Nvidia GPUs) "to directly improve capacity for Claude Pro and Claude Max" (xAI, 2026-05-06). The SpaceX S-1 discloses $1.25B/month through May 2029 for roughly 300 MW, discounted for the first two months, terminable on 90 days' notice by either side. The S-1 calls it a way to "monetize unused compute capacity" — https://x.ai/news/anthropic-compute-partnership and https://techcrunch.com/2026/05/20/anthropic-will-pay-xai-1-25-billion-per-month-for-compute/ (accessed 2026-10-02).
- **ASSUMPTION (arithmetic, illustrative):** $1.25B ÷ about 220k GPUs ≈ $5.7K per GPU-month ≈ $7.8 per GPU-hour, blended across H100/H200/GB200, power and facility included. Caveats: unknown share of the 220k allocated to Anthropic, ramp discount, and Colossus II inclusion per Network World. This is the first public *renter-price* anchor for a frontier lab.
- **FACT:** Anthropic's "Priority Tier" reserved capacity is "no longer available for purchase"; existing commitments run to contract end — https://docs.anthropic.com/en/api/service-tiers (accessed 2026-10-02, via search summary).

**Google: owns its silicon and data centres (vertically integrated)**
- **FACT:** Gemini is served on Google's own TPUs, including Ironwood, described as "the first Google TPU for the age of inference" — https://blog.google/innovation-and-ai/infrastructure-and-cloud/google-cloud/ironwood-tpu-age-of-inference/ (accessed 2026-10-02). Google also rents TPUs to Anthropic (above) and reportedly to Meta (secondary: https://winbuzzer.com/2026/03/03/meta-signs-multibillion-dollar-deal-rent-google-tpus-xcxwbn/, **unverified**).

**xAI: owns data centres, now also a seller**
- **FACT:** Colossus 1 has over 220k Nvidia GPUs and is xAI-built. xAI sells capacity to Anthropic (above). The S-1 says it "expect[s] to enter into additional similar services contracts" (TechCrunch, above).
- **Reported, not FACT:** TechCrunch writes that Grok usage "has dropped significantly", freeing servers. This is the outlet's characterisation, **unverified**.

**DeepSeek: renter accounting (self-disclosed)**
- **FACT:** One day (2025-02-27/28): $87,072 GPU rental for an average of 226.75 H800 nodes against $562,027 theoretical revenue at R1 prices, a "545%" theoretical margin. DeepSeek notes actual revenue is lower — §3.5 URL (accessed 2026-10-02).

**Alternative silicon vendors (context)**
- **FACT:** Nvidia paid about $20B for a *non-exclusive license* to Groq's inference technology and hired executives. Groq remains independent — https://groq.com/newsroom/groq-and-nvidia-enter-non-exclusive-inference-technology-licensing-agreement-to-accelerate-ai-inference-at-global-scale and https://www.reuters.com/business/nvidia-buy-ai-chip-startup-groq-about-20-billion-cnbc-reports-2025-12-24/ (accessed 2026-10-02).
- **Search summary only, unverified:** SambaNova positioning SN50 RDUs for decode.
- **FACT:** Cerebras resells API access through OpenRouter, Hugging Face and AWS Marketplace — https://www.cerebras.ai/pricing (accessed 2026-10-02).
- **ASSUMPTION:** Custom ASICs (Google TPU, AWS Trainium, OpenAI–Broadcom) shift cost away from Nvidia margins. Magnitude **UNKNOWN**: no public per-token cost for any of them.

### 10.2 Per-lab distortion table (how each bias moves a price-to-size estimate)
Convention: estimating size from price under an *assumed* markup over a *GPU-rental* cost curve. If true cost is lower than the curve (owned or cheaper silicon, subsidy) or the markup is smaller than assumed, the estimate **under**-states size. If the lab pays a renter premium or charges a speed or priority premium, it **over**-states size. The throughput method has its own row. All entries are ASSUMPTIONs built on the §10.1 FACTs.

| Lab | Ownership / deals (FACT basis) | Price-to-size bias | Throughput-to-size bias | Confidence |
|---|---|---|---|---|
| Google | Owns TPUs and data centres; rents TPUs out | **Under**-estimates (no renter margin; can price near marginal cost; free and promo tiers) | Moderate (TPU speed differs from GPU curve) | Medium |
| xAI | Owns Colossus; sells surplus to Anthropic | **Under**-estimates (owned silicon; incentive to fill idle capacity cheaply) | Low | Medium |
| Anthropic | Rents Trainium, TPU, Nvidia (incl. xAI at ~$1.25B/mo); priority tier closed to new buyers | **Over**-estimates (renter premium stacked on margin); partly offset if Trainium/TPU are cheaper per token than GPUs (UNKNOWN) | Mixed: three silicon types, unknown routing | Low |
| OpenAI | Rents Azure, Oracle, AWS, CoreWeave; Cerebras capacity-as-service; own Broadcom chip from late 2026 | **Over**-estimates on standard tiers (renter + margin); strongly **over** on Fast/priority/Ultrafast tiers (speed premium, not size) | **Under**-estimates on Cerebras-served models (wafer-scale speed looks like a small model) | Low |
| DeepSeek | Rents H800; self-reported theoretical 545% margin | **Over**-estimates if a thin margin is assumed | Low | Medium (self-reported) |
| Third-party open-weight hosts | Competitive renters | ≈ calibration baseline; quantization can bias toward **under** (§3.4) | Hardware-dependent (Groq/Cerebras/SambaNova hosts are fast) | Medium-High |

---

## §11 Kyle's hypotheses: verdicts
| # | Claim | Verdict | Evidence |
|---|---|---|---|
| a1 | OpenAI uses Cerebras | **FACT** | 750 MW deal; Codex-Spark on Cerebras (§10.1) |
| a2 | …but keeps most of that capacity for itself | **UNKNOWN / partially supported** | Only public signal: Codex-Spark is Pro-only, API limited to "select design partners". No disclosure of capacity split. The deal is Cerebras-hosted capacity for "OpenAI customers" (Cerebras blog) |
| a3 | Cerebras just released a $500 plan | **Not supported as stated** | The $500/month plan is **OpenAI's ChatGPT Pro 500** (DevDay 2026-09-29, "Astra Ultrafast"). Pre-launch leaks tied it to Cerebras, but OpenAI pages do not name the hardware (Business Insider; https://pasqualepillitteri.it/en/news/19330/openai-launches-pro-500-500-dollars-month, accessed 2026-10-02). Cerebras Code plans are $50 and $200, shown as sold out — https://www.cerebras.ai/code, https://support.cerebras.net/articles/9996007307-cerebras-code-faq (accessed 2026-10-02). Ultrafast on Cerebras: **UNKNOWN** |
| b1 | xAI owns its own data centres | **FACT** | Colossus 1, "built from the ground up" (xAI), Memphis |
| b2 | xAI sells compute to others, e.g. Anthropic | **FACT** | xAI 2026-05-06 announcement; S-1 terms $1.25B/month to May 2029 (TechCrunch) |
| c1 | Owned or reserved silicon and priority deals mean API price ≠ lab cost | **Supported in direction** | Priority/Scale tiers price capacity, not size; DeepSeek theoretical margin; xAI monetising "unused" capacity. Magnitude per lab **UNKNOWN** |
| c2 | Owners price near marginal cost; renters carry a premium | **ASSUMPTION (plausible, unproven)** | No lab discloses marginal cost. Gundlach et al. attribute part of the closed-vs-open price gap to competition and markup, not ownership. Owners may also price *above* cost to recover capex |

---

## §12 Hardware ownership as a methodology risk, and open decisions for Kyle

**Risk statement (ASSUMPTION):** Price-to-size and size-to-cost inversions assume one shared cost curve. Ownership (Google, xAI), alternative silicon (Cerebras, Groq, TPU, Trainium, custom ASICs), lab-to-lab leases (Anthropic→xAI), and priced priority tiers (OpenAI Fast/Scale, Pro 500) each move a lab off that curve, by unknown amounts and in different directions (§10.2). On top of the about 2–3× size uncertainty (§2.3), any "true cost" point estimate is unsupported.

**Open decisions:**
1. **Present "estimated true cost" as a range?** Recommendation (ASSUMPTION): yes, always. Show low/high bands that combine the size band (IKP/Epoch) × hardware-class cost range × markup range. Never show a point. Label the tier (`disclosed` / `estimated:<method>`).
2. **Back out hardware ownership as a variable?** Options:
   - (i) Treat it as a **categorical covariate** (owned / rented-GPU / rented-alt-silicon / mixed) from §10 evidence and report results stratified by category. Lowest risk.
   - (ii) Fit it as a **latent parameter**. It is not identifiable from price alone: markup and hardware advantage are confounded.
   - (iii) Leave it out and publish the residual as "unexplained price gap".
   - Recommendation (ASSUMPTION): (i) plus (iii). Avoid (ii) unless an independent per-token cost anchor appears, such as a disclosed lease rate × measured throughput.
3. **Which price is "the" price per lab?** First-party standard tier, cheapest third-party host, or batch. This affects every row of §10.2.
4. **Do priority/fast tiers count as separate data points?** They are useful because they isolate the speed premium.
5. **Default workload profile** (§8.3): measured, 7:2:1, or output-only stress test.
6. **Home:** under the reframe, this is research rather than a leaderboard. That strengthens the §4.5 verdict: run the investigation in a separate research repo or notebook, and republish only cited, tiered outputs into minibench (Benchmark Lens / Usage Board).

**Sparks re-ranked under the reframe (ASSUMPTION):**
1. Open-Weight Provider Markup Index (was #2). It now becomes the **calibration layer** for the cost curve and is valid on FACT-tier sizes.
2. Lab True-Cost Range Report (evolves #3). The cost curve plus external size bands plus the §10.2 ownership strata give per-lab *ranges* and an "unexplained gap", published as research.
3. Value Frontier with Size Lens in minibench (was #1). Still the easiest build, but now a by-product rather than the goal.

---

## §7 Source index (all accessed 2026-10-02; placed last, after the addenda §8–§12)
- AA v4.3: https://artificialanalysis.ai/articles/artificial-analysis-intelligence-index-v4-3
- AA v4.1: https://artificialanalysis.ai/articles/artificial-analysis-intelligence-index-v4-1
- AA comparisons: https://artificialanalysis.ai/models/comparisons · open-source: https://artificialanalysis.ai/models/open-source
- Arena Pareto: https://www.linkedin.com/posts/arenaai_weve-added-pareto-frontier-charts-to-the-activity-7445144386054828033-jYa1 · https://arena.ai/blog/agent-categories-and-cost
- Epoch price of thought: https://epoch.ai/publications/the-plunging-price-of-thought
- Epoch smaller models: https://epoch.ai/gradient-updates/frontier-language-models-have-become-much-smaller
- Epoch data: https://epoch.ai/data/ai-models · https://epoch.ai/models/claude-3-5-sonnet
- Gundlach et al.: https://arxiv.org/abs/2511.23455
- IKP: https://arxiv.org/abs/2604.24827 · NightVision: https://arxiv.org/abs/2607.01313
- Carlini et al.: https://proceedings.mlr.press/v235/carlini24a.html
- MEDEC: https://arxiv.org/abs/2412.19260 · GPT-4 TR: https://arxiv.org/abs/2303.08774
- FMTI 2025: https://crfm.stanford.edu/fmti/December-2025/index.html
- DeepSeek-V3: https://github.com/deepseek-ai/DeepSeek-V3/blob/main/README.md · DeepSeek margin: https://github.com/deepseek-ai/open-infra-index
- gpt-oss: https://arxiv.org/html/2508.10925 · Grok-1: https://x.ai/news/grok-os
- HF OLL: https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard/discussions/1135
- OpenRouter models API: https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties
- the-frontier.app: https://the-frontier.app/
- minibench: https://github.com/RaapTechllc/minibench (main @ f9e2b31; PRs #68, #69, #70)
- Addenda: AA methodology https://artificialanalysis.ai/methodology · AA Data API https://artificialanalysis.ai/data-api/docs · OpenRouter State of AI https://arxiv.org/abs/2601.10088
- Cerebras/OpenAI: https://www.cerebras.ai/blog/openai-partners-with-cerebras-to-bring-high-speed-inference-to-the-mainstream · SEC exhibit https://www.sec.gov/Archives/edgar/data/2021728/000162828026029503/exhibit1011-sx1a.htm · Reuters 2026-01-14 & 2026-04-17 · https://openai.com/index/introducing-gpt-5-3-codex-spark/
- Cerebras Code: https://www.cerebras.ai/code · https://support.cerebras.net/articles/9996007307-cerebras-code-faq · https://www.cerebras.ai/pricing
- OpenAI Pro 500: https://www.businessinsider.com/chatgpt-new-plan-pro-500-cost-compute-allowance-2026-9
- xAI/Anthropic: https://x.ai/news/anthropic-compute-partnership · https://techcrunch.com/2026/05/20/anthropic-will-pay-xai-1-25-billion-per-month-for-compute/
- Anthropic compute: https://www.anthropic.com/news/expanding-our-use-of-google-cloud-tpus-and-services · https://www.aboutamazon.com/news/aws/aws-project-rainier-ai-trainium-chips-compute-cluster · https://docs.anthropic.com/en/api/service-tiers
- OpenAI compute: https://openai.com/index/five-new-stargate-sites/ · https://newsroom.amd.com/news/amd-and-openai-announce-strategic-partnership-to-d/ · https://openai.com/index/openai-and-broadcom-announce-strategic-collaboration/ · https://openai.com/index/aws-and-openai-partnership/ · https://openai.com/api-scale-tier/
- Google TPU: https://blog.google/innovation-and-ai/infrastructure-and-cloud/google-cloud/ironwood-tpu-age-of-inference/ · Groq/Nvidia: https://groq.com/newsroom/groq-and-nvidia-enter-non-exclusive-inference-technology-licensing-agreement-to-accelerate-ai-inference-at-global-scale
