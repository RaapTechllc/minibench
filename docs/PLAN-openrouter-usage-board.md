# Plan: Mode A OpenRouter Usage Board

**Date:** 2026-08-28  
**Status:** GATE-1 CLEAR — implement on this repo, one PR, do not merge  
**Flow:** setup-matt-pocock-skills (GitHub) → grill-with-docs → to-spec → to-tickets → implement (TDD) → code-review

This plan is posted **before product code**. Spec and tickets follow it.

---

## GATE-1 OVERRIDE (must stay in the plan; STOP if violated)

1. Mode A poll and recommend are GET-only on documented OpenRouter Data API: `/models`, `/datasets/rankings-daily`, `/benchmarks`, `/classifications/task`. Do not call `/chat/completions`, `/analytics`, or agentbench live runs. Mode B stays parked.
2. `OPENROUTER_API_KEY` from env or GitHub Actions secret only. Never commit, never log, never return in MCP/REST, never accept a client-supplied key. Dedicated Data-API-only key if OpenRouter allows; do not put the inference key on a public recommend server.
3. Recommend MCP/REST is read-only compare over cached/polled board data. If it live-calls OpenRouter, bind localhost or require auth. Do not hang an unauthenticated recommend on CORS `*` that forwards the bearer. Existing backend `cors_origins` includes `*`; do not bind recommend there.
4. No scrape. No Arena clone. Cite every number: `Source: OpenRouter (openrouter.ai/rankings), as of {as_of}. CC BY 4.0.` No new packages without stopping. No new secrets in the repo.

**STOP** if this plan grows into completions, scrape, Arena, a new package, Mode B, $800 spend, Folio, FabOps, billing, or DNS.

---

## What we are building

A **daily-fresh Usage Board** that joins four OpenRouter Data API payloads into one cited snapshot, plus a **recommend** compare (`task`, `budget`, `max_latency_ms`) over that snapshot.

User-facing question: *"Given today's OpenRouter usage, price, official eval, and task share — which model should I call?"*

Not: Mini PC hardware HEI, MiniBench cabinet pass rate, or a live MoA run.

## What already exists (reuse)

| Seam | Reuse |
|------|--------|
| GET `/models` + injectable transport | `agentbench/client.py` `list_models` / `HttpxTransport.get_json` |
| Catalog parse | `agentbench/tracker.py` `ModelInfo` |
| Offline fakes | `agentbench/tests/fakes.py` |
| Committed replay when no key | `agentbench/results/*.json` + `import_results` pattern |
| Public FastAPI + CORS `*` | `backend/app/main.py` — **board read only**, never recommend |
| Frontend pages + `node:test` helpers | `frontend/src/pages/*`, `frontend/src/lib/*` |
| CI jobs | `.github/workflows/ci.yml` — add fixture-only checks, no secret required |

## Architecture (conclusion)

```
                    ┌─────────────────────────────────────┐
  cron / CLI        │  agentbench poller (GET × 4)        │
  env key only      │  allowlisted paths, Referer+X-Title │
                    └──────────────┬──────────────────────┘
                                   │ writes
                                   ▼
                    ┌─────────────────────────────────────┐
                    │  board snapshot (JSON on disk)      │
                    │  + committed fixture for CI         │
                    └──────┬───────────────┬──────────────┘
           public read     │               │  localhost / stdio only
                           ▼               ▼
              GET /api/v1/openrouter/*    recommend MCP + REST
              (main FastAPI, CORS *)      (agentbench, 127.0.0.1)
              board + compare views       ?task=&budget=&max_latency_ms=
                           │
                           ▼
              frontend /usage/{cost,task,latency}
              deep-link openrouter.ai/{id}
```

### Poller

- New agentbench module, not a second HTTP client stack.
- Transport injected (same idea as `OpenAICompatClient`). Production transport GETs only the four allowlisted paths.
- Auth header from `os.environ["OPENROUTER_API_KEY"]` only. Missing key → do not call the network; load fixture.
- Send `HTTP-Referer` and `X-Title` on every Data API request.
- Join into one snapshot: models (price, optional catalog latency) + latest daily ranking row per permaslug (drop `other`) + official eval scores + task-share vectors.
- `meta.as_of` = most conservative OpenRouter `as_of` among payloads that supplied one.
- Cron: GitHub Actions scheduled workflow. If the secret is absent, the job **skips** the live poll and still passes (fixture path). Never commit the key.

