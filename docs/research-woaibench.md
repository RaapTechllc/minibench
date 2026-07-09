# WOAI Bench Research Notes

**Source:** https://www.woaibench.ai/docs  
**Researched:** 2026-07-09  
**Purpose:** Competitive / inspiration research for Minibench

**Method note:** The docs site is a client-rendered SPA (`/docs` serves a Vite shell; content lives in the JS bundle). Nested paths like `/docs/judge-system/overview` return the same shell without SSR. All 39 documentation articles below were extracted from the official bundle at `https://www.woaibench.ai/assets/index-DILK21tf.js` (same content the docs UI renders). Firecrawl CLI was not available in this environment. Marketing pages (`/`, `/pricing`) were fetched separately; where marketing and docs disagree, **docs win** and the conflict is noted under Gaps.

## Executive summary

- **WoAI Bench** (“World of AI Bench”) is a hosted “vibe coding” benchmark: models generate self-contained HTML/CSS/JS artifacts; outputs are rendered in headless Chromium, screenshotted, and scored by a vision-capable LLM judge on a 0–100 scale across **10 categories** and **5 rubric dimensions** ([What is WoAI Bench?](https://www.woaibench.ai/docs)).
- Differentiator claimed in docs: **screenshot + vision judge** — score what the output *looks like*, not only whether code parses ([What is WoAI Bench?](https://www.woaibench.ai/docs)).
- Judging is the product core: category-weighted rubrics, mandatory penalties, **3 concurrent judge passes with median consensus**, agreement scores, judge ≠ model-under-test, and a capped heuristic fallback ([Judge System Overview](https://www.woaibench.ai/docs), [Multi-Judge Consensus](https://www.woaibench.ai/docs)).
- Results UX is strong: heatmap leaderboard, composite + per-category columns, $/eval and latency, showcase gallery of screenshots, radar analysis with **custom category weights**, run history with pause/resume ([Leaderboard](https://www.woaibench.ai/docs), [Features](https://www.woaibench.ai/docs)).
- Docs IA is a left-nav knowledge base: Introduction → Methodology → **Judge System** → Categories → Leaderboard → Features → Getting Started → API — methodology and judging get first-class sections, not buried footnotes.
- Freemium: free = top-5 / 4 categories + “Can I Run It?”; Pro ($12/mo) = BYOK runs, full board, playground, showcase, analysis, CSV ([Pricing](https://www.woaibench.ai/pricing), [Free Tier](https://www.woaibench.ai/docs)).

## Product overview

### What it is

World of AI Bench evaluates LLMs on practical coding tasks that produce **renderable web artifacts** (dashboards, games, SVG, 3D, agentic UIs, debugging fixes, etc.). Pipeline at a high level ([What is WoAI Bench?](https://www.woaibench.ai/docs)):

1. Dispatch prompts to models in parallel  
2. Render HTML in headless Chromium  
3. Capture PNG screenshot  
4. AI Judge evaluates code + screenshot  
5. Weighted scores aggregate into rankings  

Docs cite **50+ models**, **120+ benchmark prompts**, **10 task categories**, **5 scoring dimensions** ([What is WoAI Bench?](https://www.woaibench.ai/docs)). (Homepage marketing sometimes says “3,900+” / “4,300+ prompts judged” — see Gaps.)

### Who it’s for / positioning

- **Positioning:** “vibe coding” / shippable visual code quality vs classic academic suites (MMLU, HumanEval, MATH) ([What is WoAI Bench?](https://www.woaibench.ai/docs); [Homepage](https://www.woaibench.ai/)).
- **Free users:** public leaderboard slice, hardware compatibility tool, docs ([Getting Started – Free](https://www.woaibench.ai/docs)).
- **Pro users:** BYOK hosted runs, full leaderboard, playground, showcase, analytics, prompt library, history/CSV ([Getting Started – Pro](https://www.woaibench.ai/docs); [Pricing](https://www.woaibench.ai/pricing)).
- **Enterprise (marketing/pricing):** custom rubrics, on-prem/VPC, SSO, volume API ([Pricing](https://www.woaibench.ai/pricing); [Homepage](https://www.woaibench.ai/)).
- **Business model:** Pro subscription + **user-supplied API keys** for model and judge calls; platform does not absorb frontier inference cost ([API Key Setup](https://www.woaibench.ai/docs); [Terms §7](https://www.woaibench.ai/terms)).

### Stack (from Architecture docs)

React SPA (HashRouter) + Node/Express (`runner.js`, `judge.js`, `connectors.js`, `screenshot.js`) + Supabase Auth + local SQLite for runs/results ([Architecture](https://www.woaibench.ai/docs)). Progress via **polling** `GET /api/benchmark/stream-state/:runId` (avoids SSE proxy buffering) ([Key Concepts](https://www.woaibench.ai/docs)).

## Site / docs information architecture

Official docs nav (from bundle `Nc=[...]`, rendered at [https://www.woaibench.ai/docs](https://www.woaibench.ai/docs)):

| Section | Pages |
|---------|--------|
| **Introduction** | What is WoAI Bench?, Key Concepts, Architecture |
| **Methodology** | Prompt Design, Execution Protocol, Scoring System, Anti-Contamination |
| **Judge System** | Overview, Multi-Judge Consensus, Evaluation Criteria, Composite Score, Value Metric |
| **Categories** | Frontend UI, Game Development, 3D Graphics, SVG Art, System Simulation, Agentic Tasks, Reasoning, Debugging, Creative Coding, Price/Quality |
| **Leaderboard** | Overview, Free Tier, Pro Tier, Heatmap Colors |
| **Features** | Run Benchmark, Playground, Showcase, Can I Run It?, Analysis, History, Prompt Library |
| **Getting Started** | Free Users, Pro Users, API Key Setup |
| **API Reference** | Endpoints, Authentication, Model Catalog |

**Why this layout works (for Minibench inspiration):**

1. **Judge System is a top-level section** equal to Methodology — scoring credibility is navigable, not a blog post.
2. **Each category is its own page** with weight profile, task types, score bands, and failure modes — readers learn *what a number means*.
3. **Leaderboard docs explain the UI** (free vs Pro columns, heatmap legend) — product and methodology stay linked.
4. **Features + Getting Started** separate “what exists” from “how I start” — reduces onboarding friction.
5. Single-page docs app with sticky left nav + in-page article body (SPA); sitemap only lists `/docs` as one URL ([sitemap.xml](https://www.woaibench.ai/sitemap.xml)).

Public site map (sitemap): `/`, `/public-leaderboard`, `/docs`, `/pricing`, `/privacy`, `/terms`.

## Benchmarking model

### Task / prompt model

- Atomic unit: **prompt** in `server/data/prompts.json` with `id`, `title`, `category`, `prompt`, `difficulty` (easy/medium/hard), `output_type` (`html`/`svg`/`canvas`/`webgl`), `est_time` ([Prompt Design](https://www.woaibench.ai/docs)).
- Design rules: concrete success criteria; **single-turn only**; **self-contained HTML** (no CDN/build); difficulty mix ~30% / 45% / 25%; avg length 150–400 words; **120+ active prompts** ([Prompt Design](https://www.woaibench.ai/docs)).
- Standardized system instruction: format constraints, vanilla stack unless specified, visual fidelity, Judge success criteria ([Prompt Design](https://www.woaibench.ai/docs)).
- Versioning + rotation; contamination → remove from pool + recalculate history ([Prompt Design](https://www.woaibench.ai/docs); [Anti-Contamination](https://www.woaibench.ai/docs)).

### Categories (10)

| Category | Emphasis (from weight profile) | Notes |
|----------|--------------------------------|-------|
| Frontend UI | Visual 0.30 | Dashboards, forms, landing pages |
| Game Development | Functional 0.35 | Canvas/WebGL/DOM games |
| 3D Graphics | Visual 0.35 | Three.js / WebGL scenes |
| SVG Art | Visual 0.40 | Vector / generative SVG |
| System Simulation | Functional + Completeness 0.30 each | Physics / ecosystems / circuits |
| Agentic Tasks | Functional 0.35 | Multi-step workflows *as web apps* |
| Reasoning | Functional 0.40 | Algorithms as interactive visualizers |
| Debugging | Functional 0.45 | Fix broken provided code |
| Creative Coding | Creativity 0.30 | Open-ended generative art |
| Price/Quality | Derived | `Composite / ($/eval)`, normalized 0–100 — **no own prompts** |

Sources: individual category pages under [Categories](https://www.woaibench.ai/docs); [Price/Quality](https://www.woaibench.ai/docs).

### How runs work

- Run = UUID; lifecycle `created → running → completed | paused | stopped` ([Key Concepts](https://www.woaibench.ai/docs)).
- Worker pool concurrency 1–5; claim `(prompt, model)` pairs; dual timeouts (absolute + stall); classified retries with jitter; pause/resume via `completedPairs` set ([Execution Protocol](https://www.woaibench.ai/docs)).
- Per-task phases: stream → Puppeteer screenshot → judge → persist ([Execution Protocol](https://www.woaibench.ai/docs); [Scoring System](https://www.woaibench.ai/docs)).
- Standardized params: temperature default 0.7, single-turn, category system prompt ([Execution Protocol](https://www.woaibench.ai/docs)).
- “Slow providers” get 15m timeouts ([Model Catalog](https://www.woaibench.ai/docs)).

### Metrics

| Metric | Definition |
|--------|------------|
| Dimension scores | 1–10 × 5 dimensions |
| Prompt `overall_score` | Weighted avg × 10 → 0–100 int |
| Category score | Mean of prompt scores in category |
| Composite | Unweighted mean of category scores |
| Latency | Wall-clock request→complete ms |
| $/eval | Mean model API cost per prompt (**excludes** judge cost) |
| Price/Quality | Composite / ($/eval), normalized |
| Agreement | Consensus reliability 0–1 |
| `score_source` | `judge` / `consensus` / `heuristic_fallback` |

([Scoring System](https://www.woaibench.ai/docs); [Composite Score](https://www.woaibench.ai/docs); [Value Metric](https://www.woaibench.ai/docs); [Multi-Judge Consensus](https://www.woaibench.ai/docs)).

## Judging systems (HIGH PRIORITY)

### Role of the Judge

The Judge is the **primary scorer** for all leaderboard-quality results. Implementation referenced as `services/judge.js`, rubric version `1.0` ([Judge System Overview](https://www.woaibench.ai/docs)).

**Hard rule:** Judge model is **never** one of the models under evaluation (anti self-preference bias) ([Judge System Overview](https://www.woaibench.ai/docs)).

### Judge model cascade

1. User override from `JUDGE_REGISTRY` (if key present)  
2. Default: **Gemini 3 Flash** (`gemini-3-flash-preview`) — cost/speed/human-correlation rationale  
3. Fallback: **Claude Sonnet 4.6**  
4. Last resort: **GPT-4.1**  
5. No key → Judge returns `null` → **heuristic fallback capped at 40/100**

([Judge System Overview](https://www.woaibench.ai/docs); [API Key Setup](https://www.woaibench.ai/docs)).

### Inputs / outputs

**Inputs:** original prompt (with category prefix); model output (HTML truncated at 60k chars); optional base64 PNG screenshot. Without screenshot, visual scores are instructed to be **conservative** ([Judge System Overview](https://www.woaibench.ai/docs)).

**Output JSON shape** ([Judge System Overview](https://www.woaibench.ai/docs)):

```json
{
  "functional_correctness": { "score": 7, "reasoning": "..." },
  "visual_quality":         { "score": 8, "reasoning": "..." },
  "completeness":           { "score": 6, "reasoning": "..." },
  "code_quality":           { "score": 7, "reasoning": "..." },
  "creativity":             { "score": 5, "reasoning": "..." },
  "summary": "One paragraph overall assessment",
  "critical_issues": ["..."],
  "standout_features": ["..."]
}
```

Normalization: category weights → weighted average (1–10) → `Math.round(weighted * 10)` → 0–100 ([Judge System Overview](https://www.woaibench.ai/docs)).

### Five dimensions + banded rubrics

Each dimension has explicit 1–10 band descriptions (not free-form “rate 1–10”) ([Evaluation Criteria](https://www.woaibench.ai/docs)):

1. **Functional Correctness** — does it work end-to-end?  
2. **Visual Quality** — would a designer approve?  
3. **Completeness** — % of stated requirements  
4. **Code Quality** — structure / maintainability  
5. **Creativity and Polish** — beyond bare minimum  

**Bell-curve guidance:** most outputs should land 4–7; 8+ reserved for production / world-class ([Judge System Overview](https://www.woaibench.ai/docs); [Scoring System](https://www.woaibench.ai/docs) grade table 85–100 = rare Excellent).

### Category weight profiles

Weights sum to 1.0 per category ([Evaluation Criteria](https://www.woaibench.ai/docs)):

| Category | Func | Visual | Complete | Code | Creativity |
|----------|------|--------|----------|------|------------|
| Frontend UI | 0.20 | 0.30 | 0.20 | 0.15 | 0.15 |
| Game Dev | 0.35 | 0.15 | 0.25 | 0.10 | 0.15 |
| 3D Graphics | 0.20 | 0.35 | 0.15 | 0.10 | 0.20 |
| SVG Art | 0.15 | 0.40 | 0.15 | 0.10 | 0.20 |
| System Sim | 0.30 | 0.15 | 0.30 | 0.15 | 0.10 |
| Agentic | 0.35 | 0.10 | 0.30 | 0.15 | 0.10 |
| Reasoning | 0.40 | 0.05 | 0.35 | 0.15 | 0.05 |
| Creative | 0.15 | 0.30 | 0.15 | 0.10 | 0.30 |
| Debugging | 0.45 | 0.05 | 0.30 | 0.15 | 0.05 |
| Default | 0.25 | 0.20 | 0.25 | 0.15 | 0.15 |

### Mandatory penalties (applied before dimensional scoring)

| Condition | Penalty |
|-----------|---------|
| Console errors / runtime crashes | −3 Functional |
| Default browser styling (no custom CSS) | −2 Visual |
| >30% requirements missing | −2 Completeness |
| No error handling / validation | −1 Code Quality |
| Placeholder / TODO content | −1 Completeness |

([Evaluation Criteria](https://www.woaibench.ai/docs)).

### Multi-judge consensus (reliability)

For each `(prompt, model)` ([Multi-Judge Consensus](https://www.woaibench.ai/docs)):

1. Call judge **3× concurrently** (configurable `judge_passes`; budget mode = 1).  
2. Per dimension: take **median** score.  
3. Reasoning text from the pass closest to the median.  
4. **Agreement** = `1 - (stdev / 25)`; labels HIGH ≥0.90, MODERATE 0.70–0.89, LOW &lt;0.70.  
5. Shown on leaderboard as `avg_agreement`; stored per result.  

Docs claim single-pass variance ~±15 pts → median-of-3 ~±3 pts. Median preferred over mean for outlier robustness. Cost: ~3× judge tokens; cited as ~$0.003–0.01/eval on Gemini Flash. Single-pass tagged `score_source: "judge"` vs `"consensus"` ([Multi-Judge Consensus](https://www.woaibench.ai/docs)).

**Not documented as:** multi-*model* judge panel, pairwise preference battles, or human review in the scoring path. Homepage marketing says “multi-agent scoring that matches human consensus” and “3 disagreements flagged for human review” in a terminal demo — **not corroborated** in Judge System docs (see Gaps).

### Three-phase scoring pipeline

1. **Heuristic** (always): regex/keyword presence; **hard cap 40**; `score_source: heuristic_fallback`  
2. **Screenshot** (if Puppeteer + judge enabled)  
3. **AI Judge** (primary): if fails → fall back to heuristic  

([Scoring System](https://www.woaibench.ai/docs)).

### Aggregation & ranking

- Category = mean of prompt scores; Composite = **equal-weight** mean of categories (anti-gaming specialization) ([Composite Score](https://www.woaibench.ai/docs)).  
- Tiebreak: (1) # categories &gt;80, (2) lower category variance, (3) faster latency ([Composite Score](https://www.woaibench.ai/docs)).  
- Interpretation bands: 85+ autonomous-ready; 70–84 supervised; 55–69 simple only; &lt;55 not recommended ([Composite Score](https://www.woaibench.ai/docs)).  
- Contamination: flagged prompts excluded; historical composites recalculated ([Anti-Contamination](https://www.woaibench.ai/docs); [Composite Score](https://www.woaibench.ai/docs)).

### Bias mitigation (as documented)

| Mechanism | Purpose |
|-----------|---------|
| Judge ≠ evaluated models | Self-preference |
| Identical system prompt + rubric | Consistency |
| Bell-curve / rare 8+ language | Score inflation |
| Mandatory penalties | Floor for broken/unstyled output |
| Median of 3 passes | LLM sampling noise |
| Agreement score | Surface unreliable cells |
| No-screenshot → conservative visual | Avoid hallucinated polish |
| Heuristic capped at 40 | Don’t let keyword scorer inflate ranks |
| Unique constraints / rotation / n-gram + embedding checks | Contamination / memorization |
| Near-identical multi-model outputs → flag | Memorized recall detection |

([Judge Overview](https://www.woaibench.ai/docs); [Consensus](https://www.woaibench.ai/docs); [Anti-Contamination](https://www.woaibench.ai/docs)).

### Known limitations (first-party)

- Vision model bounds: subtle regressions, animation smoothness, micro-interactions may be missed.  
- Unconventional-but-correct solutions may be underscored.  
- Judge **cannot execute or interact** — static screenshot + code review only.  

([Judge System Overview](https://www.woaibench.ai/docs)).

### Anti-contamination (prompt integrity)

Prevention: original prompts, unique constraints, randomized parameters, rolling rotation. Detection: n-gram vs public corpora, embedding similarity, multi-model near-identical output analysis. Remediation: remove, recalculate history, tag `contaminated`, recompute leaderboard; Pro prompt library shows flags ([Anti-Contamination](https://www.woaibench.ai/docs); [Prompt Library](https://www.woaibench.ai/docs)).

## Leaderboards & results presentation

### Ranking & views

- Sort by composite descending; ties as above ([Leaderboard Overview](https://www.woaibench.ai/docs)).  
- Views: **Table** (all); **Cards** (Pro) with mini radar ([Leaderboard Overview](https://www.woaibench.ai/docs)).  
- Tabs: Overall Rankings; Category Breakdown (Pro) ([Leaderboard Overview](https://www.woaibench.ai/docs)).  

### Free vs Pro columns

| | Free | Pro |
|---|------|-----|
| Models | Top 5; rest blurred + CTA | All 50+ |
| Categories | Frontend, Game, 3D, SVG | All 10+ |
| Speed / Cost | Hidden | Visible |
| Sort / CSV / model detail | Disabled | Enabled |
| Judge metadata | — | Judge model, confidence, rubric version |

([Free Tier](https://www.woaibench.ai/docs); [Pro Tier](https://www.woaibench.ai/docs)).

### Heatmap

Continuous color scale on category cells + composite bar (dual encoding color + width); text always overlaid for a11y ([Heatmap Colors](https://www.woaibench.ai/docs)):

| Score | Approx color |
|-------|----------------|
| 85–100 | Deep green `#2d8a4e` |
| 75–84 | Light green `#5cb85c` |
| 65–74 | Yellow-green `#8cc152` |
| 55–64 | Yellow `#f0ad4e` |
| 45–54 | Orange `#e67e22` |
| 0–44 | Red `#d9534f` |

### Analysis / Showcase / History

- **Analysis:** radar overlays, histograms, per-category rankings, trends, **custom category weight sliders** for personal composite ([Analysis](https://www.woaibench.ai/docs)).  
- **Showcase:** screenshot grid; filter by model/category/score/run; side-by-side same-prompt comparison; code + render ([Showcase](https://www.woaibench.ai/docs)).  
- **History:** run metadata, resume/re-run/delete/filter/CSV; score_source visible ([History](https://www.woaibench.ai/docs)).  
- **Model detail (Pro):** radar, per-prompt results, history, sample screenshots, cost/latency ([Pro Tier](https://www.woaibench.ai/docs)).  

Homepage also markets filters by price / open-weight and “every cell links to exact test cases” ([Homepage](https://www.woaibench.ai/)) — drill-down is consistent with Pro model detail + showcase docs.

## Developer / API surface

Documented REST API ([API Endpoints](https://www.woaibench.ai/docs); [Authentication](https://www.woaibench.ai/docs)):

| Endpoint | Purpose | Auth / tier |
|----------|---------|-------------|
| `POST /api/benchmark/start` | Start run (`models`, `promptIds`, `concurrency`, `enableJudge`, `name`) → `{ runId }` | JWT, Pro |
| `GET /api/benchmark/stream-state/:runId` | Live progress poll | JWT |
| `POST /api/benchmark/stop\|pause\|resume/:runId` | Control run | JWT |
| `GET /api/leaderboard` | Leaderboard (tier-gated fields) | Optional |
| `GET /api/category-scores` | Category breakdowns | JWT, Pro |
| `GET /api/models` | Model catalog | Optional |
| `GET /api/benchmark/runs` | User run list | JWT, Pro |
| `GET /api/benchmark/results/:runId` | Per-prompt results | JWT |

Auth: Supabase JWT (`Authorization: Bearer`); Google / GitHub / email; 401 vs 403 for missing auth vs free-on-Pro ([Authentication](https://www.woaibench.ai/docs)).

**Not documented:** public webhooks, published SDKs, OpenAPI/Swagger UI, or anonymous submit API. Enterprise “Volume API access” is pricing copy only ([Pricing](https://www.woaibench.ai/pricing)).

Connectors normalize 10+ providers including **Ollama** into `{ response, inputTokens, outputTokens, cost }` ([Architecture](https://www.woaibench.ai/docs); [Model Catalog](https://www.woaibench.ai/docs)).

## Notable UX / IA patterns worth copying

1. **Docs mirror product mental model:** Methodology → Judge → Categories → Leaderboard → Features — same order a skeptical user needs to trust a number.  
2. **Category pages as “score literacy”:** weight table + 85+ / 55–70 / &lt;40 bands + common failure modes.  
3. **Heatmap + composite bar:** glanceable matrix without opening charts.  
4. **Agreement / score_source as first-class UI fields:** reliability is visible, not hidden in logs.  
5. **Showcase as visual leaderboard companion:** screenshots make vibe-coding scores auditable.  
6. **Live run UX:** phase indicator (streaming / screenshot / judging), cost accumulator, retry countdown ([Run Benchmark](https://www.woaibench.ai/docs)).  
7. **Pause/resume** as cost-saving control, not just Stop ([Execution Protocol](https://www.woaibench.ai/docs)).  
8. **Custom weight analysis:** official composite stays equal-weight; users reweight for their use case ([Analysis](https://www.woaibench.ai/docs)).  
9. **Can I Run It?** free tool adjacent to rankings — bridges local hardware reality ([Can I Run It?](https://www.woaibench.ai/docs)).  
10. **Freemium blur rows + locked Category Breakdown** — clear upgrade path without empty free experience ([Free Tier](https://www.woaibench.ai/docs)).  
11. **Prompt library contamination badges + version tags** — transparency for eval hygiene ([Prompt Library](https://www.woaibench.ai/docs)).  
12. **Value metric color bands** (&lt;$0.05 / $0.05–0.20 / &gt;$0.20) next to quality ([Value Metric](https://www.woaibench.ai/docs)).

## Inspiration for Minibench (actionable)

Context: Minibench is local-first / self-hosted (FastAPI + Postgres, Vite UI, `minibench` CLI + Ollama, `agentbench` MoA runs, coding tasks, trials, dry-run, publish). Pivot plan favors **executable oracles** and cost-bounded suites (`docs/PIVOT-PLAN.md`, `agentbench` grading) — WoAI is the opposite extreme (LLM-as-judge + visual). Steal **structure and UX**, not a wholesale judge-only philosophy.

| # | What WoAI does | Why it matters | Suggested Minibench adaptation |
|---|----------------|----------------|--------------------------------|
| 1 | Top-level **Judge System** docs with rubric, consensus, weights | Users distrust opaque scores | Add `docs/` (or in-app Help) section: **Grading System** — list each grader (`unit_test`, `numeric_match`, `json_fields`, …), pass/fail semantics, Wilson CI / pass^k, what is *not* graded. Mirror WoAI’s nav depth even if graders are deterministic. |
| 2 | **5 dimensions + category weight matrix** | One number hides tradeoffs | For agent/coding runs that *do* use LLM judge (optional future), store dimension JSON + category weights in Postgres; for executable suites, expose **axis scores** (capability vs format, calibration Brier, robustness) as separate columns like WoAI dimensions. |
| 3 | **Median of 3 judge passes + agreement** | LLM noise destroys credibility | If/when Minibench adds LLM-as-judge for open-ended coding: default `judge_passes=3`, median, persist `agreement`; tag `score_source`. For executable graders, keep **≥3 trials** (already planned) and surface trial disagreement analogously. |
| 4 | Judge ≠ model under test + cascade | Self-preference / availability | Config: `judge.model` pinned separately from proposers in MoA YAML; refuse publish if judge id ∈ evaluated set; document fallback chain (OpenRouter model → local Ollama judge → heuristic). |
| 5 | **Mandatory penalties** + bell-curve rubric language | Caps inflation | Encode hard fails in graders (canary leak, infra_error excluded — already); for any rubric judge, ship YAML penalties (e.g. empty output → 0 functional). Publish rubric version string on every `agent_runs` row (WoAI `rubric version: 1.0`). |
| 6 | Screenshot + vision for visual tasks | Coding quality ≠ AST pass | Optional **render harness** for HTML/SVG tasks in agentbench: Playwright/Chromium screenshot artifact stored with trial; keep primary grade executable, attach screenshot for human/LLM secondary review — Showcase-style UI on results page. |
| 7 | Heatmap leaderboard + composite bar | Scanability | Frontend model/agent leaderboard: category columns with green→red cells + composite bar; reuse Recharts already in stack. |
| 8 | **Equal-weight composite** + user **custom weights** in Analysis | Fair public rank vs personal priority | Public board: equal category mean. Analysis page: sliders to reweight coding / reasoning / tools / calibration for “my stack” composite (client-side recompute from stored category means). |
| 9 | `$/eval` + Price/Quality ratio | Local + API cost decisions | Extend publish payload: mean `$/task` from OpenRouter `usage.cost` (agentbench already tracks cost); column + scatter “score vs $/eval”; for Ollama runs show **tokens/sec** and **$/hour-of-rig** from hardware profiles instead. |
| 10 | `score_source` + agreement on board | Prevent silent bad data | Never mix dry-run, heuristic, and live grades without badges; refuse or asterisk publish when `score_source != consensus|grader_v3`. |
| 11 | Pause/resume + concurrency + retry taxonomy | Long MoA runs are expensive | CLI/API: checkpoint completed `(task, trial)` pairs; resume skips done; classify 429/5xx/timeout like WoAI table (agentbench already retries — document + UI the classes). |
| 12 | Showcase side-by-side same prompt | Model comparison UX | Results UI: pick task id → grid of model outputs (code + optional screenshot) sorted by score. |
| 13 | Prompt schema: difficulty, output_type, version, contamination | Suite hygiene | Extend `tasks/*.json` metadata; UI Prompt Library filters; canary + contamination asterisk already in agentbench — surface in library like WoAI flags. |
| 14 | Category pages with failure modes | Author better tasks | For each minibench category, short doc: what pass means, common model failure modes (format pedantry vs capability — aligns with grader_version 3 dual metrics). |
| 15 | “Can I Run It?” | Minibench’s original hardware story | Keep/promote hardware compatibility next to capability leaderboard — WoAI treats it as free adjacent tool; Minibench can own this better (curated bandwidth table already exists). |
| 16 | Docs IA: Methodology before Features | Trust before CTA | Restructure Minibench docs: Overview → Methodology/Grading → Suites → Leaderboards → CLI/API → Getting Started. |
| 17 | Live phase indicator during run | Operator confidence | Frontend run view: phases `generate → grade → aggregate` with cost accumulator (agentbench tracker). |
| 18 | BYOK + local keys story | Self-hosted ethos | Prefer server-side encrypted keys or env (note WoAI docs vs privacy conflict); Minibench: `.env` / OpenRouter prepaid as today — document clearly. |

**Explicit non-goals to copy blindly:** replacing executable oracles with vision-LLM judging for core public suites (conflicts with Minibench cost ceiling and rigor guardrails); freemium blur paywall (Minibench is self-hosted); HashRouter SPA docs-only (prefer linkable markdown routes).

## Gaps / unknowns

- **Marketing vs docs prompt counts:** Homepage / pricing claim “3,900+” or “4,300+ prompts judged”; official docs consistently say **120+ active prompts**. Treat 120+ as the library size; larger figures may mean cumulative judgments.  
- **Homepage category list ≠ docs categories:** Marketing lists Data Viz, Animation, Full-Stack, Code Golf, etc.; docs list Frontend, Games, 3D, SVG, System Sim, Agentic, Reasoning, Debugging, Creative, Price/Quality. Prefer docs.  
- **Human review / pairwise / multi-model judges:** Terminal demo and “multi-agent” marketing imply human disagreement review and multi-agent panels; **Judge System docs describe one judge model × 3 passes**, not humans or multi-model ensembles.  
- **API key storage contradiction:** [API Key Setup](https://www.woaibench.ai/docs) says encrypted SQLite on server; [Privacy Policy](https://www.woaibench.ai/privacy) and [Terms §7](https://www.woaibench.ai/terms) say keys in **browser localStorage only**. Unresolved from primary sources.  
- **Architecture diagram inconsistency:** Architecture prose says Supabase + SQLite; an embedded flow also mentions “SQLite: Local Database” vs earlier “Supabase-managed PostgreSQL” wording — exact production DB topology unclear.  
- **No public OpenAPI / SDK / webhooks** beyond the endpoint list in docs.  
- **Enterprise custom rubrics / on-prem:** pricing claims only; no technical docs fetched.  
- **Public leaderboard page** gated behind signup modal when fetched anonymously ([/public-leaderboard](https://www.woaibench.ai/public-leaderboard)) — live cell values not independently verified beyond homepage marketing table.  
- **Firecrawl unavailable** — crawl used WebFetch + official JS bundle extraction; nested `/docs/...` URLs do not SSR article HTML.  
- **Correlation with human raters:** claimed for Gemini Flash default; no published study/link in docs.  
- **ELO / arena:** homepage meta description mentions “ELO battles”; Pro pricing mentions “head-to-head arena”; **not detailed in docs articles extracted**.

## Source index

| URL | Description |
|-----|-------------|
| https://www.woaibench.ai/docs | Docs SPA entry; Introduction “What is WoAI Bench?” and full nav |
| https://www.woaibench.ai/assets/index-DILK21tf.js | Official frontend bundle containing all 39 docs article bodies |
| https://www.woaibench.ai/ | Marketing homepage: positioning, sample leaderboard, pricing teaser, categories |
| https://www.woaibench.ai/pricing | Free / Pro $12 / Enterprise feature comparison |
| https://www.woaibench.ai/public-leaderboard | Public leaderboard route (auth gate when fetched) |
| https://www.woaibench.ai/privacy | Privacy policy (API keys, Supabase, Stripe, retention) |
| https://www.woaibench.ai/terms | Terms (tiers, BYOK liability, IP on prompts/scoring) |
| https://www.woaibench.ai/robots.txt | Disallows `/api/`, `/benchmark`, `/dashboard`, etc. |
| https://www.woaibench.ai/sitemap.xml | Public URL list (home, leaderboard, docs, pricing, legal) |

### Docs articles extracted from official bundle (content of `/docs`)

| Article id | Title |
|------------|-------|
| what-is-woai | What is WoAI Bench? |
| key-concepts | Key Concepts |
| architecture | Architecture |
| prompt-design | Prompt Design |
| execution-protocol | Execution Protocol |
| scoring-system | Scoring System |
| anti-contamination | Anti-Contamination |
| judge-overview | Judge System Overview |
| judge-consensus | Multi-Judge Consensus |
| evaluation-criteria | Evaluation Criteria |
| composite-score | Composite Score |
| value-metric | Value Metric |
| cat-frontend … cat-price | 10 category pages |
| lb-overview / lb-free-tier / lb-pro-tier / lb-heatmap | Leaderboard docs |
| feat-benchmark … feat-prompts | 7 feature pages |
| gs-free / gs-pro / gs-api-keys | Getting Started |
| api-endpoints / api-auth / api-models | API Reference |

**Pages fetched (HTTP):** 8 distinct site URLs (home, docs, pricing, public-leaderboard, privacy, terms, robots, sitemap) + 1 JS asset containing 39 docs articles. **Nested `/docs/...` paths** return SPA shell only (no article SSR) — noted, not counted as separate content sources.
