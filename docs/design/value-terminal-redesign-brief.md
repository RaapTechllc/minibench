# MiniBench Value Terminal — implementation-ready redesign brief

**Status:** Recommended direction  
**Audience:** Product, frontend, backend/data, benchmark operators  
**Primary user:** A technical buyer choosing a model or deployment configuration  
**Design objective:** Turn MiniBench from a collection of benchmark views into a coherent decision product that answers:

1. **Which model should I use?**
2. **What does successful work cost at my volume?**
3. **Is the premium tier worth it?**
4. **Which local or cloud setup fits my constraints?**

This is a design brief, not a code change. It uses the present React implementation, screenshots, API contracts, benchmark methodology, model catalog, agent/MoA tooling, and hardware data as its source material.

---

## 1. Executive recommendation

Build **Value Terminal**: a light-first, premium research terminal organized around decisions rather than benchmark taxonomy. It should feel closer to a financial research product than a startup dashboard: quiet surfaces, compact controls, strongly aligned numbers, explicit assumptions, linked evidence, and a clear distinction between recommendation, measurement, and provenance.

The core product loop becomes:

> **Describe the job → see a recommendation and alternatives → inspect cost/quality trade-offs → compare → open the evidence.**

Do not carry the current arcade metaphor forward as the shell. Tier labels can survive as an optional plain-language interpretation of scores, but “Solo Cabinet,” “Multiplayer Cabinet,” “$/quarter,” neon chart chrome, scanlines, and “HOLD START” interactions should be removed from the primary experience. They are memorable, but they turn a purchase decision into a theme and make the product less credible precisely where its methodology is strongest.

The redesign should also stop treating local hardware, cloud models, and MoA pipelines as unrelated products. They are three deployment choices in one decision system. Preserve their different evidence models, but present them through the same buyer questions: capability, reliability, latency, unit cost, monthly cost, compatibility, and confidence.

---

## 2. Product truth and design principles

### Product truth

MiniBench’s defensible advantage is not visual novelty. It is the combination of:

- executable, deterministic graders;
- contamination and validity gates;
- confidence intervals and pairwise significance discipline;
- real run cost accounting;
- pinned model/provider snapshots;
- local throughput and memory-bandwidth evidence;
- model, agent/MoA, and hardware data in one system.

The interface should make that rigor useful without making every visitor read the methodology first.

### Design principles

1. **Lead with a decision, not a dataset.** Every primary page must answer “so what?” before showing a complete table.
2. **Show recommendation and evidence together.** Never present a “best” badge without the workload, constraints, score, cost, and confidence behind it.
3. **Translate, then disclose.** Use buyer language first (“Best value for coding under $100/month”); preserve pass rate, CI, suite, grader, and snapshot in an evidence layer.
4. **Use density deliberately.** Dense tables are appropriate; repeated stat cards, oversized hero text, and large empty chart canvases are not.
5. **No theme as product logic.** Metaphor must not rename units or hide semantics. Cost per task remains cost per task.
6. **Separate measured, estimated, and unavailable.** A benchmark result, a scenario projection, and an unknown must look and read differently.
7. **Default to honest comparison.** Comparability and validity are hard gates, not footnotes.
8. **Mobile is a decision summary, not a squeezed desktop terminal.** Recompose, do not merely overflow.
9. **Accessibility is part of trust.** Data must not depend on hover, color, animation, or visual position alone.
10. **One accent, few surfaces, almost no decoration.** The data and recommendation state create the hierarchy.

---

## 3. Audit of the current experience

### 3.1 The product has two centers of gravity

The root README still defines MiniBench as “Crowdsourced LLM benchmarks for Mini PCs” and asks for the best local hardware per dollar (`README.md:1-5`), while the capability pivot explicitly demotes hardware and promotes model capability (`docs/PIVOT-PLAN.md:7-20`). The frontend reflects both strategies at once.

The Overview opens with a capability-first promise, then immediately presents “Legacy” throughput, submissions, HEI, two large hardware charts, and recent legacy submissions (`frontend/src/pages/Dashboard.tsx:273-317`, `320-425`, `427-488`). This forces a new visitor to resolve the product strategy before they can use the product.

**Design consequence:** The home page must not be a museum of both roadmaps. It should be a decision desk, with legacy hardware evidence accessible as evidence rather than occupying the main narrative.

### 3.2 Navigation mirrors implementation modules, not user decisions

The main navigation is Overview, Models, Agents, MoA Calculator, Test Rigs, and Methodology (`frontend/src/App.tsx:16-23`). Compare and Submit exist as routes but are absent from the nav (`frontend/src/App.tsx:84-96`). “Agents” describes an internal evaluation object; “Test Rigs” describes benchmark operations; “MoA Calculator” describes a mechanism. None directly names the buyer jobs “choose,” “compare,” or “plan cost.”

**Design consequence:** Reframe the IA around Recommend, Models, Setups, Compare, and Evidence. Keep contribution/admin actions in a secondary menu.

### 3.3 The visual system is coherent in isolation but reads as generated dashboard UI

The base system describes itself as “Apple-light,” with cool paper, white cards, blue accent, three large radii, layered shadows, pills, stat tiles, uppercase eyebrows, and entrance animations (`frontend/src/index.css:3-8`, `9-65`, `176-194`; `frontend/src/components/ui.tsx:7-29`, `44-76`). The shell uses a generic gauge-in-a-rounded-square logo and Lucide icon for every navigation item (`frontend/src/App.tsx:3`, `16-23`, `55-73`).

These are common AI-generated SaaS patterns:

- oversized marketing headline above every tool;
- tiny uppercase blue eyebrow;
- repeated floating white rounded cards;
- badges for most attributes;
- generic icon-plus-label navigation;
- a four-tile stat strip regardless of information priority;
- soft rise animations applied broadly;
- explanatory microcopy inside every card.

No single element is bad, but their accumulation produces a familiar “assembled dashboard” texture. The result feels pleasant but non-specific. A benchmark terminal should communicate authority through typographic alignment, stable columns, provenance, and explicit assumptions—not card count.

### 3.4 Arcade chrome fractures trust and product coherence

The CSS defines a separate black/neon/scanline arcade system (`frontend/src/index.css:37-49`, `90-173`). Models and Agents each wrap their complete page in that theme (`frontend/src/pages/Models.tsx:228-241`; `frontend/src/pages/Agents.tsx:167-173`), while the masthead, methodology, hardware, calculator, and footer remain daylight. This creates two products inside one shell.

