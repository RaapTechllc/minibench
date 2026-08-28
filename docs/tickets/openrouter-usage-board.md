# Tickets: OpenRouter Usage Board (Mode A)

Parent spec: #48 · `docs/PRD-openrouter-usage-board.md` · plan: `docs/PLAN-openrouter-usage-board.md`

Work the **frontier**: any ticket whose blockers are all done.

---

## T1 — Data API client + fixture fallback — #49

**What to build:** A GET-only OpenRouter Data API client that can fetch the four allowlisted paths through an injectable transport, sends Referer + X-Title, reads the key only from env, and loads the committed fixture when the key is missing. Callers cannot aim it at `/chat/completions` or `/analytics`.

**Blocked by:** None — can start immediately.

- [x] Allowlist rejects any path outside the four documented GETs
- [x] Missing key does not open a socket; fixture loads
- [x] Key never appears in raised errors, logs, or returned payloads
- [x] Offline tests use a fake transport (tracker prior art)

## T2 — Board join + poller + daily cron — #50

**What to build:** Join the four payloads into one cited Usage Board snapshot and a CLI/cron poller that writes that snapshot. Cron skips cleanly when the Actions secret is absent.

**Blocked by:** T1

- [x] Snapshot rows carry price, daily usage, official eval, task shares, optional latency, `as_of`, citation
- [x] `other` ranking rows are not treated as a model
- [x] Fixture-labelled snapshots are never presented as live
- [x] Scheduled workflow does not fail the repo when no secret is set

## T3 — Recommend MCP + localhost REST + dog-food — #51

**What to build:** Read-only recommend over the cached/fixture board (`task`, `budget`, `max_latency_ms`) as an MCP tool and a localhost REST GET. Dog-food prints one real cited pick from the fixture.

**Blocked by:** T2

- [x] Same compare function serves MCP and REST
- [x] REST binds 127.0.0.1 and is not mounted on the CORS `*` app
- [x] Client-supplied key is rejected; response has no secret
- [x] Honest miss when no row fits; fixture dog-food shows a cited pick

## T4 — Public board API + Usage Board compare routes — #52

**What to build:** Public read of the snapshot (board + best-by-$ / best-by-task / best-by-latency) and frontend compare views with OpenRouter deep-links and the citation footer. Hardware `/compare` and cabinet `/models` stay as they are.

**Blocked by:** T2

- [x] Main API serves cache only — no live OpenRouter, no recommend
- [x] Every payload includes the citation + `as_of`
- [x] Frontend ranking helpers are unit-tested
- [x] Deep-links go to the OpenRouter model page

---

## Dependency graph

```
#49 ──┬── #50 ──┬── #51
      │         └── #52
```
