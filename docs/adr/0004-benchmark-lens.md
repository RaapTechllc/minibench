# ADR 0004: Benchmark Lens republishes cited external claims with provenance tiers, never a composite

**Status:** proposed  
**Date:** 2026-09-14  
**Context:** [docs/research-agentic-benchmark-lens.md](../research-agentic-benchmark-lens.md). The Usage Board (ADR 0002/0003) reduces a model's external evaluation to one `eval_score`, taken first-wins from `intelligence_index`. That is the "proxy of a proxy" pattern the research rejects. Vendor launch tables mix self-reported, imported, and standardized numbers without distinction. MiniBench needs a place to show external agentic benchmarks side by side with cost and speed, flag benchmark-tuned results, and still refuse to invent a score of its own.

## Decision

1. **A Benchmark Lens is a republisher of cited external claims, not a measurement.** Every claim row carries `benchmark`, `revision`, `model`, `harness`, `effort`, `score`, `unit`, `source_kind`, `source_url`, `as_of`, and a citation string. Rows without a URL and `as_of` are rejected at load time.
2. **Claim provenance is a first-class field.** `source_kind ∈ {standardized, provisional, self-reported, imported}` as defined in the research notes. The UI never places rows of different tiers in one sorted column without the tier badge visible.
3. **Benchmarks carry signal-quality metadata.** A benchmark registry records axis, `information_gain`, `saturated`, `harness_sensitivity`, `contamination_resistance`, and the standardized leaderboard URL. Saturated benchmarks are shown collapsed and excluded from default views.
4. **Flags, not verdicts.** Benchmaxxing and genuine-capability signals are emitted as named flags with the numbers that triggered them. MiniBench never labels a model a cheater and never publishes a "benchmaxxing score".
5. **No public composite.** Any weighted "my index" is computed client-side from the user's chosen benchmarks and weights, is not persisted server-side, and is labelled as the user's own view. This extends the existing no-composite rule from Agent Cabinet.
6. **Data sources.** Phase 0 audits the live OpenRouter `/benchmarks` payload (already allowlisted). If it carries the needed per-benchmark fields, the Lens reads them through the existing poll. If not, the Lens reads an **operator-curated claims ledger**: a JSON file maintained by hand from the cited leaderboards, versioned like the fixture, with `as_of` per row. No scraping, no new API keys, no `/chat/completions`, no Mode B. Adding an automated fetch from any non-OpenRouter host is a separate ADR.
7. **Separation from MiniBench measurements.** Lens rows are never joined into Solo, Multiplayer, or Agent Cabinet scores, and Agent Cabinet receipts never cite Lens rows as evidence. The same lens *rules* (saturation, guardrail floor, abstention, comparability tiers) are applied to MiniBench's own suites through the existing `item_stats`, grading, and Agent Cabinet contracts.

## Rationale

- The research shows the strongest available evidence lives in provenance and variance, not in the score column. Encoding the tier and the information gain is the minimum needed to stop apples-to-oranges comparison.
- A curated ledger is honest about being manual. It mirrors how the Usage Board handles a missing key: a committed, labelled fixture rather than a fabricated live feed.
- The flags are computable from public numbers alone and do not require running any model.
- MiniBench's Agent Cabinet already implements the comparability ladder for its own runs (`comparability_receipt`); the Lens extends the same discipline to claims made by others.

## Consequences

- New module `agentbench/benchmark_lens.py`, registry and ledger fixtures under `agentbench/data/`, read-only backend routes under `/api/v1/lens`, and a `/lens` frontend route.
- `board._eval_and_latency` keeps its single `eval_score` for backwards compatibility but the Lens exposes the per-benchmark fields the join currently discards.
- CONTEXT.md gains the terms Benchmark Lens, Claim tier, Signal flag, Information gain, My index, Guardrail floor.
- If Phase 0 finds OpenRouter carries the data, item 6 collapses to "read the existing poll" and the ledger becomes a test fixture only.

## References

- ADR 0002, ADR 0003 (unchanged boundaries)
- `CONTEXT.md` — Anti-patterns: Saturation, Gaming
- `docs/research-woaibench.md` item 8 (client-side weights) and item 10 (`score_source` badges)