The metaphor also changes meaningful units: Agents labels cost per task as “$/quarter” (`frontend/src/pages/Agents.tsx:221-265`, `276-299`), and Run Detail uses “RELEASE START,” “HOLD START,” “Technician mode,” and “Arcade manual” for evidence disclosure (`frontend/src/pages/RunDetail.tsx:388-406`). The original arcade PRD intentionally targets vibe coders (`docs/PRD-arcade-scorecard.md:20-45`), but the new target is a technical buyer deciding spend and deployment.

**Design consequence:** Retire arcade chrome from the primary interface. Preserve benchmark-season logic and plain-language score interpretation, but use literal terms: suite, score, cost/task, evidence details.

### 3.5 Models presents evidence before making a recommendation

The Models page provides strong raw material: suite selection, cost/capability scatter, sortable score and CI, category rates, cost, license, validity, and unbenchmarked catalog entries (`frontend/src/pages/Models.tsx:261-343`, `345-474`, `487-511`). However, it does not answer “which one should I use?” The first major visualization is an unlabeled scatter, then a wide table. Users must infer their own acceptable quality floor, category priorities, budget, and open/closed preference.

The table exposes nearly every metric at once—score, pass^k, optional calibration and robustness, composite, each category, cost, and validity (`frontend/src/pages/Models.tsx:345-394`). This is useful for research but not staged for a decision. The “new—not yet benchmarked” catalog receives a large card grid after the already long ranking, even though those entries cannot resolve the main decision (`frontend/src/pages/Models.tsx:487-511`).

**Design consequence:** Put a recommendation band and three role-based alternatives above the research table. Move unbenchmarked catalog coverage to a compact coverage drawer or Evidence section.

### 3.6 Mobile is technically responsive but not decision-optimized

The screenshots show the Models table clipped to rank, model, and score while category, cost, and validity—the fields needed to decide—sit off-screen. The implementation relies on horizontal overflow for the full table (`frontend/src/pages/Models.tsx:345-460`). The scatter retains a fixed 380px height and hover tooltip behavior (`frontend/src/pages/Models.tsx:298-341`), consuming a large portion of the mobile viewport without identifying points persistently.

Methodology tables also use horizontal overflow (`frontend/src/pages/Methodology.tsx:12-31`). In the mobile screenshot, some two-column tables become extremely narrow and others visibly clip content. The page remains a long stack of similar cards with no contents navigation or progressive disclosure (`frontend/src/pages/Methodology.tsx:91-298`).

**Design consequence:** On mobile, replace the research table with ranked decision rows/cards showing recommendation, model, fit, score with uncertainty, cost, and validity. Open a bottom sheet for categories and evidence. Convert methodology tables to definition lists or accordions.

### 3.7 Charts are visually quiet but not sufficiently explanatory or accessible

Chart points are anonymous until hover and the primary scatter is rendered as Recharts SVG with a tooltip (`frontend/src/pages/Models.tsx:305-340`). There is no persistent labeling of the recommended point, no keyboard interaction model, no text summary of outliers, and no chart-to-table selection state. The same pattern appears in Agents (`frontend/src/pages/Agents.tsx:221-274`) and Dashboard (`frontend/src/pages/Dashboard.tsx:320-425`).

**Design consequence:** Every chart needs a text conclusion, a highlighted selection, keyboard-operable point list or linked table, and a “view as table” equivalent. Default charts should show the frontier and only the most relevant alternatives, not every point with equal weight.

### 3.8 Cost is fragmented and can become stale

Models exposes measured cost per task. Agents exposes cost per task under a metaphor. The MoA calculator separately uses hardcoded model prices and hand-entered quality scores (`frontend/src/lib/moaCalculator.js:44-101`) even though the catalog stores provider prices and snapshot dates (`backend/app/data/known_models_seed.json:1-14`, representative entries throughout). The calculator’s decision rule is useful, but its recommendation is based on static presets and disconnected quality values (`frontend/src/pages/MoaCalculator.tsx:20-47`, `49-101`).

**Design consequence:** Create one scenario cost model fed by catalog pricing plus measured run cost. Show source and “priced as of” date. Label projections as estimates. Cost must scale to the user’s token/task volume and present daily/monthly totals, not only tiny unit prices.

### 3.9 Local and cloud cannot yet be compared as deployment choices

Hardware has reference-profile cards and a wide specs table (`frontend/src/pages/Hardware.tsx:7-35`, `76-142`). Compare only compares two legacy benchmark submissions and explicitly warns that rows are rarely comparable (`frontend/src/pages/Compare.tsx:45-70`). The current model leaderboard contract includes model capability, API cost, latency, categories, license, and validity (`frontend/src/api.ts:165-194`), while the hardware contract contains RAM/VRAM, bandwidth, TDP, MSRP, and form factor (`frontend/src/api.ts:39-54`). There is no model-to-hardware compatibility record and AgentRun has no reference-profile foreign key (`backend/app/models.py:132-179`).

**Design consequence:** Design a unified Setups experience now, but mark hardware fit as unavailable until the data contract supports it. Do not infer fit from model name. Add explicit compatibility and profile linkage in a later API phase.

### 3.10 Methodology contains the trust proof but asks too much of the reader

The methodology is unusually strong: executable graders, confidence intervals, private split, provenance, pinned decoding, contamination refusal, and no unsupported ordering claims (`frontend/src/pages/Methodology.tsx:40-89`, `152-295`). But it is presented as one long reference page. Its strongest buyer-facing claims—deterministic scoring, official vs dev validity, uncertainty, and no ranking without significance—are buried among implementation detail.

**Design consequence:** Split “How to trust this result” from the full methodology. Put a concise trust panel beside every recommendation and maintain a structured Evidence center for the full protocol.

### 3.11 Submit is a legacy operator workflow, not part of the buyer journey

Submit is explicitly labeled Legacy, not in main navigation, and focused on local throughput CLI/manual entry (`frontend/src/pages/Submit.tsx:172-179`). The manual form collects many technical fields but does not associate data with a reference profile or guide validation beyond inline errors (`frontend/src/pages/Submit.tsx:15-40`, `81-169`). Capability runs use a different publication path through `agentbench` and the API.

**Design consequence:** Move Submit under a “Contribute data” secondary area. Split local benchmark submission from capability-run publishing and make provenance requirements explicit.

### 3.12 State handling is reusable but too generic for a research product

