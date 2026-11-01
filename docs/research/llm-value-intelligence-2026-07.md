# LLM Value Intelligence for MiniBench

**Research snapshot:** 2026-07-17  
**Status:** proposed methodology; no benchmark scores are reproduced in this report  
**Scope:** hosted/API language models and agent configurations. This design requires no hardware tests.

## Executive conclusion

MiniBench should not turn another benchmark average into a universal ranking. It should treat a model deployment as an asset that produces **successful, on-time tasks** while consuming money and time. The primary unit of value is therefore:

\[
\text{Cost per successful SLA task}_{m,u}
= \frac{E[C_{m,u}]}{P(Y_{m,u}=1,\ L_{m,u}\le D_u)}
\]

where model/configuration \(m\) is evaluated on use case \(u\), \(C\) is the full observed episode cost, \(Y\) is task success, \(L\) is end-to-end latency, and \(D_u\) is the use case's deadline. This quantity naturally charges a model for incorrect answers, malformed outputs, retries, tool calls, provider failures, and missed deadlines. Artificial Analysis independently uses actual token consumption to calculate cost per benchmark task, including input, cached, reasoning, and answer tokens; OpenRouter returns native-token usage and charged cost in each response.[AA-M][OR-U]

A small quality gain is worth a premium only when its expected benefit exceeds its incremental cost and delay. For expensive model \(A\) versus cheaper model \(B\):

\[
\Delta U(V,\lambda)=V\Delta p-\Delta C-\lambda\Delta L-\Delta R
\]

\[
V^*=\frac{\Delta C+\lambda\Delta L+\Delta R}{\Delta p},\qquad \Delta p>0
\]

Here \(p=P(Y=1,L\le D)\), \(V\) is business value per successful on-time task, \(\lambda\) is value of one unit of delay, and \(R\) is an explicit expected risk/failure penalty. Choose \(A\) only when \(V>V^*\), subject to uncertainty. If the confidence interval for \(\Delta p\) includes zero, the break-even value is statistically unresolved and MiniBench must not claim that the premium is justified.

The product should consequently publish:

1. **use-case scorecards**, not one context-free champion;
2. **actual cost per successful on-time task** and successful tasks per dollar;
3. **quality, cost, latency, and reliability as separate audited dimensions**;
4. a **Pareto frontier** before any weighted winner;
5. confidence intervals, rank ranges, and probability-of-winning;
6. a user-entered value-of-success calculator that exposes the break-even point; and
7. a source/licence ledger that prevents third-party methodology from being mistaken for redistributable data.

## 1. What the strongest current sources contribute

### 1.1 Artificial Analysis: capability, end-to-end performance, and task cost

Artificial Analysis explicitly benchmarks quality, performance, and price at the model/endpoint level. Its current Intelligence Index v4.1 is versioned, spans nine evaluations, and publishes category weights rather than implying that benchmark composition is timeless.[AA-I][AA-API] Its performance methodology measures customer-experienced API behavior, distinguishes time to first token, time to first answer token, output speed, and end-to-end response time, and represents normal workloads with rolling medians.[AA-P]

**MiniBench lesson:** adopt the separation of model, provider endpoint, workload, and vintage; calculate cost from observed consumption rather than list price alone; and version every composite. Do not copy Artificial Analysis data from web pages. Its documented API requires attribution, has tiered access, and directs users to its Terms of Use for redistribution rights.[AA-API]

### 1.2 LMArena: live preferences and honest ranking uncertainty

Chatbot Arena/LMArena uses anonymous randomized pairwise battles and Bradley–Terry estimation to infer preference from heterogeneous, open-ended user prompts.[ARENA-P] The current Arena-Rank package is Apache-2.0 and supports contextual/style-controlled Bradley–Terry models and confidence intervals.[ARENA-R] LMArena now reports a raw rank plus a rank spread implied by overlapping score intervals instead of converting uncertainty into false precision.[ARENA-CI]

**MiniBench lesson:** use pairwise preference only for subjective tasks, blind model identity and side, control response-style covariates, and display rank ranges. Arena preference is evidence about human preference—not an interchangeable substitute for objective correctness, production reliability, or MiniBench's use-case task success.

### 1.3 LiveBench: freshness and objective grading

