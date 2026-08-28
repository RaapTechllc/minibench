# Spec: OpenRouter Usage Board (Mode A)

Parent plan: `docs/PLAN-openrouter-usage-board.md`. ADR: `docs/adr/0002-openrouter-usage-board.md`. Glossary: `CONTEXT.md` § OpenRouter Usage Board.

## Problem Statement

A vibe coder picking a hosted model today has to bounce between OpenRouter rankings, pricing, and eval pages, then still guess. MiniBench already answers "which Mini PC?" and "which cabinet score?" but not "which OpenRouter model should I call for this task, budget, and latency — with a citable as-of?" Live completions would spend money and violate GATE-1. Scraping would violate GATE-1. A CORS `*` recommend that forwarded a bearer would leak the key.

## Solution

Poll four documented OpenRouter Data API GET paths on a cron, join them into a cached Usage Board, cite every number, and recommend by comparing that cache. Public board pages show best-by-$, best-by-task, and best-by-latency with deep-links. MCP + localhost REST expose `recommend?task=&budget=&max_latency_ms=`. No key in the repo, logs, or responses. CI and dog-food use a committed fixture when the key is missing.

## User Stories

1. As a vibe coder, I want today's cheapest OpenRouter model that still has official-eval and usage context, so that I can pick without opening five tabs.
2. As a vibe coder, I want the best model for a named task (code, data, agent, general) under a budget, so that I do not overpay for a coding session.
3. As a vibe coder, I want the fastest cited model that still fits my task and budget, so that interactive work does not stall.
4. As a vibe coder, I want every number stamped `as_of` with an OpenRouter CC BY 4.0 citation, so that I can trust I am not looking at stale or invented scores.
5. As a vibe coder, I want each row to deep-link the OpenRouter model page, so that I can confirm price and providers before I call.
6. As an agent, I want an MCP `recommend` tool over the cached board, so that I can pick a model without a live OpenRouter hop.
7. As a local operator, I want `GET /recommend?task=&budget=&max_latency_ms=` on localhost, so that I can dog-food the same compare the MCP uses.
8. As a CI runner without secrets, I want tests to use the committed fixture, so that the suite stays green offline.
9. As a repo owner, I want the poller to read `OPENROUTER_API_KEY` only from env or Actions secrets, so that a key never lands in git or a response body.
10. As a repo owner, I want recommend unbound from the CORS `*` FastAPI app, so that an unauthenticated browser cannot turn MiniBench into an OpenRouter proxy.
11. As a hardware-board user, I want the Mini PC leaderboard unchanged, so that Mode A does not disturb HEI or cabinets.
12. As a visitor on `/usage`, I want to switch between best-by-$, best-by-task, and best-by-latency, so that one board answers three compare questions.
13. As a visitor, I want a miss (no row fits) explained without a fake winner, so that empty filters are honest.
14. As an operator, I want a daily cron that polls the four paths when a secret exists and skips cleanly when it does not, so that CI never requires a key.
15. As a reviewer, I want fixture data never labelled live, so that dry-run / synthetic snapshots cannot be mistaken for today's rankings.
16. As a developer extending the client, I want a hard allowlist of the four GET paths, so that a future caller cannot quietly add `/chat/completions`.
17. As a developer, I want poll requests to send HTTP-Referer and X-Title, so that OpenRouter can attribute this app.
18. As a privacy-conscious operator, I want recommend to refuse a client-supplied API key, so that users cannot inject credentials into our process.
19. As a Mode B skeptic, I want Hermes / paid live bench left parked, so that this hop cannot grow into an $800 eval.
20. As a glossary reader, I want Usage Board terms distinct from Cabinet / Score / HEI, so that official-eval is not confused with MiniBench pass rate.

## Implementation Decisions

- Extend the agentbench OpenRouter seam (injectable GET transport, catalog parse) rather than adding a second HTTP stack or a new package.
- Poller writes one JSON board snapshot. Public board and recommend both read that snapshot (or the committed fixture).
- `meta.as_of` is the most conservative OpenRouter `as_of` among payloads that supplied one. Citation string is fixed: `Source: OpenRouter (openrouter.ai/rankings), as of {as_of}. CC BY 4.0.`
- Blended price is prompt + completion at a 1:3 in:out mix, per 1M tokens, used only for ranking.
- Latency is catalog latency if published, else official-eval `avg_latency_per_task_ms` if published. If `max_latency_ms` is set, rows with unknown latency are excluded.
- Recommend rank: highest task usage_share, then lowest blended price, then lowest latency. Structured miss if nothing remains.
- Main FastAPI serves **board reads only**. Recommend REST is a separate agentbench process bound to `127.0.0.1`. MCP is stdio JSON-RPC using the stdlib.
- GitHub Actions daily cron: live poll only when `OPENROUTER_API_KEY` is present; otherwise skip. CI unit tests never need the secret.
- No new Postgres table required for this hop; snapshot is a file. Do not rebuild hardware tables or the Mini PC board.
- Frontend Usage Board is a new route family, not a rewrite of `/compare` (legacy hardware) or `/models` (cabinets).

## Testing Decisions

A good test asserts external behaviour at a pre-agreed seam: given a fixture payload or snapshot, the public function returns a cited board, a cited pick, or an honest miss. It does not inspect private helpers or require a network.

Modules under test: Data API client, board join, recommend compare, MCP/REST adapters, public board read API, frontend ranking helpers.

Prior art: `agentbench/tests/test_tracker.py` + `fakes.py` (injectable transport, no key); `backend/tests/test_api.py` (FastAPI TestClient); `frontend/tests/moaCalculator.test.mjs` (pure ranking helper).

CI without a secret must stay green. Dog-food is a recommend call against the fixture that prints one cited pick.

## Out of Scope

Mode B, live completions, `/analytics`, scrape, Arena clone, new packages, new secrets in the repo, Folio, FabOps, billing, DNS, affiliate/P&L, Agent Cabinet #30/#36/#37/#43, Mini PC hardware board rebuild, GPQA/HLE/AA Index as a competing product.

## Further Notes

GATE-1 overrides in `docs/PLAN-openrouter-usage-board.md` are binding. If an implementation impulse violates them, stop.
