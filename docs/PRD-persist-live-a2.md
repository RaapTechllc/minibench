# Spec: persist-live A2 — durable Usage Board path

Parent plan: `docs/PLAN-persist-live-a2.md`. ADR: `docs/adr/0003-openrouter-board-path.md`. Glossary: `CONTEXT.md` § OpenRouter Usage Board. Builds on #48 / ADR 0002 (Mode A Usage Board).

## Problem Statement

Mode A already joins today's OpenRouter usage, price, official eval, and task share into a cited Usage Board. A live poll still writes that snapshot to `/tmp` (or a gitignored default). `/tmp` is not durable: the daily job's live file dies with the runner, and recommend / the public board cannot see it. Operators have no named **board path** to wire. If the public loader is pointed at a missing file, it 503s instead of serving the committed fixture. Fixture data must never be labelled live.

## Solution

Honor `OPENROUTER_BOARD_PATH` for poll write and for board / recommend / public read. When that path is set and the file exists, serve that snapshot and cite `meta.as_of`. When the path is unset or the file is missing, serve the committed fixture and do not label it live. The daily workflow keeps a live snapshot as an Actions artifact or at `OPENROUTER_BOARD_PATH` — not as a durable `/tmp` file. Do not commit a live snapshot. Do not persist into Postgres.

## User Stories

1. As an operator, I want a live poll to write the joined board to `OPENROUTER_BOARD_PATH`, so that today's snapshot survives the process that fetched it.
2. As an operator, I want recommend to read that path when it is set and the file exists, so that a dog-food pick uses today's board instead of `/tmp`.
3. As a visitor on the public Usage Board, I want the same path honored when it is set and the file exists, so that `/usage` and the API show the same cited snapshot recommend uses.
4. As a CI runner or a fresh clone, I want the committed fixture when the path is unset, so that the public default stays fixture until the path is wired.
5. As a reviewer, I want a missing board-path file to fall back to the fixture, so that a bad deploy path does not 503 or invent numbers.
6. As a reviewer, I want fixture fallback never labelled `live=true`, so that dry-run / synthetic data cannot be mistaken for today's rankings.
7. As a vibe coder, I want every number stamped `as_of` from `meta.as_of`, so that I can cite Source: OpenRouter (openrouter.ai/rankings), as of {as_of}. CC BY 4.0.
8. As a repo owner, I want the live file off the git tree, so that a poll cannot accidentally commit today's rankings.
9. As a repo owner, I want `.env.example` to name `OPENROUTER_BOARD_PATH=` empty, so that operators know the var without receiving a value or a snapshot.
10. As a workflow operator, I want the daily job to keep a live snapshot as an artifact or at `OPENROUTER_BOARD_PATH`, so that `/tmp` is not treated as durable.
11. As a local tester, I want an explicit `--out` / snapshot argument to still win, so that existing poll tests and throwaway smokes stay isolated.
12. As a privacy-conscious operator, I want no new secret and no key in MCP/REST, so that this hop cannot leak `OPENROUTER_API_KEY`.
13. As a GATE-1 reviewer, I want this hop to stay GET-only on the four Data API paths, so that persist-live cannot grow into completions or scrape.
14. As a hardware-board user, I want the Mini PC leaderboard unchanged, so that wiring a board path does not rebuild HEI.
15. As a Mode B skeptic, I want Hermes / paid live bench left parked, so that a path env var cannot become an $800 eval.

## Implementation Decisions

- Same Mode A seam: poller writes one JSON snapshot; recommend and the public board read it. No second HTTP stack. No Postgres table.
- `OPENROUTER_BOARD_PATH` is the implicit durable location. Explicit poll `--out` and an explicit loader argument remain caller overrides for tests and throwaway smokes.
- Reader rule: env set and file exists → read that file as-is (its `meta.live` and `meta.as_of` stand). Env unset or file missing → committed fixture, `live` false.
- Public loader must not 503 on a missing override path; that is a fixture-default, not a hard miss.
- Workflow: fixture smoke may use a throwaway file. Live poll writes `OPENROUTER_BOARD_PATH` (job-provided runner path) and uploads that file as an artifact. Do not treat `/tmp` as the durable live board.
- `.env.example` may name the var empty. Do not commit a value. Do not git-add the live file. Existing gitignore of the default snapshot file stays.
- Citation string and GET-only allowlist stay as ADR 0002. This hop does not add Data API paths, packages, or secrets.

## Testing Decisions

A good test asserts external behaviour at a pre-agreed seam: given an env path and a snapshot file (or their absence), poll writes the path, or a reader returns that snapshot, or a reader returns the committed fixture with `live` false and a citation that includes `meta.as_of`. It does not inspect private helpers or require a network.

Modules under test: poller write target, board/recommend loader, public board loader, workflow durable destination.

Prior art: `agentbench/tests/test_poll_openrouter.py`, `test_board.py`, `test_recommend.py`; backend Usage Board HTTP tests plus direct loader tests.

Red first: path-honor + fixture-default tests, then product code.

## Out of Scope

Mode B, $800 spend, Folio, FabOps, Mini PC hardware board rebuild, secrets, billing, DNS, `/chat/completions`, `/analytics`, scrape, Arena clone, new packages, committed live snapshot, Postgres persist, Agent Cabinet tickets.

## GATE-1 OVERRIDE

1. GET-only documented OpenRouter Data API: `/models`, `/datasets/rankings-daily`, `/benchmarks`, `/classifications/task`. Do not call `/chat/completions`, `/analytics`, or agentbench live runs. Mode B stays parked.
2. `OPENROUTER_API_KEY` from env or GitHub Actions secret only. Never commit, never log, never return in MCP/REST, never accept a client-supplied key.
3. Recommend MCP/REST is read-only compare over cached/polled board data. Do not bind recommend on the existing CORS `*` app.
4. No scrape. No Arena clone. Cite every number. No new packages without re-GATE-1. No new secrets in the repo.
5. Do not commit a live snapshot. Unset/missing path stays committed fixture and must not be labelled live.

## Further Notes

CI without a secret must stay green. Public default stays fixture until an operator wires `OPENROUTER_BOARD_PATH`.