LiveBench was designed around frequently refreshed questions from recent sources and objective, automatically verifiable answers rather than an LLM judge. Its published design covers diverse categories and refreshes questions to reduce contamination risk.[LIVE-P][LIVE-R]

**MiniBench lesson:** maintain a rolling hidden tranche, use temporal holdouts, prefer executable or deterministic graders, and expire old evidence. “Contamination-free” should be treated as a design goal, not an absolute guarantee: public questions can enter later training corpora, and the LiveBench paper itself motivates continual refresh for this reason.[LIVE-P]

### 1.4 SWE-bench: harness identity is part of the result

SWE-bench evaluates patches by applying them to real repositories and executing tests in containers. SWE-bench Verified is a human-reviewed 500-instance subset whose problem statements, tests, and solvability were checked.[SWE-E][SWE-V] The current Verified page warns that even results using mini-SWE-agent 1.x and 2.x are not necessarily comparable because the harness changed.[SWE-V]

**MiniBench lesson:** a coding result belongs to **model × endpoint × agent/scaffold × tool policy × benchmark version × run configuration**. Never merge “model-only” and arbitrary-agent leaderboards. Crown coding winners only within a fixed, pinned harness lane, and report full-system lanes separately.

### 1.5 OpenRouter: operational ground truth for charged usage and routing

OpenRouter's Models API exposes model IDs, pricing dimensions (including cache read/write, reasoning, request, and conditional overrides), capabilities, and context limits.[OR-M] Its response `usage` object reports native-token counts, reasoning and cache details, and charged cost.[OR-U] Provider routing can prioritize price, throughput, or latency and supports fallbacks; fallback requests are charged according to the model ultimately used.[OR-R][OR-F]

**MiniBench lesson:** ingest live operational metadata through the documented API, but record the actually served model/provider and actual response cost. A routed alias is not a stable model observation. Failed first attempts add latency, so route policies themselves need evaluation.[OR-F][OR-L]

### 1.6 HELM and Epoch AI: broad coverage, provenance, and reproducibility

HELM's central contribution is a reproducible framework that exposes scenarios, models, metrics, and predictions rather than hiding a single score; its code is Apache-2.0.[HELM] Epoch AI separates internally run evaluations from external results, publishes run settings and logs, cites provenance per result, repeats many evaluations, and warns that prompt/settings changes and contamination can materially alter results.[EPOCH] Epoch also licences its own benchmark-hub data under CC BY while preserving upstream licences for externally sourced data.[EPOCH]

**MiniBench lesson:** retain raw run artifacts and field-level provenance, separate “run by MiniBench” from “reported by source,” and never erase protocol differences through normalization.

## 2. Canonical observation and evidence model

The atomic identity is:

```text
(model_revision, endpoint/provider, routing_policy, harness_revision,
 prompt_template_revision, tool_policy, decoding/reasoning_settings,
 benchmark/task_revision, region, run_timestamp)
```

Never collapse aliases such as `latest` across time. Store the provider-returned model ID, upstream endpoint when available, and immutable model revision where the provider exposes it. For every episode store:

- task and use-case stratum;
- success/partial-credit result and grader revision;
- request count, retry/fallback chain, tool invocations, and terminal failure class;
- input, cache-read, cache-write, visible output, and reasoning tokens when exposed;
- total charged cost and price snapshot;
- queue time, time to first token, time to first answer token where observable, end-to-end latency, and deadline status;
- source class: `minibench_run`, `licensed_import`, or `reported_external`;
- artifact hashes, timestamps, and code/config revisions.

The unit of comparison is the **episode**, not an individual API call. If a policy retries or falls back, all attempts, cost, and elapsed time belong to that episode. This prevents unreliable cheap models from appearing artificially inexpensive.

### Evidence hierarchy

1. **MiniBench hidden/rotating evals:** primary evidence for use-case valuation.
2. **Licensed, protocol-compatible imports:** secondary evidence, clearly labelled.
3. **External reported scores:** capability context or prior evidence only.
4. **Vendor self-reports:** displayed as claims, never used to crown a winner without independent replication.

External evidence should never silently become MiniBench task success. If enough models overlap, fit a pre-registered calibration on historical models:

\[
\operatorname{logit}(p_{m,u})=\alpha_u+\sum_b\beta_{u,b}z_{m,b}
\]

