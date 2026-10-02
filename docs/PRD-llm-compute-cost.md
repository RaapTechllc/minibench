# PRD: LLM true-compute-cost investigation (spec only)

- **Status:** PROPOSED. Awaiting acceptance by Kyle Raap. No build until §11 GO gate clears.
- **Date:** 2026-10-02.
- **Idea owner:** Kyle Raap (RaapTech). Proposed home: `RaapTechllc/minibench` (notes header).
- **Single source of market facts:** [`docs/research/llm-compute-cost-research-notes-2026-10-02.md`](research/llm-compute-cost-research-notes-2026-10-02.md), frozen 2026-10-02. Cited below as `notes §n`. No price, parameter count, deal figure, or statistic in this document comes from anywhere else.
- **Repo baseline:** `main` at `f9e2b31`, the same commit the notes inspected (notes §4). Open PRs #68, #69, #70 are not touched by this document (notes §4.3).
- **Glossary and decision records:** `CONTEXT.md`; ADR 0002 (Usage Board, Mode A), ADR 0003 (board path), ADR 0004 (Benchmark Lens, proposed). Where this PRD would require an ADR change it says so explicitly, per `docs/agents/domain.md`.

## 0. How to read the labels

| Label | Meaning |
|---|---|
| **FACT** | Carried over from the notes with their URL and access date. Cited as `notes §n`. |
| **ASSUMPTION** | The notes' own reasoning, not sourced. Carried over unchanged. |
| **UNKNOWN** | Not found or not verified in the notes. Never upgraded here. |
| **PROPOSED** | A design choice introduced by this PRD. Not in the notes. Kyle may reject it. |

The project has been reframed (notes header, addendum 2). It started as a size-over-cost ratio (parameter count ÷ per-million-token price) on a Pareto chart. It is now an *investigation of what labs actually pay for inference compute*. The ratio and the Pareto chart are estimation tools, not the product (notes §9–§12).

## 1. Problem