The shared Skeleton, EmptyState, and ErrorState are clean (`frontend/src/components/ui.tsx:105-140`), but every error collapses to a generic centered card, and loading skeletons often mimic rows without preserving page context. Some secondary fetches fail silently—for example, new models and profiles become empty arrays (`frontend/src/pages/Models.tsx:142-155`; `frontend/src/pages/Hardware.tsx:43-51`).

**Design consequence:** Distinguish unavailable data from zero data, preserve the current comparison/recommendation shell while refreshing, and show data freshness and partial-failure notices inline.

---

## 4. Three radically different product directions considered

### Direction A — Research Workbench

A neutral, paper-like benchmark publication. The home page is a compact research abstract, the model table is central, methodology is first-class, and every result links to reproducibility receipts. Visual references: an academic data appendix, Our World in Data, and a restrained Carbon-style enterprise system.

**Strengths**

- Highest methodological credibility.
- Efficient for benchmark researchers and expert users.
- Natural home for confidence intervals, suite versions, and provenance.
- Lowest risk of decorative AI-slop.

**Weaknesses**

- Still asks buyers to synthesize the answer themselves.
- Can become a prettier leaderboard rather than a decision product.
- Local/cloud/MoA comparison remains conceptually fragmented.
- Premium value and monthly cost are secondary rather than central.

### Direction B — Guided Buyer

A question-first wizard: workload, deployment preference, budget, volume, latency, and privacy. It produces one recommended model/setup, two alternatives, and a plain-language explanation. Tables and methodology are secondary drill-downs.

**Strengths**

- Fastest path to “what should I use?”
- Excellent on mobile.
- Makes cost and premium uplift understandable.
- Can tailor language and avoid metric overload.

**Weaknesses**

- Risks feeling like a marketing recommender if evidence is not visible.
- Requires more explicit decision rules and missing fit data.
- Power users may find the wizard restrictive.
- A single-answer UI can overstate certainty where CIs overlap.

### Direction C — Value Terminal

A persistent decision workspace with a compact scenario bar at the top, a recommendation strip, a frontier chart, and a dense evidence table. Users can edit workload, budget, volume, deployment, and constraints without leaving the view. Compare is a tray shared across Models, Setups, and MoA. Visual references: premium financial research, pricing analytics, and restrained data terminals.

**Strengths**

- Combines immediate guidance with transparent evidence.
- Makes unit economics a first-class axis.
- Scales from novice defaults to expert inspection.
- Unifies cloud, local, and MoA without pretending their evidence is identical.
- Supports desktop density while recomposing cleanly on mobile.

**Weaknesses**

- Needs disciplined hierarchy to avoid becoming another dashboard.
- Requires a shared scenario model and stronger data contracts.
- More implementation effort than a visual reskin.
- Must keep controls compact and avoid Bloomberg cosplay.

### Synthesis and decision

Use **Direction C, Value Terminal**, with the question framing of Guided Buyer and the provenance discipline of Research Workbench.

- From Guided Buyer: a scenario bar, default workload templates, “why this wins,” and concrete monthly cost.
- From Research Workbench: official/dev distinction, suite/grader/snapshot metadata, CIs, evidence links, and no unsupported winner claims.
- From Value Terminal: persistent compare, frontier visualization, dense tables, and one coherent model for cloud/local/MoA choices.

This direction best serves a technical buyer without discarding the sophistication already present in the codebase.

---

## 5. Recommended information architecture

### Primary navigation

1. **Recommend** (`/`) — decision desk and saved/current scenario.
2. **Models** (`/models`) — research table and model detail.
3. **Setups** (`/setups`) — Cloud API, Local, and MoA configurations.
4. **Compare** (`/compare`) — persistent multi-item comparison.
5. **Evidence** (`/evidence`) — methodology, suites, coverage, and data freshness.

### Secondary navigation

- Cost planner (`/cost`) — also opens from any scenario.
- Contribute data (`/contribute/local`, `/contribute/capability`).
- API/docs.
- About.

### Route migration

| Current route | Recommended destination | Treatment |
|---|---|---|
| `/` | `/` Recommend | Replace mixed legacy dashboard with decision desk. |
| `/models` | `/models` | Keep route; redesign hierarchy. |
| `/agents` | `/setups?type=moa` | Redirect after transition; “MoA configurations” is a setup type. |
| `/moa-calculator` | `/cost?type=moa` | Fold into shared cost planner. |
| `/hardware` | `/setups?type=local` | Preserve hardware specs as local evidence. |
| `/compare` | `/compare` | Replace legacy-only pair compare with shared compare. |
| `/methodology` | `/evidence/methodology` | Keep redirect and deep links. |
| `/submit` | `/contribute/local` | Preserve legacy route via redirect. |
| `/benchmarks/:id` | `/evidence/local-runs/:id` | Keep compatibility redirect. |
| `/agents/runs/:runId` | `/models/:modelId/runs/:runId` or `/setups/moa/:runId` | Route by run type; retain old URLs as redirects. |

### App shell

- **Desktop:** 56px masthead; product wordmark left; primary text nav; scenario status and Compare tray count right. No decorative nav icons.
- **Tablet:** primary nav condenses; scenario opens in a sheet.
- **Mobile:** wordmark, current section, Compare count, menu. The current decision summary stays sticky below the masthead only after the user has changed defaults.
- **Footer:** data timestamp, active suite/grader, methodology link, API status, company attribution. Do not repeat a marketing tagline.

---

## 6. Core journeys

### Journey 1 — Choose a cloud model

1. User lands on Recommend.
2. Default scenario is visible and editable: **Coding agent · Cloud allowed · 10k input / 5k output · 100 tasks/day · balanced quality/cost**.
3. Recommendation strip shows:
   - **Recommended:** best non-dominated model that meets the workload floor.
   - **Lower cost:** cheapest statistically acceptable alternative.
   - **Higher confidence/premium:** highest-capability alternative, with incremental success and spend.
4. “Why this wins” states the rule in one sentence.
5. User opens model detail or adds options to Compare.
6. Evidence drawer shows suite, score/CI, category fit, validity, grader, snapshot, and pricing timestamp.

**Success condition:** The user can identify a default model and monthly spend in under 30 seconds without reading the full table.

### Journey 2 — Decide whether premium is worth it

1. User chooses a baseline and a premium model in Compare.
2. The header states the decision in literal terms:
   - estimated monthly cost delta;
   - measured success-rate delta;
   - confidence status: significant, indistinguishable, or unavailable;
   - cost per additional successful task.