where \(z_{m,b}\) is a version-pinned external benchmark feature. Validate out of sample and shrink coefficients. If overlap is inadequate or calibration drifts, show the external score separately and give it zero weight in the valuation. This is safer than averaging ranks or assuming that one point from unrelated benchmarks has the same meaning.

## 3. Quality and normalization

### 3.1 Use-case quality

Let task strata \(k\) have declared user weights \(w_{u,k}\), with \(\sum_k w_{u,k}=1\). For bounded task score \(Y\in[0,1]\):

\[
Q_{m,u}=\sum_k w_{u,k}\,E[Y_{m,k}]
\]

For a strict production view, define:

\[
p_{m,u}^{SLA}=P(Y_{m,u}\ge \tau_u,\ L_{m,u}\le D_u)
\]

where \(\tau_u\) is the acceptance threshold. This single joint event avoids double-counting reliability: transport errors, invalid output, and missed deadlines are failures. Diagnostic panels may decompose `correct_given_response`, transport completion, schema validity, and SLA attainment, but the headline probability remains joint.

Weights must represent an explicit use-case workload, not the tasks that happen to be available. Publish at least the weight vector, task counts, scorer, language, sampling dates, and coverage gaps. Artificial Analysis's versioned category weights demonstrate why changing composition requires a new composite version.[AA-I]

### 3.2 Normalize only for visualization or calibrated prediction

- Preserve native accuracy/pass rate whenever semantics match.
- For pairwise preference, convert a Bradley–Terry difference to a win probability against a **fixed versioned anchor**, not to “percent correct.”[ARENA-P][ARENA-R]
- For cross-benchmark radar charts, use within-benchmark/version percentiles or robust standardized scores and label them as relative position only.
- Do not min-max across the currently visible model set: adding a model changes every score.
- Do not average leaderboard ranks: rank gaps have no common cardinal meaning.
- Do not compare composites across major methodology versions. Artificial Analysis explicitly notes that its index versions change evaluations, weighting, normalization, and graders.[AA-API][AA-I]

## 4. Cost, latency, and reliability

### 4.1 Full episode cost

For episode \(i\), sum every attempt \(a\):

\[
C_i=\sum_a (n^{in}_{ia}r^{in}_{ia}+n^{read}_{ia}r^{read}_{ia}+n^{write}_{ia}r^{write}_{ia}
+n^{reason}_{ia}r^{reason}_{ia}+n^{out}_{ia}r^{out}_{ia}+r^{request}_{ia}+C^{tool}_{ia})
\]

Prefer the provider's charged `usage.cost` as ledger truth and retain the token-price reconstruction as an audit. OpenRouter documents both detailed usage and conditional pricing overrides; Artificial Analysis's cost-per-task method likewise uses actual input, cache, reasoning, and answer consumption.[OR-M][OR-U][AA-M]

Report mean and median attempted-task cost, but make these primary:

\[
\text{Success yield}=\frac{p^{SLA}}{E[C]} \quad\text{and}\quad
\text{CPS}=\frac{E[C]}{p^{SLA}}
\]

The first is successful on-time tasks per dollar; the second is dollars per successful on-time task. When \(p^{SLA}=0\), CPS is infinite—not zero or missing. Cache assumptions must match the use case; cold-cache and warm-cache lanes should be separate.

### 4.2 Latency and reliability

Report end-to-end p50, p90, p95, and p99, plus time-to-first-answer-token when available. Do not infer user latency from tokens/second alone. Artificial Analysis distinguishes these measures and notes that prompt length/load affect performance.[AA-P]

Reliability panels should show:

- transport completion;
- valid/parseable completion;
- tool/harness completion;
- correct completion;
- correct within deadline;
- fallback and retry rates;
- failure classes and provider concentration.

Measure across time windows and regions relevant to the target workload. OpenRouter's routing performance statistics use a rolling window and treat latency/throughput thresholds as preferences rather than guarantees, reinforcing that marketplace metadata is routing evidence, not an SLA.[OR-R]

## 5. Valuation-style metrics

These are analytical analogies, not financial securities metrics.