1. **The question.** What does each lab actually pay per token or per parameter for inference? API price is not lab cost, and the gap differs by lab (notes §0.7, §9). The direction of this claim is supported; the magnitude per lab is **UNKNOWN** (notes §11 c1).
2. **Nobody shows the pieces together.** Capability-per-dollar Pareto charts already exist at Artificial Analysis, LMArena, Epoch AI and MIT FutureTech (FACT, notes §0.1). Dividing parameters by price is uncommon and no public board doing it was found (**UNKNOWN** whether one exists, notes §0.1, §6). Charts that mix open and closed models either drop size altogether or restrict themselves to open weights (ASSUMPTION, notes §1 gap summary).
3. **Closed labs withhold size.** OpenAI, Google, xAI, Amazon and Mistral score zero on FMTI's model-information indicators, which include model size; Anthropic does not publish counts either (FACT, notes §0.3, §2.2). Published hidden-size estimators are wide: Epoch's inference-economics estimates are "off by a factor of 2", IKP's 90% prediction interval is about 3.2×, NightVision's parameter error is about 53% (FACT, notes §0.3, §2.3).
4. **The raw ratio is a poor capability proxy.** `V = P / price` swings about 20× on the MoE total-vs-active definitional choice alone, and is broken by distillation, quantization, provider margins, reasoning-token volume, price decline, caching, blend ratio and multi-provider pricing (notes §3, table rows 3.1–3.11; ASSUMPTION, supported by FACTs in §3). The ratio is defensible on one population only: open-weight models with known `P`, across hosting providers, where it measures provider markup and serving efficiency rather than capability (ASSUMPTION, notes §3 item 5).
5. **Hardware ownership breaks a shared cost curve.** Google owns TPUs; xAI owns Colossus and leases it to Anthropic for $1.25B/month; Anthropic rents Trainium, TPUs and Colossus; OpenAI rents across Azure, Oracle, AWS and Cerebras with its own Broadcom chip arriving from late 2026 (FACT, notes §0.7, §10.1). Any price-to-size or size-to-cost inversion that assumes one cost curve is therefore biased per lab, in different directions and by unknown amounts (ASSUMPTION, notes §10.2, §12).
6. **minibench is further along than the brief said.** The brief claimed minibench had "no cost or Pareto work yet". That is wrong: `_pareto_frontier` in `backend/app/agents_router.py`, the "Capability vs. cost" chart in `frontend/src/pages/Models.tsx`, and a 1:3 in:out blended price already exist. What minibench lacks is parameter counts (FACT, repo inspection, notes §0.4, §4.2).
7. **Output weighting.** Kyle wants cost weighted toward output tokens. By token count agentic traffic is input-heavy (OpenRouter averages about 6K prompt vs 400 completion tokens per request; code requests "routinely exceed 20K input tokens"), yet by dollars output and reasoning can still dominate (published output prices run 1–5× input; in AA's example payload reasoning cost exceeds input cost) (FACT, notes §0.6, §8.2). The weighting must therefore be a configurable workload profile, with output-only as a stress test, not the default (ASSUMPTION, notes §8.3).

## 2. Buyer and user: agent vs human

### 2.1 Buyer

Kyle Raap, RaapTech (notes header). Kyle decides GO (§11), resolves the open decisions (§10), and authorizes any publication. The MVP spends nothing on model calls (§5, `AGENTS.md` hard invariants).

### 2.2 Users, by deliverable

| Deliverable (§4) | Primary consumer | Secondary consumer | Is the consumer an agent? |
|---|---|---|---|
| D1 Open-Weight Provider Markup Index | **Vibe coder / normal dev** (`CONTEXT.md` audience) asking "who hosts model X cheapest per unit of compute" (ASSUMPTION, notes §3 item 5, §5 #2) | **Agents** picking a host for a known open model. The Usage Board already exposes an MCP `recommend` tool over a cached board (`docs/PRD-openrouter-usage-board.md`, story 6); D1 output is shaped to be consumable the same way (PROPOSED) | Both. Machine-readable JSON is a first-class output. |
| D2 Lab True-Cost Range Report | **Humans**: Kyle, researchers, readers of a RaapTech research repo, notebook or blog post (ASSUMPTION, notes §4.5, §12 d6) | None by design. Ranges plus ownership strata need interpretation; the report must not be fed to an agent as a cost input (PROPOSED) | No. Human-read research. |
| D3 Value Frontier with Size Lens | **Vibe coder** on `/models` (notes §4.4 Surface A) | **Agents** reading `/api/v1/agents/models/leaderboard`, which already returns `on_pareto_frontier` (FACT, notes §4.2) | Both. Size is an annotation on an existing agent-readable payload. |

### 2.3 Operator

PROPOSED: the computation pipeline (ledger validation, cost-curve fit, range generation, report rendering) is designed to be run end-to-end by a coding agent under the repo's hard invariants, with Kyle as the human gate on publication. Ledger *curation* (entering a parameter count, a price, a deal figure) follows the Benchmark Lens rule: never type a number without the URL and date it came from, and leave untraceable values `null` (`docs/PLAN-benchmark-lens.md`, guardrails). An agent may draft ledger rows; a human verifies URL and date before a row leaves fixture status.

## 3. Agent-First score intent

The notes contain no Agent-First rubric and the repo has none. The six dimensions below are **PROPOSED**. Intent is a 1–5 target per dimension, scored per deliverable, with the evidence that would justify the score.

| # | Dimension (PROPOSED) | D1 Markup Index | D2 Range Report | D3 Value Frontier | Evidence needed to claim the score |
|---|---|---|---|---|---|
| A | **Machine-readable output.** Every artifact has a JSON form with a published schema. | 5 | 3 | 5 | Schema file in `agentbench/data/`; CLI `--out` writes JSON; D2's markdown report is generated from the same JSON (hence 3, not 5, because the narrative is the deliverable). |
| B | **Provenance per number.** Every number carries `source_url`, `as_of`, and a tier. | 5 | 5 | 5 | Loader rejects rows missing URL or `as_of` (ADR 0004 item 1 pattern); tier badge visible wherever a number renders. |
| C | **Offline reproducibility.** Rebuildable from committed fixtures with no key and no network. | 5 | 4 | 5 | CI job without `OPENROUTER_API_KEY` is green; D2 is 4 because the cost-curve fit depends on curated ledgers that a human verified. |
| D | **Agent operability.** An agent can run the pipeline and act on exit codes. | 4 | 3 | 4 | `python -m agentbench.<module> --check` exits non-zero on loader violations; dry-run mode; no interactive prompts. |
| E | **Consumable without human interpretation.** | 4 | 2 | 3 | D1 is a ranked table with one meaning (provider markup). D2 is intervals plus strata and an unexplained gap; it is written for a human reader (notes §12 d6). D3 adds a size channel that still needs the tier legend. |
| F | **Safety and gating.** No paid calls, no publishing, no external communication without owner authorization. | 5 | 5 | 5 | Allowlist tests on the OpenRouter client; `live=false` on fixtures; GO gate (§11) and `AGENTS.md` hard invariants. |

## 4. MVP scope

Scope follows the notes' re-ranked sparks under the reframe (ASSUMPTION, notes §12 "Sparks re-ranked"): the markup index is the baseline and calibration layer, the range report is the investigation, and the minibench view is a by-product.

### 4.1 D1 — Open-Weight Provider Markup Index (baseline; calibration layer)

- For each open-weight model with a disclosed parameter count, compute `$ per 1M tokens ÷ active_params` for each hosting-provider endpoint, rank providers, and track over time (notes §5 #2).
- Why first: it is Kyle's ratio on the one population where it is valid, because `P` is a FACT, and it answers a real buyer question: who is overcharging for the same weights? (ASSUMPTION, notes §5 #2.) Under the reframe it becomes the calibration layer for the cost curve (notes §12).
- Inputs: a **parameter ledger** (open weights, `disclosed` tier) and **per-provider endpoint prices**. The endpoint data path is constrained; see §7 and open decision D7.
- Known confounder: quantization differences between providers (notes §3.4, §5 #2). Whether OpenRouter endpoint data records quantization is **UNKNOWN** (notes §6).
- Fit in minibench: Usage Board "best-by-$-per-active-param" compare route for open weights only (ASSUMPTION, notes §4.4 Surface B).

### 4.2 D2 — Lab True-Cost Range Report (the investigation)

- The cost curve from D1, plus external size bands, plus the ownership strata of notes §10.2, give per-lab cost *ranges* and an "unexplained gap", published as research (notes §12 spark 2).
- Method follows notes §9 (ASSUMPTION): calibrate on open weights served by competitive hosts; anchor dollar-per-hardware-hour from disclosed deals; for each closed lab compare API price against the calibrated curve evaluated at an *external* size band, never one inferred from the same price; cross-check with throughput once hardware is identified.
- Output is always a range, never a point (notes §12 d1, recommendation ASSUMPTION; confirmed as open decision D1).
- Home: the notes' verdict is that this is research, not a leaderboard, and belongs in a separate research repo or notebook with only cited, tiered outputs republished into minibench via the Benchmark Lens or Usage Board (notes §4.5, §12 d6). This is open decision D6, not a settled fact.

### 4.3 D3 — Value Frontier with Size Lens (minibench; by-product)

- On `/models` "Capability vs. cost", encode marker size or opacity by `active_params` when the tier is `disclosed`; closed or unknown models get a hollow marker. Axes and Pareto logic stay as they are (ASSUMPTION, notes §4.4 Surface A, §5 #1).
- Add toggles for workload profile and cache assumption (notes §5 #1).
- Size estimates for closed models, if ever shown, are republished through the Benchmark Lens as an `estimated:<method>` tier with citation, never on an axis (notes §3 item 4, §4.4 Surface C).
- Sequencing: wait for PRs #68 and #69 to land or close before touching the frontend or backend models (ASSUMPTION, notes §4.4). PR #69 removes legacy `/api/v1/models`; a parameter catalog would extend `KnownModel` and the seed JSON instead (notes §4.3).

### 4.4 Deliverable artifacts (PROPOSED)

| Artifact | Form | Lives in |
|---|---|---|
| Parameter ledger | JSON, one row per open-weight model: `model_id`, `total_params_b`, `active_params_b`, `count_convention`, `params_source_url`, `params_tier`, `as_of` (fields per notes §2.1 ASSUMPTION and §4.4) | `agentbench/data/` if D6 picks minibench; otherwise the research repo, mirrored into minibench as a fixture |
| Endpoint price ledger | JSON, one row per (model, provider, service tier): prices by token type, `quantization` or `unknown`, `price_source`, `as_of` | Same |
| Size-band ledger (closed models) | JSON, one row per model: `band_low_b`, `band_high_b`, `size_band_method` (`ikp`, `epoch`), `source_url`, `as_of` | Same; republished via Benchmark Lens tier `estimated:<method>` |
| Deal / ownership ledger | JSON: lab, stratum, deal figure, unit, `source_kind`, `source_url`, `as_of`; derived per-hour arithmetic in a separate ASSUMPTION-labelled field | Same |
| Markup index output | JSON plus table; CLI `--out` | D1 |
| Cost curve and ranges | JSON plus a generated markdown or notebook report | D2 |
| Size-lens rendering | Marker encoding on the existing `/models` scatter | D3 |

## 5. Non-goals

1. **`params ÷ price` as a headline metric or chart axis** for any population. It rewards buying the most weights per dollar, not the most work done (ASSUMPTION, notes §3.11), and conflicts with the repo's no-composite and provenance rules (notes §4.5).
2. **Inferring a closed model's size from its price, then dividing by price.** Circular (ASSUMPTION, notes §2.4). The "second pass" in the original brief is dropped.
3. **Point estimates of any lab's true cost, margin, or profit.** Ranges only (notes §12 d1). The word "margin" appears only when quoting DeepSeek's self-reported theoretical figure (FACT, notes §3.5, §10.1).
4. **Fitting hardware ownership as a latent parameter.** Not identifiable from price alone; markup and hardware advantage are confounded (notes §12 d2 ii).
5. **Active size-extraction attacks** (logit-bias, softmax-bottleneck, timing side channels) against any provider (methods in notes §2.3). This PRD only republishes third-party published bands.
6. **Any composite score.** Extends the existing no-composite rule (ADR 0004 item 5; `CONTEXT.md`).
7. **Live model calls, `/chat/completions`, `/analytics`, scraping, Mode B, new packages, new secrets in the repo, paid campaigns** (ADR 0002, including its "adding a package is a STOP" rule; `CONTEXT.md` Mode A/Mode B; `AGENTS.md` hard invariants).
8. **Replacing or re-scoring the Solo, Multiplayer or Agent Cabinet boards.** D3 annotates an existing chart; nothing from D1 or D2 joins a measured cabinet score (notes §4.3 PR #70 rule; ADR 0004 item 7).
9. **Current price quotes.** The notes' prices are cited examples tied to their source date, not current quotes (notes header). This PRD asserts none.
10. **Resolving the hypotheses the notes leave UNKNOWN** (notes §11 a2, c2; §6). They stay at their verdicts (Appendix A).

## 6. Methodology

### 6.1 Metric definitions

| ID | Metric | Definition | Population | What it measures | Source |
|---|---|---|---|---|---|
| M0 | Raw ratio `V` | `V = P / price`, one value per model | Any | Rejected as a capability proxy (§5 item 1) | notes §3 |
| M1 | **Provider markup index** | For open-weight model `m` with disclosed `active_params_b(m)` and provider endpoint `e`: `markup_index(m, e, profile) = blended_price(e, profile) [$ per 1M tokens] ÷ active_params_b(m)` | Open weights, `params_tier = disclosed`, per provider endpoint | Provider markup and serving efficiency for the same weights. Not capability. | ASSUMPTION, notes §3 item 5, §5 #2 |
| M2 | **Cost curve** | Fit `log(blended_price(profile))` against `log(active_params_b)` and a hardware-class covariate, on open-weight models served by competitive third-party hosts. Report fit statistics and the calibration table. | Open weights only | The competitive rental cost of serving a given active size on a given hardware class | ASSUMPTION, notes §9 step 1. Calibration justification: Gundlach et al. assume open models are "not priced at a significant markup relative to the necessary GPU resources"; Epoch reports direct rented-hardware costs within 30% of API prices for 5 open models (FACT, notes §9) |
| M3 | **Hardware-hour anchors** | Dollar per accelerator-hour derived from disclosed deals. Deal figures are FACT; the per-hour arithmetic is ASSUMPTION and stored in a separate field. | Labs with disclosed rental or lease terms | A renter-price anchor for the cost curve | notes §9 step 2, §10.1. The notes' two anchors: DeepSeek's $87,072 one-day GPU rental for an average of 226.75 H800 nodes (FACT); Anthropic→xAI $1.25B/month for roughly 300 MW and over 220k GPUs (FACT), illustratively ≈ $5.7K per GPU-month ≈ $7.8 per GPU-hour (ASSUMPTION, with the notes' caveats) |
| M4 | **Implied cost range** | For closed model `m` of lab `L`: evaluate M2 at `[band_low, band_high]` from an **external** size band, over the hardware classes in `L`'s stratum. `implied_cost(m) = [low, high]`. | Closed models with an external band | What the calibrated competitive curve says serving `m` would cost | ASSUMPTION, notes §9 step 3, §12 d1 |
| M5 | **Unexplained gap** | `unexplained_gap(m) = api_price(m, price_basis) − implied_cost(m)`, as an interval. Sign and expected direction annotated from the §10.2 table. | Same as M4 | Markup ± hardware advantage ± subsidy, which this method cannot separate | ASSUMPTION, notes §9 step 3, §12 d2 iii |
| M6 | **Throughput cross-check** | Tokens/s per user constrains size *given* a hardware class. Applied only after hardware is identified. | Any model with published throughput | A consistency check on the size band, not an estimator | ASSUMPTION, notes §9 step 4; bias rows in §10.2 |
| M7 | **Value frontier** | y = cabinet pass rate; x = measured $ per task; Pareto via existing `_pareto_frontier`. Marker = `active_params` for `disclosed`; hollow or banded otherwise. Size never on an axis. | minibench models with cabinet results | Score per dollar with size as a secondary channel | FACT for existing code (notes §4.2); ASSUMPTION for the size channel (notes §3 item 4, §4.4) |
| M8 | **Rank stability** | For any ranked output, the count of profiles under which the top-k order changes: "rank changes under N of K profiles" | Any ranking | How much the ranking is an artifact of the weighting | ASSUMPTION, notes §8.3 |

Which `P`: the default divisor is `active_params`. `total_params` and `count_convention` are stored alongside, because conventions differ between vendors (embeddings in or out, MTP or vision towers in or out) and the MoE total:active ratio alone is about 18× for DeepSeek-V3 (671B/37B) and about 23× for gpt-oss-120b (117B/5.1B) (FACT counts, notes §2.1; ratios are the notes' arithmetic, §3.1). Mapping a *total*-parameter external band (IKP predicts MoE knowledge better from total than active, R² 0.67 vs 0.41, FACT notes §2.3) onto an *active*-parameter cost curve is unresolved; see open decision D8.

Every stored value carries `as_of`, `profile_id` (blend ratio), `price_source`, `cache_assumption`, and `provider` (ASSUMPTION, notes §3 item 6).

### 6.2 Workload profiles

Cost under a profile is `cost = w_cache·p_cache + w_in·p_in + w_out·p_out` with weights summing to 1, or measured tokens per task times prices (notes §8.3).

| Profile id | Formula | Origin | Who it favours (ASSUMPTION, notes §8.3) | Role in this PRD |
|---|---|---|---|---|
| `agentic-measured` | Σ tokens_type × price_type from actual runs | AA and minibench cost per task already work this way (FACT, notes §8.3) | Reflects verbosity and reasoning | **Default headline** where measured tokens exist (notes §8.3 recommendation) |
| `aa-7:2:1` | `(7p_cache + 2p_in + p_out)/10` | AA methodology (FACT, notes §8.2) | Vendors with deep cache discounts | Preset |
| `chat-3:1` | `(3p_in + p_out)/4` | AA legacy; Arena "3:1" (FACT, notes §1.2, §8.3). Whether Arena's 3:1 is input:output is **UNKNOWN** (notes §1.2, §6) | Cheap-input vendors | Preset |
| `output-only` | `p_out` | Kyle's premise | Flat-priced or fast-silicon hosts; penalises 5× vendors | **Stress test only**, never default (notes §8.3) |
| `minibench-1:3` | `(p_in + 3p_out)/4` | Existing `agentbench/board.py::blended_per_million` (FACT, notes §4.2) | Between 3:1 and output-only | PROPOSED additional preset, so the existing Usage Board blend is reproducible |
| `openrouter-15:1` | `(15p_in + p_out)/16` | OpenRouter observed ~6K:400 tokens (FACT, notes §8.2; 15:1 is the notes' arithmetic, ASSUMPTION) | Cheap-input vendors (strongest) | PROPOSED additional preset, as the token-volume reality check |

Rules:
- The profile is a first-class, labelled parameter (notes §8.3). Every output states its `profile_id`.
- Where no measured tokens exist (D1 has no runs), the default profile is open decision D5.
- Rankings are shown with M8 rank stability. The notes' worked flip is the fixture test: Cerebras-launch Qwen3-Coder ($2/$2) vs Qwen3.7 Max ($1.25/$3.75) gives 2.00 vs 1.875 under 3:1, 2.00 vs 1.41 under 15:1, 2.00 vs 3.125 under 1:3, 2.00 vs 3.75 under output-only; the ranking flips with the weighting (ASSUMPTION, arithmetic on dated prices from different dates, illustration only, notes §8.3).
- Why output-only is not the default: token mix is input-heavy (about 15:1 by tokens, ASSUMPTION on FACT, notes §8.2), yet reasoning can be about 95% of output tokens and output about 56% of cost in AA's example payload, whose cost breakdown is **unverified** (notes §8.2). Effort setting alone moves output volume about 3.7× for one model (FACT, notes §8.2). A per-category in:out ratio for agentic tool-call loops is **UNKNOWN** (notes §6, §8.2).

### 6.3 How ranges are produced

PROPOSED procedure, implementing notes §9 and §12 d1:

1. **Calibration set.** Open-weight models with `params_tier = disclosed`, served by competitive third-party hosts. Each row: model, provider, hardware class, prices by token type, `quantization` or `unknown`, `as_of`. No closed-model row is ever in the calibration set.
2. **Fit M2** per hardware class. Report fit statistics and the residual spread of the calibration set. The residual spread is the first component of the range.
3. **Size band.** Take `[band_low, band_high]` from an external source (`ikp`, `epoch`) with URL and `as_of`. Example of the width to expect: IKP reports "GPT-5.5 ~4.7T [1.5T–15.1T]" (FACT, notes §2.3); Epoch says its GPT-4o (~200B) and Claude 3.5 Sonnet (~400B) estimates could be "off by a factor of 2" (FACT, notes §2.3); MEDEC's ~175B for Sonnet contradicts Epoch's ~400B and is described by its authors as unverified (FACT, notes §2.3). Where no external band exists the row is `unknown` and produces no range.
4. **Hardware-class range.** From the lab's ownership stratum (§6.4), the set of hardware classes the lab is known to serve on. Per-token costs of TPU, Trainium, Cerebras or Broadcom silicon are **UNKNOWN** (notes §6), so alternative-silicon strata widen the range rather than shift it.
5. **Interval arithmetic.** `implied_cost = [min, max]` over band endpoints × hardware-class endpoints × calibration residual. Endpoints, not distributions: the inputs are bands with stated tiers, not calibrated distributions (PROPOSED).
6. **Gap.** `unexplained_gap = api_price − implied_cost`, as an interval, with the §10.2 expected bias direction annotated. Never labelled margin or profit.
7. **Throughput check (M6).** If published tokens/s is inconsistent with the band on the identified hardware class, flag the row; do not adjust the band.
8. **Report.** One row per (lab, model, price basis, service tier, profile), stratified by ownership stratum, with every input's tier visible. A point value is never rendered.

The notes are explicit that at 2–3× size error a closed model's ratio can move about 10× end to end (ASSUMPTION, notes §2.4) and that on top of that uncertainty "any 'true cost' point estimate is unsupported" (ASSUMPTION, notes §12). The report's copy must say so.

### 6.4 Per-lab distortion handling

Convention (notes §10.2): estimating size from price under an assumed markup over a GPU-rental cost curve. If true cost is below the curve (owned or cheaper silicon, subsidy) or the markup is smaller than assumed, the estimate **under**-states size. If the lab pays a renter premium or charges a speed or priority premium, it **over**-states size. All entries are ASSUMPTIONs built on the §10.1 FACTs.

| Lab | Ownership / deals (FACT basis, notes §10.1) | Stratum (PROPOSED enum, from notes §12 d2 i) | Price-to-size bias | Throughput-to-size bias | Confidence (notes) |
|---|---|---|---|---|---|
| Google | Owns TPUs and data centres; rents TPUs out | `owned` | **Under** | Moderate | Medium |
| xAI | Owns Colossus; sells surplus to Anthropic | `owned` | **Under** | Low | Medium |
| Anthropic | Rents Trainium, TPU, Nvidia (incl. xAI at ~$1.25B/mo); priority tier closed to new buyers | `mixed` | **Over**; partly offset if Trainium/TPU are cheaper per token than GPUs (UNKNOWN) | Mixed: three silicon types, unknown routing | Low |
| OpenAI | Rents Azure, Oracle, AWS, CoreWeave; Cerebras capacity-as-service; own Broadcom chip from late 2026 | `mixed` | **Over** on standard tiers; strongly **over** on Fast/priority/Ultrafast tiers | **Under** on Cerebras-served models | Low |
| DeepSeek | Rents H800; self-reported theoretical 545% margin | `rented-gpu` | **Over** if a thin margin is assumed | Low | Medium (self-reported) |
| Third-party open-weight hosts | Competitive renters | `rented-gpu` or `rented-alt-silicon` | ≈ calibration baseline; quantization can bias toward **under** | Hardware-dependent (Groq/Cerebras/SambaNova hosts are fast) | Medium-High |

Handling (notes §12 d2 recommendation, ASSUMPTION; pending open decision D2):
- Option (i): treat ownership as a **categorical covariate** (`owned` / `rented-gpu` / `rented-alt-silicon` / `mixed`) and report results stratified by category. Lowest risk.
- Option (iii): publish the residual as an **unexplained price gap** (M5).
- Option (ii), a latent parameter, is avoided unless an independent per-token cost anchor appears, such as a disclosed lease rate × measured throughput.
- Priority, fast and Scale tiers are kept as separate rows because they isolate the speed premium (notes §12 d4; open decision D4). Examples in the notes: OpenAI Scale Tier and `service_tier="priority"`, ChatGPT Pro 500 with "Astra Ultrafast"; Anthropic's Priority Tier "no longer available for purchase" (FACT, notes §10.1).

## 7. Data sources and refresh

| Source | What it supplies | Tier | Access path and constraint | Refresh |
|---|---|---|---|---|
| Open-weight model cards and papers: DeepSeek-V3 README, gpt-oss paper, Grok-1 release, NightVision Appendix C | `total_params`, `active_params`, `count_convention` | FACT (notes §2.1) | Hand-curated ledger with URL and access date (ADR 0004 item 6 pattern: curated ledger, no scraping) | On each new open-weight release; PROPOSED review at least monthly |
| OpenRouter `/models` | Per-token prices (prompt, completion, cache, reasoning), `context_length`, sort by price, throughput, latency, AA index. **No parameter field** | FACT (notes §1.6) | Already allowlisted Mode A GET path, polled daily (ADR 0002; `CONTEXT.md`) | Existing daily poll; fixture when no key |
| OpenRouter `/models/{author}/{slug}/endpoints` | Per-provider price, latency, throughput | FACT that it exists (notes §3.10) | **Not** in the Mode A allowlist. Would need an ADR change; **UNKNOWN** whether permitted (notes §5 #2, §6). Whether it records quantization is **UNKNOWN** (notes §6). See D7 | Only if D7 allows; otherwise a curated endpoint ledger |
| minibench `backend/app/data/known_models_seed.json` | 42 OpenRouter models: `provider, model_id, display_name, family, license, context_length, prompt_price, completion_price, snapshot_date`. No parameter fields. Generated 2026-07-06 | FACT (notes §4.2) | Repo file | Already stale relative to price decline (§9.3); regenerate from the daily poll (PROPOSED) |
| IKP (arXiv 2604.24827) | Banded size estimates for 97 proprietary models; calibrated on 93 open models | FACT for the paper's claims (notes §2.3). Preprint, not independently replicated (ASSUMPTION, notes §2.4). Code license **UNKNOWN**; probe-release statement internally inconsistent (notes §6) | Curated size-band ledger citing the paper; tier `estimated:ikp` | On paper revision; see D9 |
| Epoch AI data and gradient updates | Parameter and compute database with confidence tiers ("Confident" within 3×, "Likely" within 10×, "Speculative" within 30×); size guesses for GPT-4o and Claude 3.5 Sonnet | FACT (notes §1.3, §2.3) | Curated ledger; tier `estimated:epoch`, carrying Epoch's own confidence tier | On Epoch update; see D9 |
| MEDEC (arXiv 2412.19260) | Press-mined sizes, described as unverified | FACT that the paper lists them; values unverified (notes §2.3) | PROPOSED: excluded from ranges; may be shown as `imported` for the disagreement note only | n/a |
| Deal and ownership evidence (notes §10.1 URLs: Cerebras/OpenAI blog, SEC exhibit, Reuters, xAI announcement, TechCrunch S-1 reading, Anthropic TPU/Trainium posts, Google Ironwood, DeepSeek inference overview) | Ownership stratum, lease and rental figures, capacity commitments | Mixed: FACT where first-party; many figures via search summaries or secondary press, S-1 not read directly (notes §6) | Curated deal ledger with `source_kind` per row (ADR 0004 enum) | On new filings or announcements; PROPOSED review monthly |
| AA methodology and Data API docs | 7:2:1 blend definition; example payload token and cost split (cost breakdown **unverified**) | FACT / unverified (notes §8.2) | Profile definitions only; no AA data fetched | On AA methodology change |
| Third-party mirror of AA data (aiagentstore.ai) | Effort-level cost and token spread for one model | Third-party mirror, not AA's own export (notes §3.7, §6) | Not used as a data source; cited only as evidence for the effort-curve risk | n/a |
| OpenRouter / a16z "State of AI" (arXiv 2601.10088) | Token-mix evidence | FACT (notes §8.2) | Profile justification only | n/a |

Refresh and staleness rules:
- The cost of a fixed performance level fell about 47%/quarter, about 13×/yr (FACT, notes §1.3); 5–10×/yr per Gundlach et al. (FACT, notes §1.4). Any price without `as_of` is meaningless; `V` for a model drifts with time and must be timestamped (notes §3.6).
- Every row and every rendered number carries `as_of` (existing repo rule: `CONTEXT.md` as_of; ADR 0004 item 1).
- PROPOSED: a staleness badge when a row's `as_of` is older than 90 days, and exclusion from default rankings when older than 180 days. Kyle sets the thresholds (D11).
- Fixture data is never labelled live (ADR 0003 reader rule).

## 8. Acceptance criteria

Each criterion is numbered and has a check that can be run or inspected. "Fixture" means a committed, `live=false` JSON file.

### Spec-level (this document)

- **AC-1** Every price, parameter count, deal figure, and statistic in this PRD cites `notes §n` in the same sentence or table row. Check: search this file for `$`, `B total`, `×`, `%` and confirm an adjacent `notes §` cite.
- **AC-2** No UNKNOWN or hypothesis from the notes is restated as FACT. Check: Appendix A matches notes §11 verbatim; §1 items 1–3 keep their UNKNOWN markers.
- **AC-3** The research notes file is a verbatim copy. Check: `sha256sum` of `docs/research/llm-compute-cost-research-notes-2026-10-02.md` equals that of the frozen notes supplied on 2026-10-02 (`41783be1da754c0c14ec7174dfeda44e60c55f4ca6e14dd6e1fa8da21edfe575`).

### D1 — Open-Weight Provider Markup Index

- **AC-4** A parameter ledger exists with the fields `model_id`, `total_params_b`, `active_params_b`, `count_convention`, `params_source_url`, `params_tier`, `as_of`; the loader rejects a row missing `params_source_url` or `as_of`. Check: `--check` exits non-zero on a fixture row with the URL removed.
- **AC-5** The ledger's seed rows reproduce the FACT-tier counts in notes §2.1 with their URLs: DeepSeek-V3 671 total / 37 active (HF checkpoint 685 incl. 14B MTP noted in `count_convention`), gpt-oss-120b 116.83 total / 5.13 active, Grok-1 314 total, Qwen3-30B-A3B 30.5 / 3.4. Check: values equal notes §2.1 at the stated precision.
- **AC-6** For each (model, provider endpoint, profile) the index equals blended price ÷ `active_params_b`, and the output row records `provider`, `price_source`, `as_of`, `profile_id`, `cache_assumption`. Check: a hand-computed fixture value matches to four significant figures.
- **AC-7** The index is computed only for `params_tier = disclosed`; an `estimated` or `unknown` row is refused with a named reason. Check: fixture test.
- **AC-8** No UI copy, API field description, or report text describes the index as capability, intelligence, or value. Copy says provider markup or serving efficiency. Check: string test over the methodology copy and field descriptions.
- **AC-9** Each endpoint row carries `quantization` with a value or `unknown`; rows with `unknown` are flagged in the output rather than silently compared. Check: fixture with one `unknown` row produces a flag.
- **AC-10** Endpoint prices come only from an allowlisted documented GET path or from a curated fixture. If `/models/{author}/{slug}/endpoints` has not been allowlisted by an accepted ADR, the client refuses it. Check: `agentbench/tests/test_openrouter_data.py::test_allowlist_is_exactly_the_four_gate1_paths` still passes, and a request for the endpoints path raises `DataAPIError` "not allowlisted".

### D2 — Lab True-Cost Range Report

- **AC-11** The cost curve is fitted on open-weight rows only; the report prints the calibration table (model, provider, hardware class, price, `as_of`) and a goodness-of-fit statistic. Check: no row in the calibration table has `params_tier ≠ disclosed`.
- **AC-12** Every closed-model row uses an external size band with `size_band_method ∈ {ikp, epoch}` and a URL; a closed model without a band is `unknown` and yields no numeric range. Check: fixture closed model with no band renders "no range" and no number.
- **AC-13** No size band is derived from the same lab's API price. Check: `size_band_method` never takes a value of `price-implied`; a test asserts the enum.
- **AC-14** Every true-cost output is a `[low, high]` interval; the output schema has no scalar point-estimate field. Check: JSON schema validation.
- **AC-15** Each lab row carries an ownership stratum from `{owned, rented-gpu, rented-alt-silicon, mixed}`, a bias direction, and a confidence consistent with §6.4; the report is stratified by stratum. Check: fixture rows for Google, xAI, Anthropic, OpenAI, DeepSeek match the §6.4 table.
- **AC-16** The residual is named `unexplained_gap` and is an interval; the strings "margin" and "profit" appear only inside a quotation of DeepSeek's self-reported figure. Check: string test.
- **AC-17** Priority, fast, Scale and similar tiers are separate rows with `service_tier` set and are never averaged into a standard-tier row. Check: fixture with a standard and a priority row for one model yields two output rows.
- **AC-18** The deal ledger stores the FACT deal figure and any derived per-hour value in separate, separately labelled fields. Check: the Anthropic→xAI row has `deal_value = $1.25B/month` labelled FACT and `≈ $7.8 per GPU-hour` labelled ASSUMPTION, with the notes' caveats attached.
- **AC-19** Every ranking carries M8 rank stability as "rank changes under N of K profiles". Check: the notes §8.3 worked flip fixture reproduces Qwen3.7 Max cheaper under `chat-3:1` and `openrouter-15:1`, Cerebras-launch Qwen3-Coder cheaper under `minibench-1:3` and `output-only`.
- **AC-20** The report's copy states that point estimates are unsupported and that size bands carry about 2–3× error. Check: the two sentences are present and cite the notes.
- **AC-21** Nothing from D2 joins a Solo, Multiplayer or Agent Cabinet score, and no route returns a field named `composite`, `overall`, or `index_score` computed by minibench. Check: the no-composite guard test from `docs/PLAN-benchmark-lens.md` L2.2 passes.

### D3 — Value Frontier with Size Lens

- **AC-22** `/models` "Capability vs. cost" axes and `_pareto_frontier` output are unchanged; size appears only as marker size or opacity for `disclosed` rows and a hollow marker otherwise. Check: existing Pareto tests pass without modification; a component test asserts marker encoding by tier.
- **AC-23** A workload-profile selector offers at least `agentic-measured`, `aa-7:2:1`, `chat-3:1`, `output-only`; the default is `agentic-measured`; `output-only` is labelled "stress test". Check: helper test on the default and labels.
- **AC-24** Every rendered number shows `as_of`, `price_source`, `profile_id` and a tier badge. Check: component test.
- **AC-25** D3 work does not start until PRs #68 and #69 have landed or been closed. Check: the implementing issue records the dependency and its resolution date.

### Cross-cutting

- **AC-26** No live model calls, no `/chat/completions`, no `/analytics`, no scraping, and no new secrets; the CI-equivalent checks in `AGENTS.md` pass with no `OPENROUTER_API_KEY` set. Check: CI run log shows fixture path only.
- **AC-27** Fixture data is never labelled `live=true`. Check: loader test per ADR 0003.
- **AC-28** Every output artifact (D1 table, D2 ranges, D3 payload) is available as JSON conforming to a committed schema, so an agent can consume it without parsing a chart or prose. Check: schema files exist and the CLI `--out` output validates.
- **AC-29** The methodology page and any README copy state Kyle's hypotheses at exactly the verdicts in notes §11. Check: text match against Appendix A.

**Total: 29 acceptance criteria.**

## 9. Risks

### 9.1 Methodology

| Risk | Evidence | Mitigation in this PRD |
|---|---|---|
| **Circularity.** Estimating size from price then dividing size by price makes the output a function of price plus assumed markup | ASSUMPTION, notes §2.4 | Non-goal §5 item 2; AC-13; size bands must be external (M4) |
| **Size-band width.** 2–3× error moves a closed model's ratio about 10× end to end; IKP 90% PI ≈ 3.2×; Epoch "off by a factor of 2"; NightVision ≈ 53% params error; above 1T IKP has only 2 calibration anchors | FACT/ASSUMPTION, notes §0.3, §2.3, §2.4 | Ranges only (M4, AC-14); report copy (AC-20); `unknown` when no band (AC-12) |
| **Which `P`.** MoE total vs active differ about 18–23× | FACT counts, notes §2.1; §3.1 | `active_params` default with `total_params` and `count_convention` stored (§6.1); D8 |
| **Total-band vs active-curve mismatch.** IKP predicts from total (R² 0.67 vs 0.41) while the cost curve is in active params | FACT, notes §2.3, §2.4 | Unresolved; D8 |
| **One shared cost curve does not exist.** Ownership, alternative silicon, lab-to-lab leases, and priced priority tiers each move a lab off the curve by unknown amounts and in different directions | ASSUMPTION on §10.1 FACTs, notes §10.2, §12 | Strata (§6.4); unexplained gap (M5); no latent fit (§5 item 4); D2 |
| **Alt-silicon per-token cost unknown.** TPU, Trainium, Cerebras, Broadcom | UNKNOWN, notes §6 | Widens the range rather than shifting it (§6.3 step 4) |
| **Quantization.** Providers can serve `P` at lower cost and quality; text tests detect quantization only ~50% of the time; whether endpoint data records it is UNKNOWN | FACT (secondary), notes §3.4; §6 | `quantization` field, flagged when `unknown` (AC-9) |
| **Effort and verbosity.** One model's cost per task spans $0.48 to $2.32 across effort settings, about 5× at the same $/token | FACT via third-party mirror, notes §3.7 | Measured profile as default; effort recorded per row; rank stability (M8) |
| **Blend-ratio artifacts.** Ranking order flips with the weighting | ASSUMPTION, notes §3.9, §8.3 | Profiles first-class; M8; output-only never default |
| **Unreplicated preprints.** IKP and NightVision are 2026 preprints; IKP's own acknowledgements record an external sanity check that forced a scoring revision | ASSUMPTION, notes §2.4 | Tier `estimated:<method>` always visible; D9 |
| **Open-weight calibration assumption.** "Not priced at a significant markup" is an assumption of Gundlach et al.; DeepSeek reported a *theoretical* 545% daily margin on rented H800s | FACT, notes §9, §3.5 | Calibration residual enters the range (§6.3 step 2); DeepSeek stratified as `rented-gpu` |

### 9.2 Legal and reputational risk of publishing cost estimates

| Risk | Evidence | Mitigation |
|---|---|---|
| **Named-lab cost or margin claims.** A range labelled "true cost" for OpenAI or Anthropic is a claim about a private company's economics that no lab discloses | No lab discloses marginal cost (notes §11 c2) | Ranges only; `unexplained_gap` never called margin or profit (AC-16); research framing outside the leaderboard (D6); publication requires explicit owner authorization (`AGENTS.md`); D10 |
| **Secondary and unverified sources.** Deal figures from search summaries and secondary press; the S-1 was not read directly; AA figures partly from a third-party mirror; 2026 model names reproduced as printed and not checked against vendor pages | notes §6, notes header | `source_kind` per row (ADR 0004 enum); no third-party mirror as a data source (§7) |
| **Third-party IP.** IKP code license UNKNOWN; probe-release statement inconsistent | notes §6 | Cite the paper's published bands only; do not vendor code or probes (D9) |
| **OpenRouter terms.** Existing citation and GET-only rules | ADR 0002; `CONTEXT.md` | Unchanged; `/endpoints` only via an accepted ADR (D7, AC-10) |
| **Disputing a lab's hypothesis in public.** For example "Cerebras released a $500 plan" is not supported as stated | FACT, notes §11 a3 | Appendix A keeps the notes' exact verdicts; nothing is upgraded or softened (AC-2, AC-29) |
| **Being read as a leaderboard.** A ranked table of labs by "true cost" would be read as a verdict | ADR 0004 item 4 ("flags, not verdicts") | D2 stratified, interval-only, human-read; D6 |

### 9.3 Data staleness

| Risk | Evidence | Mitigation |
|---|---|---|
| **Prices fall fast.** About 13×/yr at fixed performance; 5–10×/yr per Gundlach et al. | FACT, notes §1.3, §1.4, §3.6 | `as_of` on everything; staleness badge and exclusion thresholds (D11) |
| **The seed catalog is already dated.** `known_models_seed.json` was generated 2026-07-06 | FACT, notes §4.2 | Regenerate from the daily poll (PROPOSED, §7) |
| **The notes' prices are examples, not quotes.** | notes header | Non-goal §5 item 9; fixtures carry the notes' dates |
| **Deals change.** The Anthropic→xAI lease is terminable on 90 days' notice by either side; Anthropic's Priority Tier is closed to new buyers; OpenAI's Broadcom chip arrives from late 2026 | FACT, notes §10.1 | Deal ledger `as_of`; stratum re-review on each filing (§7) |
| **Fixture-only operation.** The Usage Board's scheduled run has used fixtures when no key was configured | `docs/PROJECT-STATUS.md` | `live=false` labelling (AC-27); no fixture presented as current |

## 10. Open decisions for Kyle

Decisions D1–D6 are the notes' §12 list. D7–D12 are raised by this PRD. Where the notes give a recommendation it is shown as an ASSUMPTION; where this PRD proposes a default it is marked PROPOSED.

| # | Decision | Options | Notes' recommendation / PRD default |
|---|---|---|---|
| **D1** | **Present "estimated true cost" as a range?** | Range always; range with a central tendency; point | Notes: yes, always. Show low/high bands combining size band × hardware-class cost range × markup range. Never show a point. Label the tier (ASSUMPTION, notes §12 d1). AC-14 assumes this. |
| **D2** | **Back out hardware ownership as a variable?** | (i) categorical covariate, stratified results; (ii) latent parameter; (iii) leave out, publish the residual as "unexplained price gap" | Notes: (i) plus (iii). Avoid (ii) unless an independent per-token cost anchor appears (ASSUMPTION, notes §12 d2). §6.4 assumes this. |
| **D3** | **Which price is "the" price per lab?** | First-party standard tier; cheapest third-party host; batch | Notes: affects every row of §10.2 (notes §12 d3). PROPOSED default: first-party standard tier as the headline, with cheapest-host and batch as additional rows under `price_basis`. |
| **D4** | **Do priority/fast tiers count as separate data points?** | Separate rows; excluded; merged | Notes: useful because they isolate the speed premium (notes §12 d4). PROPOSED default: separate rows (AC-17). |
| **D5** | **Default workload profile** when measured tokens do not exist (D1) | `agentic-measured` (n/a without runs); `aa-7:2:1`; `chat-3:1`; `output-only` stress test; `minibench-1:3` | Notes: default the headline to measured cost per task; output-only is a stress test, not the default (ASSUMPTION, notes §8.3, §12 d5). PROPOSED fallback where no runs exist: `aa-7:2:1`, with M8 stability always shown. |
| **D6** | **Where does this live?** | (a) all in minibench; (b) D2 in a separate research repo or notebook (for example `RaapTechllc/price-implied-size`) with only cited, tiered outputs republished into minibench via Benchmark Lens or Usage Board; (c) blog post only | Notes: under the reframe this is research rather than a leaderboard, which strengthens the §4.5 verdict for (b) (notes §4.5, §12 d6). This PRD is written so that D1 and D3 fit minibench and D2 can be either. |
| **D7** | **Extend the Mode A allowlist to `/models/{author}/{slug}/endpoints`?** | New ADR allowing one more GET path; curated endpoint ledger only; defer D1 live tracking | Notes: needs an ADR change; UNKNOWN whether permitted (notes §5 #2, §6). PROPOSED default: curated ledger first (AC-10), ADR later if D1 proves useful. |
| **D8** | **Which `P`, and how to map total-parameter external bands onto the active-parameter cost curve?** | Active only (drop total-only bands); carry both and show the band in total with a sensitivity note; attempt a conversion | Notes: store `total_params`, `active_params`, `count_convention` (notes §2.1); IKP predicts better from total (notes §2.3). PROPOSED default: active for the curve; closed-model bands shown as reported with their basis labelled; no conversion. |
| **D9** | **Which external size-band sources are admissible?** | IKP; Epoch; both; MEDEC excluded or `imported` only | Notes: IKP and NightVision unreplicated (notes §2.4); IKP license UNKNOWN (notes §6); MEDEC unverified (notes §2.3). PROPOSED default: IKP and Epoch bands as `estimated:<method>`; MEDEC excluded from ranges. |
| **D10** | **Publication posture for named-lab ranges** | Publish with lab names; publish with strata only and no lab names; internal only until reviewed | PROPOSED default: internal draft first; publication is a separately authorized step (`AGENTS.md`). |
| **D11** | **Refresh cadence and staleness thresholds** | Badge at 90 days / exclude at 180 (PROPOSED); other values; no exclusion | Notes: ~13×/yr price decline makes timestamps essential (notes §1.3, §3.6). |
| **D12** | **Source for the throughput cross-check (M6)** | OpenRouter `/models` throughput sort (allowlisted, notes §1.6); none; defer | PROPOSED default: allowlisted catalog throughput only; no measurement runs. |

**Total: 12 open decisions** (6 from notes §12, 6 raised by this PRD).

## 11. GO gate

**No build until Kyle accepts this PRD.**

Acceptance means all of the following, recorded in this file:

1. The Status line at the top changes from `PROPOSED` to `ACCEPTED` with a date and Kyle's name.
2. Decisions D1, D2, D3, D5 and D6 have a recorded choice. The remaining decisions may fall to their PROPOSED defaults if Kyle writes "default" against them.
3. If D6 chooses a separate research repo or notebook for D2, the minibench scope reduces to D1 and D3 plus a republishing path, and that is written into §4.

Until the gate clears:

- No product code, schema change, fixture, ledger, ADR status flip, or frontend change is made for this PRD.
- Open PRs #68, #69 and #70 are not touched.
- The research notes stay frozen; corrections go in a new dated notes file, not edits to the frozen one.

After the gate clears, the next artifacts are a handoff plan in the shape of `docs/PLAN-benchmark-lens.md` and, if D7 is answered yes, a new ADR for the allowlist change. Paid live model calls, publishing, deployment and external communication remain separately authorized under `AGENTS.md` regardless of this gate.

---

## Appendix A. Kyle's hypotheses: verdicts (reproduced exactly from notes §11)

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| a1 | OpenAI uses Cerebras | **FACT** | 750 MW deal; Codex-Spark on Cerebras (§10.1) |
| a2 | …but keeps most of that capacity for itself | **UNKNOWN / partially supported** | Only public signal: Codex-Spark is Pro-only, API limited to "select design partners". No disclosure of capacity split. The deal is Cerebras-hosted capacity for "OpenAI customers" (Cerebras blog) |
| a3 | Cerebras just released a $500 plan | **Not supported as stated** | The $500/month plan is **OpenAI's ChatGPT Pro 500** (DevDay 2026-09-29, "Astra Ultrafast"). Pre-launch leaks tied it to Cerebras, but OpenAI pages do not name the hardware (Business Insider; https://pasqualepillitteri.it/en/news/19330/openai-launches-pro-500-500-dollars-month, accessed 2026-10-02). Cerebras Code plans are $50 and $200, shown as sold out — https://www.cerebras.ai/code, https://support.cerebras.net/articles/9996007307-cerebras-code-faq (accessed 2026-10-02). Ultrafast on Cerebras: **UNKNOWN** |
| b1 | xAI owns its own data centres | **FACT** | Colossus 1, "built from the ground up" (xAI), Memphis |
| b2 | xAI sells compute to others, e.g. Anthropic | **FACT** | xAI 2026-05-06 announcement; S-1 terms $1.25B/month to May 2029 (TechCrunch) |
| c1 | Owned or reserved silicon and priority deals mean API price ≠ lab cost | **Supported in direction** | Priority/Scale tiers price capacity, not size; DeepSeek theoretical margin; xAI monetising "unused" capacity. Magnitude per lab **UNKNOWN** |
| c2 | Owners price near marginal cost; renters carry a premium | **ASSUMPTION (plausible, unproven)** | No lab discloses marginal cost. Gundlach et al. attribute part of the closed-vs-open price gap to competition and markup, not ownership. Owners may also price *above* cost to recover capex |

Section references inside this table (§10.1) point into the notes, not this PRD.

## Appendix B. Repo fit map

Where each piece would live if D6 keeps it in minibench. All rows are ASSUMPTION or PROPOSED design sketches, not changes.

| Piece | Location | Basis |
|---|---|---|
| Parameter fields on the catalog | Extend `KnownModel` and `backend/app/data/known_models_seed.json` with `total_params_b`, `active_params_b`, `params_source_url`, `params_tier`, `params_band_low/high`; not the legacy `/api/v1/models` quality table that PR #69 removes | notes §4.3, §4.4 |
| D1 compare route | Usage Board, "best-by-$-per-active-param", open weights only | notes §4.4 Surface B |
| D3 size channel | `frontend/src/pages/Models.tsx` "Capability vs. cost" marker encoding; `_pareto_frontier` unchanged | notes §4.2, §4.4 Surface A |
| Closed-model size bands | Benchmark Lens (ADR 0004, proposed, not implemented) as `estimated:<method>` rows with provenance tier | notes §4.4 Surface C; ADR 0004 items 1–2, 6 |
| Ledgers and loaders | `agentbench/data/*.json` with a runtime override path following the ADR 0003 pattern; pure-function loaders in `agentbench/` | `docs/PLAN-benchmark-lens.md` concept map |
| Glossary | `CONTEXT.md` gains: Workload profile, Provider markup index, Size tier (`disclosed` / `estimated:<method>` / `unknown`), Ownership stratum, Unexplained gap | `docs/agents/domain.md` |
| Sequencing | After #68 and #69 land or close | notes §4.4 |

ADR interactions flagged per `docs/agents/domain.md`: this PRD does not change ADR 0002, 0003 or 0004. D7 would require a new ADR because ADR 0002 fixes the Mode A path allowlist and ADR 0004 item 6 says any automated fetch from a new host or path is a separate ADR.
