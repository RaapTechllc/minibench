# ADR 0002: OpenRouter Usage Board is a republisher, not a proxy

**Status:** accepted  
**Date:** 2026-08-28  
**Context:** GATE-1 CLEAR Mode A hop. Grilling session (grill-with-docs) against OpenRouter Data API docs and this repo's existing CORS / key / agentbench seams.

## Decision

MiniBench **republishes** OpenRouter's CC BY 4.0 Data API as a daily-fresh Usage Board. It does not call models, scrape HTML, or clone Arena.

### Allowed network

Poll, GET-only, these four documented paths on `https://openrouter.ai/api/v1`:

1. `/models` — catalog + pricing (and any latency the catalog already publishes)
2. `/datasets/rankings-daily` — daily token usage, top 50 + `other`
3. `/benchmarks` — official eval scores (AA / Design Arena / OpenRouter)
4. `/classifications/task` — task market share, window `7d`

Forbidden: `/chat/completions`, `/analytics`, HTML scrape, agentbench live runs, Mode B.

### Key handling

`OPENROUTER_API_KEY` comes from process env or a GitHub Actions secret. Never committed, never logged, never returned in MCP/REST, never accepted from a client. Dedicated Data-API-only key if OpenRouter allows; do not put the inference key on a public recommend server.

Poll requests send `HTTP-Referer` and `X-Title` so OpenRouter can attribute this app. Deep-links on the board go to `https://openrouter.ai/{model_id}`.

### Cache, not live recommend

A poller (CLI + daily cron) writes a joined **board snapshot** to disk. Recommend and the public board **read that snapshot**. If the key is missing, load the committed fixture / agentbench replay. Never fail-open with invented numbers. Never label fixture data as live.

### Recommend is not on the CORS `*` app

The existing FastAPI app sets `cors_origins` including `*`. Recommend MCP/REST therefore:

- lives in `agentbench` as a read-only compare over the cached board
- REST binds **localhost only** (separate process / separate ASGI app)
- MCP is stdio (no HTTP, no CORS)
- does not mount on `app.main:app`

The public Usage Board **read** endpoints on the main API may serve the cached snapshot (no key, no live OpenRouter call). That is republishing CC BY 4.0 data, not forwarding a bearer.

### No new packages

Reuse `httpx` (already an agentbench runtime dep) and FastAPI (already the backend). MCP is a tiny stdio JSON-RPC loop using the stdlib. Adding a package is a STOP.

### Citation

Every number in board, compare, and recommend responses includes:

```
Source: OpenRouter (openrouter.ai/rankings), as of {as_of}. CC BY 4.0.
```

`as_of` is the OpenRouter `meta.as_of` (or the most conservative `as_of` across the four payloads if they differ).

## Rationale

- OpenRouter already publishes usage, price, and official evals. Re-running completions would violate GATE-1 and spend money.
- The hardware Mini PC board answers a different question and stays untouched.
- `agentbench/tracker.py` + `client.py` already poll `/models` behind an injectable transport. Extend that seam; do not invent a second HTTP stack.
- CORS `*` on the main API is a hard stop for any endpoint that could grow a live OpenRouter hop.

## Consequences

- Cron + fixture path must both produce the same board schema.
- Recommend can be dog-fooded offline against the fixture.
- Mode B, scrape, Arena, Folio, FabOps, billing, DNS, and Agent Cabinet tickets stay out.

## References

- OpenRouter Data API: `/datasets/rankings-daily`, `/benchmarks`, `/classifications/task`, `/models`
- `CONTEXT.md` — Usage Board glossary
- `agentbench/tracker.py`, `agentbench/client.py`
- `backend/app/config.py` — `cors_origins` includes `*`