### Board snapshot schema (decision, not a file path prescription)

Each row is a model that appears in at least one of the four feeds, keyed by OpenRouter id / permaslug:

- `id`, `name`, `openrouter_url`
- `prompt_price`, `completion_price`, `blended_per_million` (1:3 in:out mix)
- `daily_tokens`, `ranking_date` (latest day in the poll window)
- `eval_score`, `eval_source`, `eval_task` (best official eval we have for the row; omit if none)
- `latency_ms` (catalog latency if published; else official-eval `avg_latency_per_task_ms` if published; else omit — do not invent)
- `task_shares`: `{ tag: usage_share }` from classifications
- `citation`, `as_of`

### Recommend (pure function over a snapshot)

Inputs: `task` (classification tag or macro, e.g. `code` / `code:general_impl`), `budget` (USD per 1M blended tokens; omit = no price cap), `max_latency_ms` (omit = no latency cap).

Filter: drop rows missing the requested task share; drop rows over budget; drop rows over latency when a latency is known **and** a cap was set. Rows with unknown latency survive a latency cap only if we refuse to guess — **decision:** unknown latency is excluded when `max_latency_ms` is set (honest: we cannot certify it).

Rank: highest task `usage_share`, then lowest blended price, then lowest latency. Return the top row plus the citation. Empty filter → structured miss, not a fabricated pick.

### MCP + REST

- MCP: stdio JSON-RPC 2.0, one tool `recommend`. Stdlib only. Never prints the key.
- REST: `GET /recommend?task=&budget=&max_latency_ms=` on a **separate** agentbench process bound to `127.0.0.1`. Not mounted on `app.main:app`. No CORS `*`.
- Both call the same pure function and the same snapshot loader.

### Public board on the main API

`GET /api/v1/openrouter/board` and compare slices (`best-by-cost`, `best-by-task`, `best-by-latency`) serve the snapshot. No key. No live OpenRouter. Citation on every payload.

### Frontend

New Usage Board routes (names TBD at implement time; not the hardware `/compare`):

- best-by-$
- best-by-task
- best-by-latency

Each row deep-links to the OpenRouter model page. Footer citation uses `meta.as_of`. Do not rebuild the Mini PC hardware board.

### Tests / dog-food

- TDD at the seams below. CI without a secret uses the committed fixture.
- Dog-food: invoke recommend against the fixture (or a real cache if a key exists in the environment) and print one cited pick. Missing key is success-via-fixture, not failure.

## Seams under test (TDD)

Agreed before product code. Tests hit these public interfaces only.

1. **Data API client** — allowlist, GET-only, env key, Referer/X-Title, fixture fallback, never logs/returns the key.
2. **Board join** — four fixture payloads → snapshot rows + `meta.as_of` + citation.
3. **Recommend compare** — task / budget / latency filters and ranking over a snapshot.
4. **MCP + localhost REST** — recommend over cache; no key in the body; not imported by `app.main`.
5. **Public board API** — serves snapshot; 503/empty-with-citation if no snapshot (not fail-open numbers).
6. **Frontend ranking helpers** — sort/filter + citation string (same pattern as `moaCalculator.test.mjs`).

## Out of this hop

Mode B Hermes bench, $800 spend, GPQA/HLE/AA Index as a competing product, HTML scrapers, trading-platform / Shadow Arena, Folio, FabOps, secrets, billing, DNS, affiliate/P&L, Agent Cabinet #30 / #36 / #37 / #43, Mini PC hardware board rebuild, new pip/npm packages.

## Sequencing

1. This plan + ADR + glossary (this commit).
2. Spec issue + tracer-bullet tickets on GitHub.
3. Implement T1→T4 on this branch (TDD).
4. Dog-food + CI-equivalent checks.
5. Code review. Do not merge.