3. Category deltas show where the premium model earns its uplift.
4. If intervals overlap or matched significance is unavailable, the UI says **“No demonstrated uplift on this suite”**, not “tie” without context.
5. User changes volume/token assumptions; cost changes, benchmark evidence does not.

**Success condition:** The buyer can defend or reject premium spend with a written, exportable conclusion.

### Journey 3 — Choose local versus cloud

1. User sets privacy/local preference, target model size, acceptable latency, and budget.
2. Setups shows separate evidence lanes:
   - **Cloud:** measured capability + catalog price + provider latency.
   - **Local:** compatibility + measured throughput/TTFT + hardware price/power.
   - **MoA:** measured pipeline capability + cost + latency.
3. If compatibility evidence is missing, the local lane says **“Fit not verified”** and explains what data is needed.
4. Total-cost view shows one-time hardware spend, amortization assumption, estimated monthly energy, and cloud/API monthly cost.
5. User compares break-even and operational trade-offs.

**Success condition:** The user can choose a deployment shape without confusing API model cost with hardware efficiency data.

### Journey 4 — Evaluate MoA against a single model

1. User opens Setups → MoA or follows “See orchestration options” from a model.
2. MoA entries are named configurations, not “multiplayer cabinets.”
3. Recommendation emphasizes whether the pipeline produces a measured uplift over the strongest included single model at matched/visible cost.
4. Cost per task, monthly cost, p50/p95 latency, pass rate/CI, and model composition are visible.
5. A failed value test is stated plainly: **“Costs 2.1× more; no demonstrated capability uplift.”**

### Journey 5 — Audit the evidence

1. Any recommendation opens an Evidence drawer.
2. The first level answers four questions: Is it official? What was tested? How uncertain is it? How fresh is it?
3. The second level links to run detail, category/task results, suite definition, methodology, and provenance.
4. Technician-grade details remain available but are labeled **Run diagnostics**, not hidden behind a game interaction.

### Journey 6 — Contribute a result

1. User selects Local throughput or Capability run.
2. The UI recommends the supported CLI/import path before manual entry.
3. Required provenance and validation are shown before submission.
4. Success state explains whether the result is pending, reference-only, or eligible for ranking.

---

## 7. Page specifications

## 7.1 Recommend / Decision Desk

### Desktop hierarchy

1. **Scenario bar** — single horizontal control group, not a hero card.
   - Workload: General, Coding, Tool use, Reasoning, Structured data, Custom.
   - Deployment: Any, Cloud, Local, MoA.
   - Priority: Balanced, Lowest cost, Highest reliability, Lowest latency.
   - Volume: compact “100 tasks/day” button opens cost assumptions.
   - Constraints: Open weights, max monthly cost, min context, privacy.
2. **Decision summary** — one sentence and timestamp.
   - “For coding at 100 tasks/day, **Model X** is the best measured value under **$120/month**.”
   - If evidence cannot support a winner: “Three models are statistically indistinguishable; choose by cost or deployment constraint.”
3. **Recommendation strip** — one primary result plus two alternatives.
4. **Value frontier** — compact chart linked to the shortlist.
5. **Research table** — filtered and sorted by scenario.
6. **Trust line** — official/dev status, suite, grader, snapshot, and data freshness.
7. **Legacy local evidence link** — only when relevant to the scenario.

### Recommendation card content

- Role: Recommended / Lower cost / Premium / Local option.
- Model or setup name.
- One-line reason.
- Workload score with 95% CI.
- Estimated cost/task and monthly cost.
- p50 latency when available.
- Validity and freshness.
- Actions: Add to compare, View evidence.

Avoid trophies, gems, lightning bolts, or “best” without a named rule.

## 7.2 Models

### Default view

- Compact title: **Model research**.
- Current scenario and suite visible in the filter row.
- Three segmented tabs: **Shortlist**, **All measured**, **Coverage gaps**.
- Shortlist is the default; All measured contains the full table; Coverage gaps replaces the current large “new models” card grid.

### Filters

- Search model/provider.
- Workload/category.
- Official only.
- License: Open/Closed.
- Max cost/task or monthly.
- Context floor.
- Suite.
- Freshness.

Filters must serialize to the URL and expose a **Clear all** action.

### Table columns

Default columns, in this order:

1. Compare checkbox.
2. Model.
3. Recommendation status/fit.
4. Workload score + CI.
5. Cost/task.
6. Monthly cost for active scenario.
7. Latency p50.
8. Validity.
9. Updated/snapshot.

Optional columns through a Columns menu:

- pass^k;
- composite;
- each category;
- calibration;
- robustness;
- context;
- license;
- prompt/completion price;
- suite/grader.

Keep rank only when a single, explicit sort rule is active. Do not imply a universal rank when the user has category or cost constraints.

### Row behavior

- Whole row is selectable; model name is the detail link.
- Add to Compare does not navigate.
- Selected rows remain highlighted across pagination/filtering.
- A row can expand one level for category evidence; full details use a route.
- Invalid/dev-only rows are not silently mixed with official rows; default filter is Official where official coverage exists.

## 7.3 Model detail

Header:

- Model name, provider, pinned ID/snapshot, license.
- Recommendation status under current scenario.
- Compare/add action.

Sections:

1. **Decision summary:** best for, not recommended for, cost at current volume.
2. **Capability:** overall and category scores, CI, pass^k, calibration/robustness when present.
3. **Economics:** prompt/output price, measured cost/task, projected monthly cost, price timestamp.
4. **Deployment:** cloud availability and verified local profile compatibility.
5. **Evidence:** official/dev, suite, grader, tasks×trials, run date, run detail.
6. **Alternatives:** cheaper acceptable, closest premium, local equivalent where evidence exists.

## 7.4 Setups

Use tabs, not separate visual themes:

- **Cloud API** — single models as provider configurations.
- **Local** — model + quantization + reference hardware profile.
- **MoA** — orchestrated configurations.

Every setup row uses the same top-level comparison vocabulary:

- success/capability;
- cost/task and monthly cost;
- latency;
- setup cost where applicable;
- privacy/control;
- evidence validity;
- fit status.

The Local tab must not imply capability was measured on the hardware run unless the run/profile link exists. Show two evidence columns if necessary: **model capability** and **local performance**.

## 7.5 Compare

Support two to four items. The page is a conclusion generator, not two spec cards.