| MiniBench metric | Formula | Interpretation |
|---|---:|---|
| **Success yield** | \(p^{SLA}/E[C]\) | successful on-time tasks per dollar; higher is better |
| **Cost per success (CPS)** | \(E[C]/p^{SLA}\) | price paid for one expected successful on-time task; lower is better |
| **Incremental quality price** | \(\Delta C/\Delta p\) | extra dollars per additional unit of success probability |
| **Net task value** | \(Vp^{SLA}-E[C]-\lambda E[L]-R\) | expected economic surplus per task |
| **Value margin** | \((Vp^{SLA}-E[C])/(Vp^{SLA})\) | surplus share before latency/risk, when \(Vp^{SLA}>0\) |
| **Risk-adjusted value** | lower confidence/credible bound of net task value | conservative selection criterion |
| **Regret vs best** | \(U_{best}-U_m\) | expected opportunity loss under declared assumptions |
| **Evidence grade** | protocol/provenance/recency coverage, not a score multiplier | confidence in the measurement |

Do not multiply all dimensions into an opaque “value index.” Multiplication creates arbitrary interactions and can let a near-zero denominator dominate. Keep the decomposition visible and derive a winner only after the user supplies constraints or economic values.

### 5.1 Is a 1-point gain worth a premium?

For models \(A\) and \(B\), compare paired task outcomes:

\[
\Delta p=p_A^{SLA}-p_B^{SLA},\quad
\Delta C=E[C_A]-E[C_B],\quad
\Delta L=E[L_A]-E[L_B]
\]

The maximum rational premium per task, before delay/risk, is \(V\Delta p\). Including delay and risk, the premium model is justified when:

\[
V\Delta p > \Delta C+\lambda\Delta L+\Delta R
\]

Examples must use probability points, not ambiguous “percent improvement.” A move from 0.80 to 0.81 is \(\Delta p=0.01\). If that task is worth $20 when successful and latency/risk are equal, the maximum expected premium is $0.20 per attempt. This is a direct substitution into the formula, not a market claim.

For asymmetric failure harm \(H\), fold it into utility:

\[
U=Vp^{SLA}-C-H(1-p^{SLA})-\lambda L
\]

Then higher accuracy can be worth much more in high-stakes use cases. MiniBench should ask for \(V\), \(H\), deadline, latency value, and budget rather than imposing universal defaults.

## 6. Uncertainty and confidence

### 6.1 Required estimator

Use a **paired, stratified cluster bootstrap** as the default:

1. resample task IDs within each use-case stratum;
2. resample repeated trials within task, retaining all calls in an episode;
3. keep paired model outcomes together for head-to-head differences;
4. for latency/reliability collected over time, resample time blocks rather than individual requests;
5. recompute \(Q\), \(p^{SLA}\), cost, CPS, utility, frontier membership, and rank for each replicate;
6. publish 95% intervals and the number of independent tasks, trials, dates, and blocks.

This preserves task mix and correlation between quality, cost, and latency. Ratio intervals for CPS must be computed from the joint replicates, not by dividing endpoints of separate intervals. Near zero successes produce wide or unbounded intervals; say so. LMArena's emphasis on confidence intervals and rank spreads, and Epoch's repeated-run uncertainty, support presenting uncertainty as a first-class result rather than a footnote.[ARENA-CI][EPOCH]

For simple binary diagnostic panels, a Wilson interval is acceptable. For subjective pairwise comparisons, use the maintained Arena-Rank Bradley–Terry implementation or an independently validated equivalent, with side/order and style covariates.[ARENA-R]

### 6.2 Winner declaration rule

Publish for each use case:

- point estimate and 95% interval;
- probability each model is utility-best under bootstrap replicates;
- rank range from the replicate distribution;
- probability each model is Pareto-nondominated;
- smallest effect of interest (SESOI), declared before evaluation.

Call a model **winner** only if it passes all hard constraints, has at least 95% probability of highest utility, and its expected advantage exceeds the SESOI. Otherwise label co-leaders or “insufficient evidence.” Avoid multiple pairwise claims without simultaneous/bootstrap rank treatment.

## 7. Pareto frontier and use-case crowns

A deployment is dominated if another deployment is no worse on all declared dimensions and strictly better on at least one. Default dimensions are:

- maximize \(p^{SLA}\) and reliability;
- minimize expected cost, p95 latency, and high-severity failure risk.

Show a two-dimensional quality–cost chart for readability, but calculate the frontier over the full declared set. Add uncertainty by reporting the fraction of bootstrap replicates in which each model is nondominated. Never remove a model solely because point estimates show tiny dominance with overlapping uncertainty.

