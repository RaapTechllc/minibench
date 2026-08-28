# Tickets: persist-live A2

Parent spec: #54 · `docs/PRD-persist-live-a2.md` · plan: `docs/PLAN-persist-live-a2.md`

Work the **frontier**: any ticket whose blockers are all done. This hop fits one session; both tickets are one vertical slice through the existing board/poll/recommend/public seam.

---

## T1 — Failing path-honor + fixture-default tests — #55

**What to build:** Red tests at the agreed seams: poll writes `OPENROUTER_BOARD_PATH` when set; readers serve that file when it exists; unset or missing file serves the committed fixture and is not live; every cited number carries `meta.as_of`.

**Blocked by:** None — can start immediately.

- [x] Poll-with-env writes the env path (no explicit `--out`)
- [x] Recommend / `load_board` read the env path when the file exists
- [x] Unset env or missing file → committed fixture, `live` is false
- [x] Public board loader matches the same rule (no 503 on a missing override)
- [x] Citation includes `as_of` from `meta.as_of`

## T2 — Honor OPENROUTER_BOARD_PATH on write, read, and cron — #56

**What to build:** Make the existing poller, board/recommend loader, public board, and daily workflow honor the board path. Live poll is durable via artifact or `OPENROUTER_BOARD_PATH`. Public default stays fixture until the path is wired. Do not commit a live snapshot.

**Blocked by:** T1 (red tests first).

- [x] With env set, poll writes that path; recommend can read it
- [x] With env unset or file missing, serve committed fixture and do not label it live
- [x] Workflow does not treat `/tmp` as the durable live board
- [x] `.env.example` names `OPENROUTER_BOARD_PATH=` empty; no value and no live file in git
- [x] GET-only. No key in repo/MCP. No new package.

---

## Dependency graph

```
#55 ── #56
```