Top section:

- Plain-language conclusion.
- Scenario assumptions.
- Confidence/significance status.
- Export/share link.

Comparison sections:

1. **Decision metrics:** expected successful tasks/month, monthly cost, cost per successful task, latency.
2. **Capability delta:** overall and workload categories, uncertainty.
3. **Economics:** unit prices, projected totals, premium uplift.
4. **Deployment:** context, license, local fit, privacy, setup cost.
5. **Evidence quality:** official/dev, suite, grader, freshness, missing data.

Do not normalize unrelated metrics into same-length bars without prominent units, as the legacy compare currently does (`frontend/src/pages/Compare.tsx:95-108`, `115-166`). Prefer aligned values and deltas.

## 7.6 Cost planner

Replace the MoA-only calculator with a shared scenario calculator.

Inputs:

- input/output tokens per task;
- tasks/day or tasks/month;
- working days/month;
- cache rate/discount only if supported;
- local amortization period and energy price when Local is selected;
- quality floor;
- latency ceiling;
- budget cap.

Outputs:

- cost/task;
- monthly cost;
- expected successful tasks/month (projection from measured success rate; label clearly);
- cost per successful task;
- premium increment;
- break-even month for local hardware;
- assumptions and pricing date.

Measured quality values must come from benchmark results, not hardcoded calculator constants. Catalog pricing must carry source and timestamp.

## 7.7 Evidence / Methodology

### Evidence landing page

Four concise sections:

1. **What MiniBench measures.**
2. **How results earn Official status.**
3. **How uncertainty and comparisons work.**
4. **Coverage and freshness.**

Then link to detailed pages:

- Suites and tasks.
- Graders.
- Contamination defenses.
- Statistical policy.
- Reference profiles.
- Model coverage.
- Release/change log.

### Methodology article behavior

- Sticky table of contents on desktop; select/accordion nav on mobile.
- Reading width 720–760px for prose.
- Tables transform into definition rows on narrow screens.
- Put equations in labeled figure blocks with a plain-language interpretation.
- Use inline links from every result to the relevant anchor.
- Preserve all current methodological content; reorganize rather than dilute it.

## 7.8 Contribute

Split into:

- **Local benchmark result:** CLI-first, manual fallback, reference-profile selection, validation preview.
- **Capability result:** artifact import/publish instructions, validity checks, run preview.

Before submit, show a compact eligibility checklist:

- required fields complete;
- source/profile pinned;
- valid suite/grader;
- no infra errors;
- no canary flags;
- official/dev status;
- duplicate check.

---

## 8. Visual system: “financial research in daylight”

### Overall character

- Light-first, cool neutral canvas.
- Flat or near-flat data surfaces.
- Sharp alignment; conservative 4–6px radii.
- One blue interactive accent.
- Green for favorable measured outcomes, amber for caution/estimated/dev, red for invalid/error only.
- Dark mode may follow later through tokens, but is not a separate themed product.
- No gradients, neon, scanlines, glowing shadows, decorative blobs, glass cards, or gamified terminology.

### Color tokens

| Token | Value | Use |
|---|---:|---|
| `--bg-canvas` | `#F4F6F8` | App background. |
| `--bg-surface` | `#FFFFFF` | Tables, controls, primary panels. |
| `--bg-subtle` | `#EEF1F4` | Alternate rows, selected groups, secondary bands. |
| `--ink-strong` | `#101820` | Headings, primary values. |
| `--ink` | `#273747` | Body and labels. |
| `--ink-muted` | `#667788` | Secondary metadata. |
| `--line` | `#D8E0E7` | Dividers and control borders. |
| `--line-strong` | `#AEBBC7` | Active structure. |
| `--accent` | `#0B5CAD` | Links, focus, selection, primary action. |
| `--accent-soft` | `#E8F1FA` | Selected row/surface. |
| `--positive` | `#147D55` | Favorable measured result. |
| `--positive-soft` | `#E7F4EE` | Favorable background. |
| `--caution` | `#9A6700` | Dev/estimated/stale/caution. |
| `--caution-soft` | `#FFF4D6` | Caution background. |
| `--critical` | `#B42318` | Invalid/error/destructive. |
| `--critical-soft` | `#FDECEA` | Error background. |
| `--focus` | `#005FCC` | 2px focus ring with 2px offset. |

All text/background pairs must meet WCAG 2.2 AA; body text target is 7:1 where practical.

### Typography

Use a system-friendly, distinctive technical family:

- **Primary:** IBM Plex Sans, fallback `Inter, Segoe UI, system-ui, sans-serif`.
- **Data/mono:** IBM Plex Mono, fallback `SFMono-Regular, Cascadia Code, monospace`.

Type scale:

| Role | Size / line-height | Weight |
|---|---|---|
| Page title | 30/36 desktop, 26/32 mobile | 500 |
| Section title | 20/28 | 600 |
| Panel title | 15/22 | 600 |
| Body | 15/22 | 400 |
| Table | 13/18 | 400/500 |
| Metadata | 12/16 | 400 |
| Data value | context-specific | 500, tabular nums |

Avoid 40–48px dashboard heroes for authenticated/product pages. Avoid all-caps except very short data labels; never use tracked uppercase as the default hierarchy device.

### Spacing and layout

- 4px base; primary rhythm 8/12/16/24/32/48.
- Desktop max width: 1440px; 24px gutters; tables may use full width.
- Page title to controls: 20–24px, not 40–48px.
- Panel padding: 16px dense, 20–24px narrative.
- Radius: 4px controls/tags, 6px panels, 0px data table body.
- Shadows only for true overlays (menus, popovers, sheets). Cards and tables use borders/background layers.

### Iconography

- Icons support unfamiliar actions only.
- No icon on every nav item.
- Use 16–18px stroke icons with text labels.
- Never use trophy/gem/arcade symbols as recommendation semantics.

### Motion

- 120–180ms state transitions for hover, selection, disclosure.
- No page-wide staggered entrance animation.
- Charts may animate only on explicit scenario changes and must respect reduced motion.
- Loading should not move completed content.

---

## 9. Component hierarchy

### Foundation

- `AppShell`
  - `Masthead`
  - `PrimaryNav`
  - `ScenarioStatus`
  - `CompareTrayButton`
  - `MobileNavSheet`
  - `DataFooter`
- `PageFrame`
  - `PageTitleRow`
  - `PageActions`
  - `InlineNotice`

### Decision system

