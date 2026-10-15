# Provider markup / serving efficiency (D1)

This is a **listed-price comparison** of public hosting offers for the same
open-weight models. It does not claim anything about a provider's own compute
spend or intent.

## What it reports

For each open-weight model with a `disclosed` parameter count:

- every curated host's listed input and output price
- a blended listed price under a labelled workload profile (default `minibench-1:3`)
- `$ / 1M tokens / active_params_b`
- the **baseline**: the lowest listed **standard-tier** blended price
- each host's **markup** = listed blended price / baseline
- the model's markup **range** `[min, max]` — always a range, never a single point

Rows with `quantization: unknown` stay in the table and are flagged. Priority,
fast, batch, and flex tiers are kept and flagged as non-standard; they do not
set the baseline (D4 is still open). A row older than 90 days is badged stale
and does not set the baseline; older than 180 days is dropped from the default
ranking and from the markup range (D11).

## What it is not

The figures are public list prices as of the row's `fetched_at` date. They are
not interpolated, not inferred from a cost curve, and not a statement about
provider cost. `estimated` or `unknown` parameter rows are refused.

## Ledgers

- `agentbench/data/param_ledger.json` — parameter counts with `params_source_url` and `as_of`
- `agentbench/data/endpoint_price_ledger.json` — listed prices with `price_source_url` and `fetched_at`

Both are curated files. There is no scrape and no new OpenRouter path.

## CLI

```bash
python -m agentbench.markup_index --check
python -m agentbench.markup_index --out /tmp/markup.json
```

`--check` exits nonzero if a ledger row is missing a https:// source URL or a
date, or if a null price is not marked `unlisted`. `--out` writes JSON that
must match `agentbench/data/markup_index.schema.json`. The process prints a
text table labelled `listed-price comparison, as of <date>`.
