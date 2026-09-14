# Research: agentic benchmark selection and benchmaxxing detection

**Primary source:** IndyDevDan, "Agentic Engineering Benchmarks: How I RANK Astra, Fable 5.1, and Open-Weights", https://youtu.be/9weiIHy9T_0 (published 2026-09-14).  
**Researched:** 2026-09-14 against `main` at `ce9c499`.  
**Purpose:** Turn the video's model-selection method into a MiniBench feature ("Benchmark Lens"). Implementation plan: [docs/PLAN-benchmark-lens.md](PLAN-benchmark-lens.md). Proposed decision record: [ADR 0004](adr/0004-benchmark-lens.md).

**Method note:** YouTube blocked transcript download from this environment (bot check). The analysis below uses the video's full published description and chapter list (fetched from the watch page), the five leaderboards the video links, and independent corroborating sources published the same fortnight. Claims attributed to the video are limited to what the description states; where I extrapolate, it is marked as such.

## 1. What the video argues

Chapters: 00:00 benchmarks are getting blurry · 01:50 top 5 · 02:19 Terminal-Bench · 08:13 APEX Agents · 11:55 AutomationBench · 20:17 AA-Omniscience · 25:32 DeepSWE · 29:50 why these five.

| # | Claim (from the description) | Implication for a benchmark product |
|---|---|---|
| 1 | "An index is a proxy of a proxy." Mashing ten benchmarks into one number destroys the only thing that matters: which model to run for *your* work. | Do not publish a composite. Show per-benchmark signal and let the user build their own index. |
| 2 | Model choice is a **three-dimensional** problem: performance, cost, and speed "together, as one unit". On Terminal-Bench v4.0 Astra and Fable 5.1 look close on score; on cost Astra is roughly 4x cheaper per task. | Every score must sit next to `$ / task` and `time / task`. Rank on a Pareto front, not a column. |
| 3 | **Throw out flat-line benchmarks.** Saturation means zero information gain. "I hunt for variance, because variance is where the alpha lives." AA Long Context Retrieval is called out as dead. | Compute spread across the frontier per benchmark; demote or hide saturated ones. MiniBench already does this at item level (`item_stats`, `check_ceiling_items`); the lens does it at benchmark level. |
| 4 | Variance reveals off-index truths: Gemini 3.8 Flash at the cost sweet spot, GLM 5.3 beating Kimi K3 where the index says otherwise, DeepSeek "quietly failing domains you might be deploying into". | Surface per-domain and per-benchmark rank inversions relative to the index. |
| 5 | AutomationBench's "killer detail": complete the objective **without tripping guardrails**; "the ranking flips hard when you turn violations back on." | Guardrail-clean completion is the primary metric; the flip magnitude is itself a signal. |
| 6 | AA-Omniscience: correct / incorrect / partial / **not attempted**, with zero penalty for "I don't know". "One hallucination upstream poisons every agent downstream." | Reward abstention. Score = correct − incorrect, not raw accuracy. |
| 7 | The five are proxies for **out-loop agentic engineering**: long-horizon, no human in the loop, "honest agents shipping on your behalf". Axes: alignment, truthfulness, cross-domain competence, raw engineering skill, affordable cost curve. "AGI you can't pay for is irrelevant." | The lens groups benchmarks by axis; a model needs coverage across axes, not a peak on one. |
| 8 | "The move is a model stack, not a model. Combine compute, don't select compute." Keep one eye on the index and one on **your own index**: the three or four benchmarks that map to your work. | Personal weighted index, computed client-side, never published as a MiniBench score. Fits the existing MoA / Multiplayer Cabinet story. |

### The five benchmarks and what each isolates

| Benchmark | Axis | What it measures | Why it is trusted | Saturation / caveats |
|---|---|---|---|---|
| **Terminal-Bench v4.0** (Laude Institute / Stanford; run by Artificial Analysis) | Raw engineering skill | 66 hard terminal tasks; real container, real harness loop, verifier checks final state. | Frozen harness, official leaderboard, per-task cost reported. | v2.x saturating (Fable 5.1 91.4% on v2.1); v4.0 frontier is ~56–58%, so it still discriminates. Anthropic documents ~6 points of movement from infrastructure alone. |
| **APEX Agents** (Mercor) | Cross-domain competence | Expert-authored investment-banking, consulting, and corporate-law tasks with knowledge-worker prompts. | Expert authorship; proxy for every non-SWE domain. | Rubric-graded; harness disclosure varies. |
| **AutomationBench** (run by Artificial Analysis as AutomationBench-AA) | Alignment at the floor | 600+ tasks across finance, HR, marketing, ops, sales, support in simulated SaaS environments; score is share of objectives completed **without guardrail violations**. | Independent run; the violation toggle exposes agents that "succeed" by breaking rules. | Vendor tables disagree wildly (Opus 5: 26.9% in Anthropic's table vs 50.3% in Meta's), which is itself evidence of harness dependence. |
| **AA-Omniscience** (Artificial Analysis) | Truthfulness / calibration | 6,000 questions, 6 domains, 42 topics. Index (−100..100) = rewards correct, penalises incorrect, no penalty for not attempting. Also reports Accuracy and Hallucination Rate = incorrect / (incorrect + partial + not attempted). | Independent, public subset on Hugging Face, three separable metrics. | Frontier top is ~44; far from saturated. High accuracy with high hallucination rate is the "attempts everything" fingerprint. |
| **DeepSWE v1.1** (Datacurve) | Long-horizon SWE from lazy prompts | Tasks written from scratch (not mined from public PRs), short realistic prompts, hidden tests. Standardized leaderboard fixes `mini-swe-agent` and reports uncertainty. | Contamination-resistant by construction; replaced SWE-Bench Pro in the AA Coding Agent Index because SWE-Bench Pro had become gameable (models recovering fixes from commit history). | Vendor launch tables quote non-standardized runs (Fable 5.1 67.4, Gemini 3.8 Flash 73.7, Muse Spark 1.3 75.4, Astra 74.1) that are not comparable to each other; standardized board shows Astra, Gemini, Opus, Sol clustered at 73–74 with overlapping CIs. |

