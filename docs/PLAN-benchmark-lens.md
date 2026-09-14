# Plan: Benchmark Lens (handoff brief)

Implementation handoff for the concepts in
[docs/research-agentic-benchmark-lens.md](research-agentic-benchmark-lens.md),
governed by proposed [ADR 0004](adr/0004-benchmark-lens.md).

## Authority and boundary

- Base: `main` at `ce9c499` (PR #65), verified in sync with `origin/main` on 2026-09-14. No open PR branches.
- Parent workstream stays the Real-Work Agent Cabinet (#30). The Lens is additive and must not alter any measured cabinet result.
- Hard invariants apply: no credentials in git, no dry-run or synthetic data presented as live, no paid model calls, no publishing or deploying without owner authorization. Every phase below runs offline except Phase 0's optional GET-only OpenRouter audit, which uses the already-authorized Mode A poll.
- ADR 0004 must be accepted (status flipped by the owner) before Phase 2 ships anything user-visible. Phases 0 and 1 are pure library work and can proceed under the proposal.
- Owner decisions still open are listed at the end; do not guess them.

## Goal

Give a developer a per-benchmark, three-dimensional (score, `$ / task`, `time / task`) view of external agentic benchmarks with visible claim provenance, automatic flags for benchmark-tuned results and for genuinely efficient or well-calibrated models, and a private "my index" over the three or four benchmarks that match their work. Apply the same rules to MiniBench's own suites.

## Concept to code map

| Concept | Where it lives | New or extends |
|---|---|---|
| Benchmark registry (five seeds + signal quality) | `agentbench/data/benchmark_registry.json` | New |
| Claims ledger (cited rows with tier) | `agentbench/data/benchmark_claims_fixture.json`; runtime override `BENCHMARK_CLAIMS_PATH` following the ADR 0003 pattern | New |
| Loader, validation, signal computation | `agentbench/benchmark_lens.py` (pure functions, no I/O beyond file read) | New |
| Information gain / saturation | `benchmark_lens.information_gain`, reusing `stats.percentile`; policy constants next to `check_ceiling_items.DEFAULT_CEILING_THRESHOLD` | Extends |
| Pareto / 3D selection | `benchmark_lens.pareto_front(rows, axes=("score","cost_per_task","time_per_task"))` | New |
| Claim comparability | `benchmark_lens.claim_comparability(a, b)` mirroring `agent_cabinet.comparability_receipt` shape (`comparable`, `failing_fields`, `reasons`) | Mirrors |
| Read API | `backend/app/benchmark_lens_router.py` at `/api/v1/lens` | New |
| UI | `frontend/src/pages/BenchmarkLens.tsx` at `/lens`; helpers `frontend/src/lib/benchmarkLens.js` tested with `node --test` | New |
| Own-suite application | `item_stats`, `grading`, Agent Cabinet verify contract | Extends |
| Glossary | `CONTEXT.md` | Extends |

## Data model

### `benchmark_registry.json`

```json
{
  "registry_version": "1",
  "as_of": "2026-09-14",
  "benchmarks": [
    {
      "id": "terminal-bench-4.0",
      "name": "Terminal-Bench v4.0",
      "maintainer": "Laude Institute / Stanford; run by Artificial Analysis",
      "axis": "engineering",
      "measures": "66 hard terminal tasks; container, harness loop, final-state verifier",
      "unit": "percent",
      "standardized_leaderboard": "https://artificialanalysis.ai/evaluations/terminalbench-v4-0",
      "contamination_resistance": "rotated",
      "harness_sensitivity": "high",
      "harness_sensitivity_evidence": "Anthropic reports ~6 points from infrastructure alone",
      "saturation_policy": {"top_n": 10, "min_spread_points": 5}
    }
  ]
}
```

Axis enum: `engineering`, `cross-domain`, `alignment`, `truthfulness`, `long-horizon`. Contamination enum: `by-construction`, `rotated`, `public-static`, `unknown`. Harness sensitivity enum: `low`, `medium`, `high`, `unknown`.

Seeds: Terminal-Bench v4.0, APEX Agents, AutomationBench-AA, AA-Omniscience, DeepSWE v1.1. Also seed AA Long Context Retrieval and Terminal-Bench v2.1 so the saturation rule has something to demote in tests and in the UI.

### `benchmark_claims_fixture.json`

```json
{
  "live": false,
  "meta": {"source": "fixture", "as_of": "2026-09-14", "ledger_version": "1"},
  "rows": [
    {
      "benchmark_id": "aa-omniscience",
      "model": "gpt-6-astra",
      "model_label": "GPT-6 Astra (high)",
      "open_weights": false,
      "harness": "artificial-analysis",
      "effort": "high",
      "metrics": {"index": 44, "accuracy": null, "hallucination_rate": null},
      "cost_per_task_usd": null,
      "time_per_task_s": null,
      "tokens_per_task": null,
      "source_kind": "standardized",
      "source_url": "https://artificialanalysis.ai/evaluations/omniscience",
      "as_of": "2026-09-14",
      "citation": "Source: Artificial Analysis (artificialanalysis.ai/evaluations/omniscience), as of 2026-09-14."
    }
  ]
}
```

Rules enforced by the loader: `source_url` and `as_of` required; `source_kind` in the four-value enum; `metrics` keys must be declared by the benchmark's registry entry; `imported` rows must carry `imported_from_url`. Unknown numbers stay `null`, never zero. Every fixture value must be traceable to the cited page on the cited date; do not type numbers from memory.

### Signal output shape

```json
{
  "model": "gpt-6-astra",
  "flags": [
    {"kind": "efficiency-frontier", "benchmark_id": "deepswe-1.1", "evidence": {"score": 74.1, "tokens_per_task": 1.2e6, "peers_median_tokens": 3.1e6}, "citation": "..."},
    {"kind": "self-report-gap", "benchmark_id": "deepswe-1.1", "evidence": {"self_reported": 75.4, "standardized": null}, "note": "no standardized submission; gap not computable"}
  ]
}
```

Flag kinds are exactly the eleven named in research §3 (six benchmaxxing, five genuine-capability). A flag with insufficient data is emitted with `note` and no verdict rather than silently dropped, so the UI can show "not established".

## Phases and tickets

Each ticket names files, tests, and a deterministic acceptance check. Open them as GitHub issues per `docs/agents/issue-tracker.md` with `Part of #<lens-map-issue>` at the top; the map issue carries `wayfinder:map` and links ADR 0004.

### Phase 0: Source audit and decision (no product code)

**L0.1 Audit OpenRouter `/benchmarks` fields.** With the owner's existing `OPENROUTER_API_KEY`, run the Mode A poll (`python -m agentbench.poll_openrouter`) once and record every distinct key under `artificial-analysis` rows and every `benchmark_type` value. Write the finding to `docs/validation/openrouter-benchmarks-field-audit.md` with `as_of`. Decision rule: if per-benchmark fields for at least three of the five seeds exist, Phase 1 reads the poll; otherwise the curated ledger is primary. Acceptance: the audit file lists field names verbatim and states the decision. If no key is available in the implementing environment, record `NOT CONFIGURED` and proceed with the ledger; do not fabricate.

**L0.2 Accept ADR 0004.** Owner flips status. Acceptance: ADR status line reads `accepted` with a date.

### Phase 1: Library (offline, `agentbench/`)

**L1.1 Registry and ledger loaders.** `benchmark_lens.load_registry(path=None)`, `load_claims(path=None)` honoring `BENCHMARK_CLAIMS_PATH` exactly as `board.load_board` honors `OPENROUTER_BOARD_PATH` (set + exists → file; else fixture, `live=false`). Tests: `agentbench/tests/test_benchmark_lens.py` covers missing URL rejection, bad enum rejection, undeclared metric rejection, path fallback labelling.

**L1.2 Information gain and saturation.** `information_gain(rows, benchmark) -> {"spread": float, "n": int, "saturated": bool}` using the registry's `saturation_policy`. Tests: a flat-line fixture is `saturated=True`; the five seeds are not; fewer than `top_n` rows returns `saturated=None` with `note`.

**L1.3 Claim comparability.** `claim_comparability(a, b)` returns `comparable`, `failing_fields`, `reasons` over `benchmark_id`, `revision`, `harness`, `effort`, `source_kind`. Reason strings follow the Agent Cabinet convention (`harness_mismatch`, `effort_undisclosed`, `tier_mismatch`). Tests: standardized vs self-reported is never comparable; two standardized rows with different `effort` are `provisional`.

**L1.4 Pareto front.** `pareto_front(rows, maximize=("score",), minimize=("cost_per_task_usd","time_per_task_s"))`; rows with `null` on a requested axis are excluded and reported. Tests: hand-built three-point front; null exclusion is reported not silent.

**L1.5 Signal flags.** `signals(registry, claims) -> list[ModelSignals]` implementing all eleven flag kinds with the computations in research §3. Each flag carries `evidence` and `citation`. Tests: one synthetic scenario per flag, plus a "not established" scenario per flag where data is missing.

**L1.6 CLI.** `python -m agentbench.benchmark_lens --registry ... --claims ... --out /tmp/lens.json` prints a table and writes JSON; `--check` exits non-zero on loader violations, for CI. Acceptance: the command runs against committed fixtures in CI with no network.

### Phase 2: Backend (read-only)

**L2.1 Router.** `backend/app/benchmark_lens_router.py` mounted at `/api/v1/lens`: `GET /registry`, `GET /claims?benchmark=&tier=&open_weights=`, `GET /signals?model=`, `GET /front?benchmark=&x=cost_per_task_usd&y=score`. Responses always include `meta.live`, `meta.source`, `meta.as_of`. No POST. Tests in `backend/tests/test_benchmark_lens_api.py` using the existing `client` fixture; no Postgres tables are added in this phase, so the router reads files only.

**L2.2 No composite guard.** A test asserts no route returns a field named `composite`, `overall`, or `index_score` computed by MiniBench. Registry rows may still carry a third party's index under its own name (`aa_intelligence_index`) with citation.

### Phase 3: Frontend

**L3.1 `/lens` route and page.** Sections: benchmark cards grouped by axis (saturated ones collapsed with the spread shown), a claims table with the tier badge always visible (reuse the Usage Board `Badge` pattern for `Live poll` / `Fixture / cache`), a Recharts scatter of score vs `$ / task` with the Pareto front highlighted and a toggle to swap the x axis to `time / task`, and a model drawer listing flags with evidence and citations.

**L3.2 "My index" panel.** Pick three or four benchmarks, set weights with sliders, see a ranked list computed in `frontend/src/lib/benchmarkLens.js`. Persist only in `localStorage`. Label: "Your index, computed in your browser. Not a MiniBench score." Tests: `frontend/tests/benchmarkLens.test.mjs` covers weighting, tier filtering (default excludes `imported`), and saturated exclusion.

**L3.3 Methodology page.** Add a Benchmark Lens section to `/methodology` explaining tiers, flags, and why there is no composite. Link the research note.

### Phase 4: Apply the lens to MiniBench's own suites

**L4.1 Suite-level information gain.** Extend `item_stats.audit` output with a `suite` block: spread of model pass rates, count of `ceiling` items, and a `saturated` boolean using the same policy constant shape. Surface in Technician mode. Tests extend `test_item_stats.py`.

**L4.2 Abstention with zero penalty.** Add a `not_attempted` outcome to the `calibration` category graders and compute an Omniscience-style `knowledge_index = (correct − incorrect) / n` and `hallucination_rate = incorrect / (incorrect + partial + not_attempted)` in `run.summarize`. Keep both axis-only (excluded from the binary pass pool, as `calibration` already is). Tests: a model that abstains on everything scores 0 index and 0 hallucination; a model that guesses everything wrong scores −1 and 1.

**L4.3 Guardrail floor in Agent Cabinet.** Add `guardrail_violations: int` and `forbidden_actions: list[str]` to the verify result contract; `clean_completion` becomes the headline metric and `completion_any` is kept in Technician mode so the flip is visible. Add `guardrail_violations` to `publication_receipt` refuse reasons when the manifest declares forbidden actions and the artifact omits the counter. Tests extend `test_agent_cabinet_gates.py`; a fixture with one violation shows `clean_completion < completion_any`.

**L4.4 Harness dispersion for compatible pairs.** Where two Agent Cabinet runs differ only in `harness` (already a `CHANGED_VARIABLE_CANDIDATES` value), the compare endpoint reports the spread as `harness_dispersion_points`. No new data; presentation only.

### Phase 5: Documentation and glossary

**L5.1 CONTEXT.md terms.** Benchmark Lens, Claim tier, Signal flag, Information gain, My index, Guardrail floor, Abstention. Add "Composite index" to the anti-patterns table with response "per-benchmark view plus client-side my-index".

**L5.2 PROJECT-STATUS.** Add the Lens as an additive surface row in the evidence table with its limits ("republishes cited claims; not a MiniBench measurement").

## Verification per phase

Run the CI-equivalent checks from `AGENTS.md` after each phase:

```bash
cd agentbench && pytest -q
cd backend && pytest
cd frontend && npm run lint && npm test && npm run build
python -m agentbench.run --config agentbench/presets/moa-v1.yaml --tasks agentbench/tasks/coding-v1.json --trials 2 --dry-run --out /tmp/dryrun.json
python -m agentbench.benchmark_lens --check   # from L1.6 onward
git diff --check
```

Backend tests need PostgreSQL; set `MINIBENCH_TEST_PG_HOST` / `MINIBENCH_TEST_PG_PORT` when not on the Docker default 5438.

## Guardrails for the implementer

- Never type a benchmark number into a fixture without the URL and date it came from. If a value cannot be traced, leave it `null`.
- Never present a `self-reported` or `imported` row in the same sorted column as `standardized` rows without the tier badge.
- Never compute or store a server-side composite. "My index" lives in the browser.
- Never call any model, any non-OpenRouter API, or any scraper. The only network path is the existing Mode A GET poll.
- Never relabel the fixture ledger as live; follow the ADR 0003 path rule.
- Never change a measured cabinet number or an existing receipt's semantics; Phase 4 adds fields and views only.
- Flags are named signals with evidence. Copy must say "signal" or "flag", never "cheating" or "benchmaxxed".

## Sequencing and effort shape

Phase 1 is the bulk of the logic and is self-contained pure Python with fixtures; it can be built and fully tested before any UI exists. Phase 2 is thin. Phase 3 is the largest UI slice but reuses the Usage Board and Agent Cabinet Technician patterns. Phase 4 touches grading and Agent Cabinet contracts and should be reviewed against `docs/operators/agent-cabinet.md`; L4.3 is the only change with receipt implications. Phases 1 through 3 can land as one PR each; Phase 4 tickets should be separate PRs.

## Owner decisions needed

1. Accept ADR 0004 (or amend item 6 if you prefer to wait for the OpenRouter field audit before allowing a curated ledger at all).
2. Confirm the five seed benchmarks, or substitute (for example swap APEX Agents for GDPval-AA v2 if expert-authored finance/law tasks are not your audience).
3. Confirm the default saturation policy (top-10 spread under 5 points) or set another constant.
4. Whether "My index" defaults should include `self-reported` rows (plan default: standardized and provisional only).
5. Whether Phase 4.3's guardrail floor should refuse publication when a manifest declares forbidden actions but the artifact omits the counter (plan default: refuse).