Suggested crowns:

| Crown | Eligibility and objective |
|---|---|
| **Budget batch** | maximize conservative success yield subject to minimum quality and no interactive SLA |
| **Interactive** | maximize lower-bound utility subject to p95 end-to-end deadline and reliability floor |
| **Coding, fixed harness** | maximize lower-bound utility on MiniBench coding tasks with identical pinned scaffold/tool policy |
| **Premium/high-stakes** | maximize lower-bound utility using user-supplied failure harm and auditability constraints |
| **Most reliable** | highest lower confidence bound on successful-within-SLA probability |
| **Frontier pick** | Pareto-nondominated; no single winner asserted |

A routed configuration can be crowned separately from a model endpoint. OpenRouter fallbacks can improve completion but alter model identity, price, and latency, so the route policy must be named and evaluated as the product being selected.[OR-F][OR-L]

## 8. Sensitivity and decision robustness

Every crown should ship with:

1. **Break-even chart:** winner over ranges of value per success \(V\), latency value \(\lambda\), and failure harm \(H\).
2. **Weight sensitivity:** sample plausible use-case weight vectors from a declared simplex or user ranges; report win share.
3. **Price shock:** recompute at current price and ±10%, ±25%, plus observed historical price where licensed.
4. **Quality uncertainty:** recompute over bootstrap draws and plausible grader error.
5. **Workload scenarios:** short/long context, cold/warm cache, low/high output, and single/concurrent traffic as separate lanes.
6. **Leave-one-stratum-out:** expose dependence on one benchmark category.
7. **Freshness decay:** show results with and without stale evidence; do not silently discount.

The decision is **robust** only when the same model wins across the declared core region. Otherwise MiniBench should surface the boundary (“Model A wins above $X value per success; Model B below it”) rather than force a rank.

## 9. Anti-gaming, contamination, and protocol controls

### 9.1 Evaluation integrity

- Pre-register task mix, prompts, scorers, decoding policy, retries, budgets, stopping rules, SESOI, and analysis before unblinding model names.
- Maintain public development tasks, a hidden scoring set, and a sealed audit set.
- Rotate a time-stamped fraction of hidden tasks; retire exposed tasks from crown eligibility.
- Use post-training-cutoff or newly authored tasks where feasible and track source/publication dates. LiveBench's frequent refresh and recent-source design is the relevant precedent.[LIVE-P][LIVE-R]
- Prefer deterministic checks, executable tests, database end-state validation, or expert rubrics. LiveBench specifically avoids LLM judging for objectively gradable questions, while SWE-bench uses repository tests.[LIVE-P][SWE-E]
- When LLM judges are unavoidable, blind identity and order, randomize sides, use multiple independently prompted judges, include human-audited sentinel items, estimate judge error, and test verbosity/style effects.
- Canary strings are leakage signals, not proof of non-contamination; also run paraphrase/variant families and temporal holdouts.

### 9.2 Operational anti-gaming

- Test through ordinary paid/public accounts and compare occasional independent accounts. Artificial Analysis explicitly requires benchmark traffic to receive the same public model/configuration and checks independent accounts for differential service.[AA-P]
- Pin exact model and harness identities; quarantine silent alias changes.
- Randomize schedule and payload ordering; distribute requests across relevant time blocks.
- Cap submissions and deduplicate task/output fingerprints; investigate correlated submitters.
- Retain signed raw artifacts and append-only price/methodology snapshots.
- Separate provider outage from model error diagnostically, but charge both to the evaluated deployment policy.
- Run holdout audits after leaderboard publication and retract contaminated or non-reproducible crowns with a visible changelog.

### 9.3 Comparability gates

Do not combine results unless model revision, harness lane, task version, tool access, token/reasoning budget, retry policy, and scoring semantics are compatible. SWE-bench's explicit warning that mini-SWE-agent major versions are not necessarily comparable is a concrete example.[SWE-V] A methodology change creates a new series; bridge studies may quantify the shift but must not rewrite history.

## 10. Source, access, and licence matrix

This table is operational guidance, not legal advice. Recheck current terms before implementation.