## 2. Corroborating research (same fortnight)

- **Benjamin Marie, "The Era of Agentic Benchmaxxing" (Kaitchup #158, 2026-09-05).** Launch tables are composites of first-party runs plus imported third-party numbers; GPT-6 Astra's Terminal-Bench 4.0 comparator row repeats Anthropic's block verbatim. Proposes a comparability ladder: same revision + frozen harness + disclosed budgets → *comparable*; same named harness, undisclosed settings → *provisional*; different/unknown settings → *compares systems, not models*; launch table → *summary of claims, not an experiment*. Distinguishes legitimate agent optimisation from **adaptive benchmark overfitting** (using hidden-evaluator feedback as a dev set). Notes pass@k / best-of-k / config-search winner's curse inflate published numbers while more trials should not.
- **HarnessBench (Sakasegawa) and Artificial Analysis harness study.** Same model swings 8–24 points across harnesses; a model's own vendor harness is not reliably best. Any score without a harness identifier is a system score.
- **Artificial Analysis Intelligence Index v4.2/v4.3 (2026-09-04).** Retired GPQA Diamond for saturation, added harder tests, doubled private-test share to 40% "to reduce labs' ability to game evaluations". The index maintainers themselves are applying the video's saturation rule.
- **DeepSWE swap in the AA Coding Agent Index.** Reordered the top three; SWE-Bench Pro had been "flattering some combinations and penalizing others".
- **Anthropic self-report on Terminal-Bench.** ~6 points attributable to infrastructure and resource enforcement.

## 3. Operational definitions the plan uses

These are the concepts to encode. They are derived from the sources above; MiniBench-specific names are proposed in the plan.

**Claim provenance tier** (per model × benchmark × score):

| Tier | Definition | Comparable to other rows? |
|---|---|---|
| `standardized` | Run by the benchmark maintainer or an independent lab on a frozen public harness, with revision and budget disclosed; CI or trial count reported. | Yes, within the same tier and revision. |
| `provisional` | Same named harness, but effort level / budget / retry policy not disclosed. | Only with a caveat. |
| `self-reported` | Vendor's own first-party run in a launch post or system card. | Compares a tuned system, not the model. |
| `imported` | A number copied from another party's table into a launch table. | No; cite the original instead. |

**Benchmaxxing signals** (per model; each emits a flag with evidence, never a verdict):

| Signal | Computation | Reading |
|---|---|---|
| `self-report-gap` | self-reported − standardized on the same benchmark, in points | Large positive gap = heavy configuration search or undisclosed effort setting. |
| `index-vs-variance-gap` | rank on composite index − mean rank on high-variance benchmarks | Model rides saturated components of the index. |
| `guardrail-flip` | AutomationBench score with violations allowed − without | Completion bought by rule-breaking. |
| `attempt-everything` | Omniscience accuracy high while hallucination rate is also high | Tuned for accuracy metrics that do not penalise guessing. |
| `saturated-only-strength` | share of a model's top-quartile placements that are on saturated benchmarks | Wins concentrated where there is no information. |
| `harness-dispersion` | spread of the same model across harnesses on the same benchmark | Score depends more on harness than on model. |

**Genuine-capability signals** (the "inventing new ways of running" side the owner asked for):

| Signal | Computation | Reading |
|---|---|---|
| `efficiency-frontier` | On the Pareto front of score vs `$ / task` vs `time / task` (or tokens / steps where published) | Reaches the same outcome with less compute, e.g. Astra's low step and token count on standardized DeepSWE. |
| `abstention-calibrated` | Omniscience index high relative to accuracy; low hallucination rate | Knows what it does not know. |
| `guardrail-clean` | Small or zero guardrail flip with high clean completion | Completes work without breaking rules. |
| `cross-harness-stable` | Low harness dispersion | Capability is in the weights, not the scaffold. |
| `off-index-domain-win` | Beats an index-superior model on a specific APEX or AutomationBench domain | Real specialisation the index hides. |

**Benchmark signal quality** (per benchmark):

| Field | Computation |
|---|---|
| `information_gain` | Variance (or IQR) of frontier scores; a flat line is zero. Threshold to label `saturated` is a policy constant, defaulting to the top-10 spread being under 5 points. |
| `harness_sensitivity` | Published cross-harness spread when available; otherwise `unknown`. |
| `contamination_resistance` | `by-construction` (tasks authored fresh, hidden tests), `rotated`, `public-static`. |
| `standardized_leaderboard` | URL and `as_of` of the frozen-harness board, if one exists. |

## 4. Fit with MiniBench today

| Video concept | Already in the repository | Gap |
|---|---|---|
| Saturation = zero information | `item_stats.audit` flags `ceiling`, `floor`, `low-discrimination`; `check_ceiling_items` gate at 0.9; Arcade "Credits Rolling" triggers Season 2. | Item-level only. No benchmark-level or external-leaderboard-level information-gain metric. |
| Three-dimensional choice | Usage Board has `blended_per_million`, `latency_ms`, `eval_score`; `recommend` filters by budget and latency. | `eval_score` is one number (`intelligence_index` first-wins in `board._eval_and_latency`), which is exactly the "proxy of a proxy" the video rejects. `coding_index` and `agentic_index` are in the fixture but discarded. |
| No composite | Agent Cabinet never composites; PROJECT-STATUS: "no universal score". | Solo Arcade still has a `compositeScore` in `scoreScale.js` (separate surface, out of scope here). |
| Model vs harness recorded separately | Agent Cabinet provenance: `model`, `model_route`, `harness`, `harness_version`, `tool_contract_sha256`, budgets; `comparability_receipt` with mismatch reasons. | This is the strongest existing asset. It already implements the Kaitchup comparability ladder for MiniBench's own runs; it needs a mirror for external claims. |
| Guardrail floor | Agent Cabinet verifies final state; no violation counter. | Add `guardrail_violations` to the verify contract and make clean completion primary. |
| Abstention / hallucination | `calibration` category, `mean_brier`, axis-only categories excluded from pass pool. | No "not attempted" outcome with zero penalty; no Omniscience-style index. |
| Your own index | WoAI research already recommended client-side weight sliders (`docs/research-woaibench.md`, item 8). | Not built. |
| Citation discipline | ADR 0002: every number carries source and `as_of`. | Extend the same rule to any external benchmark claim. |

## 5. Boundaries this research respects

- ADR 0002 allowlists four OpenRouter Data API paths. The five benchmarks are **not all** exposed there; the fixture shows only `intelligence_index`, `coding_index`, `agentic_index` from `artificial-analysis`. Adding another source is an ADR-level decision, hence the proposed [ADR 0004](adr/0004-benchmark-lens.md). No scraping, no `/chat/completions`, no Mode B.
- Nothing here changes MiniBench's own measured cabinet results or represents an external claim as a MiniBench measurement.
- No paid model calls are needed for any phase of the plan; live OpenRouter GETs remain the only network path and stay under the existing authorization.

## 6. Source index

| Source | Used for |
|---|---|
| https://www.youtube.com/watch?v=9weiIHy9T_0 (description + chapters, fetched 2026-09-14) | Primary claims, chapter map, five-benchmark list |
| https://kaitchup.substack.com/p/the-era-of-agentic-benchmaxxing | Comparability ladder, imported-number fingerprinting, adaptive overfitting definition |
| https://artificialanalysis.ai/evaluations/omniscience | Index / Accuracy / Hallucination Rate definitions, current frontier values |
| https://artificialanalysis.ai/evaluations/terminalbench-v2-1 | v2.1 saturation evidence (91.4%) |
| https://nyosegawa.com/en/posts/harness-bench/ | Cross-harness spread; task-count power caveat (27 tasks not significant) |
| https://ajaymittur.github.io/blog/2026/coding-agents-harnesses-where-things-are-going/ | Harness swings; "own harness is not reliably best" |
| https://digg.com/tech/wg2ou9hv | AA Coding Agent Index swap to DeepSWE; SWE-Bench Pro gameability |
| https://www.deeplearning.ai/the-batch/fable-holds-the-top-spot-for-now | Intelligence Index v4.2 retiring GPQA, 40% private share |
| Video-linked leaderboards (verified reachable 2026-09-14): https://artificialanalysis.ai/evaluations/terminalbench-v4-0, https://www.mercor.com/apex/apex-agents, https://artificialanalysis.ai/evaluations/automationbench-aa, https://artificialanalysis.ai/evaluations/omniscience, https://deepswe.datacurve.ai/ | Benchmark registry seed |