- `ScenarioBar`
  - `WorkloadSelect`
  - `DeploymentSelect`
  - `PrioritySelect`
  - `VolumeButton`
  - `ConstraintChips`
  - `ResetScenario`
- `DecisionSummary`
  - `RecommendationSentence`
  - `AssumptionSummary`
  - `EvidenceQuality`
- `RecommendationStrip`
  - `RecommendationCard`
  - `ReasonLine`
  - `MetricPair`
  - `CompareAction`
- `CompareTray`
  - selected items;
  - remove/reorder;
  - Compare CTA.

### Data display

- `ResearchTable`
  - `TableToolbar`
  - `FilterPopover`
  - `ColumnChooser`
  - `SortableHeader`
  - `PinnedIdentityColumn`
  - `MetricCell`
  - `ScoreIntervalCell`
  - `ValidityCell`
  - `FreshnessCell`
  - `ExpandedEvidenceRow`
- `ValueFrontierChart`
  - `ChartSummary`
  - `ChartLegend`
  - `SelectedPointLabel`
  - `KeyboardPointList`
  - `ChartTooltip`
  - `ViewAsTable`
- `DeltaTable`
- `CategoryProfile`
- `AssumptionTable`

### Evidence and state

- `EvidenceDrawer`
  - `OfficialStatus`
  - `RunIdentity`
  - `SuiteSummary`
  - `UncertaintySummary`
  - `ProvenanceLinks`
- `DataState`
  - loading;
  - empty;
  - partial;
  - stale;
  - error;
  - unauthorized if introduced later.
- `FreshnessStamp`
- `MeasuredEstimatedLabel`

### Forms

- `Field`
- `NumericField` with unit suffix and formatting
- `SelectField`
- `ValidationSummary`
- `SubmitEligibilityChecklist`

The current shared `PageHeader`, `Card`, `Stat`, and `Badge` primitives should be decomposed rather than restyled wholesale. Their one-shape-for-every-page behavior is part of the current sameness (`frontend/src/components/ui.tsx:7-76`).

---

## 10. Tables and charts

### Table rules

- Use sticky header on tables taller than 8 rows.
- Pin model/setup identity on desktop when horizontally scrolling optional columns.
- Right-align numeric values; use tabular numerals.
- Put units in column headers, not repeated in every cell.
- Use em dash only for truly unavailable data; use **Not measured**, **Not applicable**, or **Estimate unavailable** when the reason matters.
- Sort state must be visible in text/icon and announced via `aria-sort`.
- Table row selection must be keyboard operable.
- Heatmaps require numeric text and a non-color interpretation.
- Do not assign universal rank after user constraints change; say “sorted by X.”
- Support CSV export for the current filtered set.

### Chart rules

#### Value frontier

- X: cost per task or monthly cost, toggleable.
- Y: active workload score.
- Show only valid comparable points.
- Draw the Pareto frontier as a line only when the filtered set is comparable.
- Label recommended, lower-cost, and premium points persistently.
- Dim unselected points; selecting a table row selects the point and vice versa.
- Provide a text summary: “Model A is the lowest-cost option above the 80% floor; Model B costs 2.4× more for +3.1 points.”
- Tooltips include model, score/CI, cost, validity, and snapshot.

#### Premium uplift

Use a slope/dumbbell or aligned delta table, not grouped bars:

- baseline score → premium score;
- CI overlap/significance state;
- baseline monthly cost → premium monthly cost;
- cost per additional successful task.

#### Category profile

Use a horizontal dot plot or compact bars with a shared 0–100 scale. Avoid radar charts. Show category sample size where available.

#### Local break-even

Use a simple cumulative-cost line with explicit assumptions and an annotated break-even month. If energy/utilization data is missing, do not draw a false-precision line.

### Chart accessibility

- Every figure has a title, conclusion, and accessible description.
- Provide a semantically equivalent data table.
- Keyboard users can move between named points and hear values.
- Focused/selected states use stroke and label, not color alone.
- Tooltips appear on focus and hover and are dismissible.
- No required drag gesture.

---

## 11. Empty, loading, partial, stale, and error states

### Loading

- Keep page title, scenario, filters, and table headers visible.
- Skeleton only the result region.
- Preserve previous results with a subtle “Updating…” status during scenario changes; do not blank the page.
- Announce loading completion in a polite live region.

### Empty — no matches

**Title:** “No measured options match these constraints”  
**Body:** Name the blocking filters.  
**Actions:** Relax budget, include dev results, clear license constraint.

### Empty — no benchmark coverage

**Title:** “This model is tracked but not yet measured”  
Show catalog price/context/snapshot as catalog data, label it separately, and link to coverage/contribution. Never place it in the ranked table.

### Partial data

Show the recommendation using available comparable fields only, plus an inline warning:

> “Capability and price are available; latency is missing for 3 of 8 options and was not used in this recommendation.”

A failed secondary request must not silently look like zero rows.

### Stale data

Use a caution label with date and impact:

> “Pricing snapshot is 45 days old. Monthly estimates may have changed.”

### Error

- Keep scenario and prior successful data visible when safe.
- State which source failed: model results, catalog pricing, hardware specs, or profiles.
- Retry only that source.
- Include a compact technical detail disclosure with status/request ID when available.

### Invalid comparison

> “These runs use different suites or grader versions and cannot support a winner claim.”

Offer to align the comparison or show descriptive values without ranking.

### Submission errors

- Inline errors connect with `aria-describedby`.
- Focus the validation summary after submit.
- Preserve entered values.
- Distinguish duplicate/rate-limit/validation/network errors and provide the next action.

---

## 12. Copy system

### Voice

- Direct, measured, technical, calm.
- Prefer verbs and conclusions over slogans.
- State assumptions before claims.
- Use “measured,” “estimated,” “official,” “dev,” “not comparable,” and “not available” consistently.
- Avoid hype, gaming language, and anthropomorphic benchmark language.

### Preferred copy

| Avoid | Use |
|---|---|
| “Solo Cabinet” | “Model benchmark” or suite name |
| “Multiplayer Cabinet” | “MoA configurations” |
| “$/quarter” | “Cost per task” |
| “Credits Rolling” | “Suite saturated” |
| “Boss Beaten” | “66% measured success” with optional interpretation |
| “Top score” | “Highest measured score on [suite]” |
| “Best value” | “Lowest cost above your [X]% quality floor” |
| “Premium” alone | “Higher-cost option” plus measured uplift |
| “Couldn’t load this” | “Model results are temporarily unavailable” |
| “New—not yet benchmarked” | “Coverage gaps” |
| “Technician mode” | “Run diagnostics” |
| “Arcade manual” | “Task results” |