| Source | What MiniBench may learn/use | Data/import posture | Licence/terms evidence | Recommended treatment |
|---|---|---|---|---|
| Artificial Analysis | task-cost accounting, endpoint performance dimensions, versioned composites | Structured API is documented by tier; attribution required; redistribution requires applicable terms/bespoke permission | API docs and Terms link[AA-API] | **Method inspiration by default.** Import only through a contracted API plan, attribute visibly, and store fields allowed by that agreement; never scrape tables. |
| LMArena / Arena-Rank | Bradley–Terry, contextual/style control, CIs, rank spread | Arena-Rank/FastChat code is Apache-2.0. Released dataset prompts are CC BY 4.0, while model outputs remain under provider terms | Arena-Rank release and dataset card[ARENA-R][ARENA-D] | Code/method import is permissible with notices. Treat raw conversations/model outputs as mixed-rights; do not republish without checking provider terms. Derived MiniBench pairwise data is preferable. |
| LiveBench | rolling fresh tasks, objective grading, category design | Repository licence combines Apache-2.0 and included MIT components; paper identifies repository as Apache-2.0; underlying source datasets/content may have separate rights | repository licence and paper[LIVE-L][LIVE-P] | Run the licensed harness or adapt methodology. Verify each task/data dependency before bundling or redistributing questions. Import MiniBench's own aggregate run results. |
| SWE-bench / Verified | real issue resolution, containerized test grading, fixed-harness lane | Harness repository is MIT; task records derive from third-party GitHub repositories and retain relevant upstream rights | official repository licence and docs[SWE-L][SWE-E] | Use/pin harness with MIT notice; check dataset and repository licences before redistributing task content. Prefer own aggregate results and artifact links. |
| OpenRouter | live model metadata, pricing, served model, charged usage, routing/fallback behavior | Public documented APIs expose metadata/usage; reviewed docs did not state a general bulk-redistribution licence | Models, usage, and routing docs[OR-M][OR-U][OR-R] | Query operationally under account terms; cache timestamped minimal facts needed for audits. Do not mirror the catalog or claim redistribution rights without written terms. |
| HELM | scenario/metric separation, reproducible run artifacts | Framework is Apache-2.0; individual scenario datasets have their own licences | official repository[HELM] | Reuse framework/method with attribution and notices; audit every scenario dataset separately. Do not assume the code licence covers benchmark content. |
| Epoch AI Benchmarking Hub | repeated runs, logs, per-result provenance, internal/external separation | Epoch's own data is CC BY; external-source rows retain original licences; Python client is MIT | official methodology/licensing page[EPOCH] | **Strongest direct import candidate:** import eligible Epoch-owned rows with attribution and provenance; enforce per-row upstream licence for external data. |
| MiniBench evals | use-case success, actual episode cost/latency/reliability | First-party data generated under MiniBench's own protocol | MiniBench run artifacts and repository policy | Primary evidence for valuation and crowns; publish aggregate results plus privacy-safe reproducibility artifacts. |

## 11. Recommended implementation sequence

### Phase 1 — defensible minimum

1. Define 3–5 use cases and versioned task strata.
2. Add immutable run identity and episode-level cost/latency/failure telemetry.
3. Compute \(p^{SLA}\), success yield, CPS, net task value, and paired bootstrap intervals.
4. Publish quality–cost frontier plus user-entered \(V\), \(H\), \(\lambda\), budget, and deadline.
5. Crown only within a fixed use-case/harness lane using the winner rule.
6. Add provenance/licence fields and block imports without an allowed-use record.

### Phase 2 — broader intelligence

1. Add licensed Epoch imports and contracted sources only after field-level rights review.
2. Add MiniBench pairwise preference tasks for inherently subjective use cases using Arena-Rank methodology.
3. Add rolling hidden tasks, temporal holdouts, and post-publication audits.
4. Add time-block reliability studies and evaluated route policies.
5. Fit external-to-MiniBench calibration only after sufficient overlap and out-of-sample validation.

### Non-negotiable product language

- “Best for **this use case and these assumptions**,” never “best model.”
- “Reported by source” versus “run by MiniBench.”
- “Expected cost per successful on-time task,” not merely “price per million tokens.”
- “Statistical co-leader/insufficient evidence” when uncertainty does not resolve the winner.
- Methodology version, data vintage, model revision, harness, and source licence on every result page.

## References (primary/first-party)

