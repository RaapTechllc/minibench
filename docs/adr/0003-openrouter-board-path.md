# ADR 0003: Durable live Usage Board is OPENROUTER_BOARD_PATH, not /tmp or git

**Status:** accepted  
**Date:** 2026-08-28  
**Context:** GATE-1 CLEAR persist-live A2. Mode A (#53 / ADR 0002) already republishes a cited Usage Board. The remaining gap is where a *live* snapshot lives.

## Decision

The durable location of a live joined Usage Board is the **board path** (`OPENROUTER_BOARD_PATH`): a runtime or Actions-artifact path off the git tree.

- A live poll writes that path (explicit `--out` remains a caller override).
- Recommend and the public board read that path when it is set and the file exists.
- If the path is unset or the file is missing, serve the committed fixture and do not label it live.
- Do not treat `/tmp` as the durable live board.
- Do not persist the snapshot into Postgres.
- Do not commit a live snapshot.

Citation stays ADR 0002: every number carries `Source: OpenRouter (openrouter.ai/rankings), as of {as_of}. CC BY 4.0.` using `meta.as_of`.

## Rationale

Three alternatives were on the table:

1. **Honor `OPENROUTER_BOARD_PATH`** (this hop) — operators wire one env var; CI stays fixture; the live file never enters git.
2. **Commit the live snapshot** — durable and simple, but GATE-1 forbids representing a poll as a tracked artifact and would churn the tree daily.
3. **Postgres** — durable, but a new store for a file the poller already knows how to write; out of this hop.

`/tmp` is what the #53 workflow used for the live write. It is not durable: the runner deletes it. A 503 on a missing override path is also wrong: the public default is the fixture until the path is wired.

## Consequences

- Readers must share one rule: set + exists → that file; otherwise fixture, `live=false`.
- The daily workflow must upload an artifact and/or write `OPENROUTER_BOARD_PATH`. Throwaway fixture smokes may still use a temp file.
- `.gitignore` continues to exclude the default local snapshot file. Never git-add the live board.
- ADR 0002 (republisher, GET-only, recommend not on CORS `*`) is unchanged.

## References

- `CONTEXT.md` — board path, Usage Board, as_of
- ADR 0002 — OpenRouter Usage Board is a republisher
- `docs/PLAN-persist-live-a2.md`