### Recommendation grammar

Every recommendation sentence should contain:

- scenario;
- item;
- rule;
- cost basis;
- evidence qualifier.

Example:

> “For coding tasks at 100/day, Kimi K2.7 Code is the lowest-cost official result above an 80% success floor, estimated at $84/month on the current token assumptions.”

When evidence is weak:

> “Claude Sonnet 5 and GLM 5.2 are statistically indistinguishable on this suite. GLM is cheaper under the current pricing snapshot.”

---

## 13. Responsive behavior

### Breakpoints

- Small: `< 640px`
- Medium: `640–959px`
- Large: `960–1279px`
- Wide: `≥ 1280px`

### Mobile (`<640px`)

- Scenario bar becomes a compact summary button opening a full-height sheet.
- Recommendation cards stack; only the primary is expanded by default.
- Value frontier becomes a 260–300px chart with three labeled shortlist points, followed immediately by the text conclusion.
- Research table becomes `DecisionList` rows:
  - model;
  - recommendation/fit;
  - score + CI;
  - cost/month;
  - validity;
  - compare checkbox.
- Opening a row reveals categories and metadata in a bottom sheet.
- No horizontally clipped methodology tables; use definition lists/accordions.
- Sticky bottom Compare tray appears only with selections.
- Minimum touch target: 44×44px.
- Body text minimum: 15px; metadata minimum: 12px.

### Tablet (`640–959px`)

- Scenario controls wrap into two compact rows.
- Recommendation strip is 2+1 grid.
- Table shows identity, score, monthly cost, validity; optional columns scroll.
- Evidence drawer occupies 60–70% width.

### Desktop (`≥960px`)

- Scenario bar remains one line where possible.
- Recommendation and chart can share a 5/7 or 4/8 grid.
- Full research table uses sticky header and pinned identity.
- Evidence drawer is 420–480px.

### Wide (`≥1280px`)

- Increase table columns, not card width or hero size.
- Keep prose widths constrained.
- Avoid stretching charts to fill empty width; preserve readable aspect ratios.

---

## 14. Accessibility requirements

Target **WCAG 2.2 AA**.

1. One `h1` per page; headings follow content structure.
2. Add a skip link to main content.
3. All controls have persistent visible labels; do not rely on placeholders.
4. Focus order matches visual order; focus is never trapped outside modal/sheet patterns.
5. Focus ring is 2px and high contrast on every surface.
6. Use `aria-current` for navigation and `aria-sort` for sortable columns.
7. Icon-only buttons have names and 44px targets.
8. Badges with explanatory text cannot rely on the HTML `title` attribute; use visible copy or accessible popovers. The current badge/validity help is title-based (`frontend/src/components/ui.tsx:68-85`).
9. Status uses text/icon/shape in addition to color.
10. Charts have equivalent tables and keyboard navigation.
11. Hover states are duplicated on focus and touch.
12. Live regions announce data refresh, form errors, and compare-tray changes.
13. Reduced motion removes nonessential transitions/animations.
14. Tables do not force two-dimensional scrolling on mobile for primary decisions.
15. Numeric inputs expose units, bounds, and error guidance programmatically.
16. Use locale-aware numeric formatting while retaining exact values in accessible labels where rounding could mislead.
17. Confidence interval visuals include a textual interval and interpretation.
18. Do not call a result “winner” when the product’s statistical policy says it is indistinguishable.

---

## 15. Data and API requirements

### Can be built from current contracts

- Scenario-filtered model shortlist using category scores, pass rate/CI, pass^k, cost/task, latency, validity, license, and frontier status (`frontend/src/api.ts:165-194`).
- Cloud monthly cost from measured cost/task × volume, labeled as a projection.
- Catalog pricing/context/license/snapshot coverage (`frontend/src/api.ts:150-163`).
- MoA setup comparison using pass rate/CI, cost/task, latency, models, and suite (`frontend/src/api.ts:91-110`).
- Local hardware research from RAM/VRAM, bandwidth, TDP, MSRP, and reference profiles (`frontend/src/api.ts:39-54`, `196-209`).
- Evidence links to run detail and per-task results (`frontend/src/api.ts:112-148`).

### Required additive fields/endpoints for the full vision

#### Model/run identity and freshness

- Stable model catalog ID on leaderboard rows.
- `pricing_updated_at` and pricing source/provider route.
- `run_updated_at` or immutable run timestamp surfaced consistently.
- Explicit `reference_profile_key` on model and agent runs.
- `grader_version`, `seed/generator comparability ID`, and suite version in comparison responses.

#### Workload recommendation

- Category task counts and CI per category, not pass rate alone.
- Pairwise comparison/significance endpoint or published comparison matrix from `agentbench.compare`.
- Recommendation reason codes computed from a documented rule, or enough stable fields for a shared frontend rule module.

#### Local compatibility

- Model parameter count/architecture where known.
- Quantized weight size by supported quantization.
- Minimum/recommended RAM/VRAM.
- Verified model × reference-profile run link.
- Throughput, TTFT, context, power, engine, quantization for that link.
- Compatibility status: verified / estimated / unsupported / unknown.

#### Unified compare

Create a normalized comparison view model or endpoint with:

- `item_type`: cloud_model | local_setup | moa;
- stable identity;
- capability evidence reference;
- deployment evidence reference;
- unit cost;
- scenario projection inputs;
- latency;
- validity/freshness;
- missing-data reasons.

Do not force all data into one database table; normalize at the API/view-model boundary.

#### Cost model

- Price per input/output/cache token where supported.
- Currency and provider fees.
- Measured run tokens and cost.
- Local energy estimate inputs, clearly optional.
- Assumption version for shareable scenarios.

### Known schema inconsistency to resolve before relying on robustness

`AgentRunResponse` exposes `robustness_consistency` while model storage and leaderboard use `robustness_correct` (`backend/app/schemas.py:217-249`, `275-310`; `backend/app/models.py:177-179`). Align naming before building shared detail/compare components.

---

## 16. Implementation sequence

### Phase 0 — Product contract and measurement semantics

**Goal:** Prevent a visual redesign from encoding unsupported claims.