- **[AA-M]** Artificial Analysis, [Benchmarking Methodology and definitions](https://artificialanalysis.ai/methodology) — model/endpoint definitions, cost per task, TTFT, output speed, and end-to-end formulas.
- **[AA-I]** Artificial Analysis, [Intelligence Benchmarking Methodology](https://artificialanalysis.ai/methodology/intelligence-benchmarking) — current v4.1 composition, weights, repeats, scoring, and version history.
- **[AA-P]** Artificial Analysis, [Language Model API Performance Benchmarking](https://artificialanalysis.ai/methodology/performance-benchmarking) — workloads, cadence, rolling medians, token conventions, independent-account checks, and integrity terms.
- **[AA-API]** Artificial Analysis, [Data API documentation](https://artificialanalysis.ai/data-api/docs) — tiers, fields, rate limits, index versioning, attribution, and redistribution/Terms notice.
- **[ARENA-P]** Chiang et al., [Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference](https://arxiv.org/abs/2403.04132) — anonymous battles, Bradley–Terry estimation, uncertainty, active sampling, and anomaly controls.
- **[ARENA-R]** LMArena, [Arena-Rank: Open Sourcing the Leaderboard Methodology](https://lmarena.ai/blog/arena-rank/) — current package, contextual/style control, closed-form CIs, and Apache-2.0 licence.
- **[ARENA-CI]** LMArena, [Arena's Ranking Method](https://news.lmarena.ai/ranking-method/) — raw rank, confidence intervals, and rank spread.
- **[ARENA-D]** LMArena, [Arena Human Preference 100K dataset card](https://huggingface.co/datasets/lmarena-ai/arena-human-preference-100k) — prompt CC BY 4.0 and provider-governed model output terms.
- **[LIVE-P]** White et al., [LiveBench: A Challenging, Contamination-Free LLM Benchmark](https://livebench.ai/livebench.pdf) — freshness, objective grading, diversity, limitations of LLM judging, and licence statement.
- **[LIVE-R]** LiveBench, [official repository](https://github.com/LiveBench/LiveBench) — rolling-question design, harness, data links, and current run options.
- **[LIVE-L]** LiveBench, [repository licence](https://raw.githubusercontent.com/LiveBench/LiveBench/main/LICENSE) — Apache-2.0 FastChat-derived and MIT LiveCodeBench-derived components.
- **[SWE-V]** SWE-bench, [Verified methodology](https://www.swebench.com/verified.html) — human-filtered 500 tasks, fixed mini-SWE-agent lane, and cross-version comparability warning.
- **[SWE-E]** SWE-bench, [Evaluation guide](https://www.swebench.com/SWE-bench/guides/evaluation/) — containerized patch application and test execution.
- **[SWE-L]** SWE-bench, [repository and MIT licence](https://github.com/SWE-bench/SWE-bench) — code/data project identity and repository licence.
- **[OR-M]** OpenRouter, [Models API documentation](https://openrouter.ai/docs/guides/overview/models) — canonical IDs, pricing dimensions/overrides, capabilities, and native tokenization.
- **[OR-U]** OpenRouter, [Usage Accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting) and [API response schema](https://openrouter.ai/docs/api_reference/overview) — charged cost, cache/reasoning/native-token fields, and generation audit endpoint.
- **[OR-R]** OpenRouter, [Provider Routing](https://openrouter.ai/docs/guides/routing/provider-selection) — price/throughput/latency routing, fallbacks, thresholds, and rolling performance percentiles.
- **[OR-F]** OpenRouter, [Model Fallbacks](https://openrouter.ai/docs/guides/routing/model-fallbacks) — trigger behavior, response model identity, and pricing by ultimately served model.
- **[OR-L]** OpenRouter, [Latency and Performance](https://openrouter.ai/docs/guides/best-practices/latency-and-performance) — fallback latency and routing around recent failures.
- **[HELM]** Stanford CRFM, [HELM](https://crfm.stanford.edu/helm/) and [official repository](https://github.com/stanford-crfm/helm) — scenario/metric/model transparency, reproducibility, and Apache-2.0 code.
- **[EPOCH]** Epoch AI, [Benchmarking methodology and licensing](https://epoch.ai/benchmarks/about) — internal versus external provenance, run settings/logs, repeated-run uncertainty, contamination caveats, CC BY data, and retained upstream licences.