- Agree on the four primary questions and recommendation rule.
- Define measured vs estimated vs catalog-only states.
- Define comparability rules for shortlist and compare.
- Decide whether score tiers remain as optional interpretations.
- Specify current-data limitations for local compatibility.
- Align robustness naming.

**Deliverables:** decision-rule spec, comparison semantics, normalized frontend view models, copy glossary.

### Phase 1 — Foundations and shell

**Primary files later affected:**

- `frontend/src/index.css`
- `frontend/src/App.tsx`
- `frontend/src/components/ui.tsx`
- `frontend/src/components/chart.tsx`

Work:

- Replace arcade and Apple-light tokens with Value Terminal tokens.
- Build new shell/navigation/footer.
- Remove page-wide entrance animation.
- Add typography, focus, table, overlay, and state foundations.
- Introduce `MeasuredEstimatedLabel`, `FreshnessStamp`, and source-specific state components.

**Acceptance:** All current routes render in the new shell without neon/scanline theming or broken keyboard navigation.

### Phase 2 — Scenario and recommendation model

**Primary files/modules later affected:** new `scenario`, `recommendation`, and formatting modules; `api.ts` adapters.

Work:

- Define URL-serializable scenario state.
- Build workload/category mapping.
- Implement recommendation and alternative selection from current official comparable rows.
- Compute monthly projection from cost/task and volume.
- Add explicit “indistinguishable” handling.
- Unit-test all rules and missing-data behavior.

**Acceptance:** Given fixed entries and scenario, output is deterministic, explainable, and never calls incomparable results a winner.

### Phase 3 — Recommend and Models

**Primary files later affected:**

- `frontend/src/pages/Dashboard.tsx` (replace with Recommend)
- `frontend/src/pages/Models.tsx`
- new decision/table/chart components.

Work:

- Ship Scenario bar, Decision summary, Recommendation strip, linked frontier, and research table.
- Move catalog-only models to Coverage gaps.
- Add URL filters, compare selection, column chooser, and accessible chart equivalent.
- Build mobile DecisionList composition.

**Acceptance:** A user can answer “which cloud model and what monthly cost?” on desktop and mobile; all recommendation claims link to evidence.

### Phase 4 — Shared Compare and Cost planner

**Primary files later affected:**

- `frontend/src/pages/Compare.tsx`
- `frontend/src/pages/MoaCalculator.tsx`
- `frontend/src/lib/moaCalculator.js` (retire hardcoded quality/pricing path)

Work:

- Add persistent Compare tray.
- Build two-to-four item comparison conclusion and delta sections.
- Replace hardcoded MoA calculator data with current catalog/run adapters.
- Add scenario assumptions and shareable URL.

**Acceptance:** User can answer whether a premium option or MoA is worth its incremental monthly cost without metaphorical units.

### Phase 5 — Setups: MoA and Local

**Primary files later affected:**

- `frontend/src/pages/Agents.tsx`
- `frontend/src/pages/Hardware.tsx`
- `frontend/src/pages/BenchmarkDetail.tsx`
- `frontend/src/pages/RunDetail.tsx`
- backend schemas/endpoints for profile/compatibility linkage.

Work:

- Unify Cloud/Local/MoA under Setups tabs.
- Remove cabinet chrome and rename diagnostics/task results.
- Add local compatibility states and evidence lanes.
- Add break-even view only when sufficient data exists.

**Acceptance:** Local/cloud/MoA rows share comparison vocabulary while clearly distinguishing their evidence sources.

### Phase 6 — Evidence and contribution

**Primary files later affected:**

- `frontend/src/pages/Methodology.tsx`
- `frontend/src/pages/Submit.tsx`
- new Evidence routes.

Work:

- Reorganize methodology with TOC and deep links.
- Add evidence drawer hooks from recommendations/results.
- Split Local and Capability contribution flows.
- Add eligibility preview and partial/stale data states.

**Acceptance:** Every recommendation can be audited in two clicks; methodology is readable at 375px without clipped tables.

### Phase 7 — Quality gate

- Keyboard-only pass on all journeys.
- Screen reader pass on scenario, recommendations, table, compare, charts, and forms.
- 320/375/768/1024/1440 visual QA.
- Forced colors and 200% zoom.
- Reduced motion.
- Slow/partial/error API simulations.
- Copy review for unsupported causality or winner language.
- Performance budget: avoid rendering every unbenchmarked catalog card and every table column by default.

---

## 17. Acceptance criteria

### Product

- The default page produces a recommendation or an explicit “no defensible winner” state.
- Monthly cost is visible for the active scenario.
- Premium comparison shows incremental cost and measured uplift/confidence.
- Local, cloud, and MoA are understandable as deployment choices.
- Legacy data is accessible but does not dominate the primary journey.

### Visual

- No arcade/neon/scanline styling in primary product pages.
- No gradients or decorative hero art.
- No repeated four-stat-card default pattern.
- No page title larger than 30px desktop in the product shell.
- Data tables and recommendations establish hierarchy through alignment and typography.
- Cards/panels use borders and surface layers; shadows are reserved for overlays.

### Interaction

- Scenario and filters serialize to URL.
- Compare selections persist during navigation for the session.
- Charts and tables share selection.
- Mobile primary decisions require no horizontal scrolling.
- Loading preserves context and partial errors identify the failed source.

### Trust

- Official/dev, suite, grader, snapshot, and price freshness are available from every recommendation.
- Measured and estimated values are visibly distinct.
- Incomparable runs never yield a winner statement.
- CIs have textual equivalents.
- Catalog-only models never appear as ranked results.

### Accessibility

- WCAG 2.2 AA target met.
- All core journeys complete by keyboard.
- Charts have equivalent tables and point navigation.
- 44px mobile targets.
- 200% zoom without lost content or two-dimensional scrolling for core decisions.

---

## 18. First release recommendation

Do not start with a site-wide cosmetic reskin. Start with one vertical slice:

1. New shell and Value Terminal tokens.
2. Scenario bar using existing model leaderboard fields.
3. Recommendation + two alternatives.
4. Monthly cost projection.
5. Linked frontier and revised default Models table.
6. Evidence drawer with Official/dev, suite, grader, CI, run date, and price snapshot.
7. Mobile DecisionList.

This slice answers the first two buyer questions with existing data, demonstrates the new product direction, and creates the components required for premium compare and local/cloud setup work. The local-fit question should remain explicitly partial until compatibility/profile linkage exists; honesty about that limitation will build more trust than a visually complete but inferred answer.
