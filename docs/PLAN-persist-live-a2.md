# Plan: persist-live A2 — honor OPENROUTER_BOARD_PATH

**Date:** 2026-08-28  
**Status:** GATE-1 CLEAR — implement on this repo, one PR against `main` @ `7ee753b` (#53), do not merge  
**Base:** `main` (already includes #53). Do not start from the #53 branch.  
**Flow:** setup-matt-pocock-skills (already on this repo: GitHub Issues) → grill-with-docs → to-spec → to-tickets → implement (TDD) → code-review  
**This commit is docs only.** No product code here.

---

## GATE-1 OVERRIDE (must stay in the plan; STOP and re-GATE-1 if violated)

1. GET-only documented OpenRouter Data API: `/models`, `/datasets/rankings-daily`, `/benchmarks`, `/classifications/task`. Do not call `/chat/completions`, `/analytics`, or agentbench live runs. Mode B stays parked.
2. `OPENROUTER_API_KEY` from env or GitHub Actions secret only. Never commit, never log, never return in MCP/REST, never accept a client-supplied key. Do not put the inference key on a public recommend server.
3. Recommend MCP/REST is read-only compare over cached/polled board data. If it live-calls OpenRouter, bind localhost or require auth. Do not hang an unauthenticated recommend on CORS `*` that forwards the bearer.
4. No scrape. No Arena clone. Cite every number: `Source: OpenRouter (openrouter.ai/rankings), as of {as_of}. CC BY 4.0.` No new packages without re-GATE-1. No new secrets in the repo.
5. Do not commit a live snapshot. `OPENROUTER_BOARD_PATH` must stay off the git tree (Actions artifact or runner/runtime path). Do not git-add the live file. Unset/missing path stays committed fixture and must not be labelled `live=true`.

**STOP** if this plan grows into `/chat/completions`, scrape, Arena, Mode B, a new package, a committed key, or a committed live snapshot.

---

## Setup (already done)

`setup-matt-pocock-skills` ran once on this repo during #53:

- Issue tracker: GitHub Issues on `RaapTechllc/minibench` — `docs/agents/issue-tracker.md`
- Domain docs: single-context (`CONTEXT.md` + `docs/adr/`) — `docs/agents/domain.md`
- `## Agent skills` block in `AGENTS.md`

Triage skill is not installed here; no `triage-labels.md`. This hop does not re-run setup.

---

## Grill (facts from the #53 seam, then settled decisions)

This is one session. Wayfinder is not needed. The frontier was the persistence question; Mode A compare, GET-only poll, and recommend-on-localhost are already decided in ADR 0002.

### What the code does today

| Seam | Today | Gap |
|------|--------|-----|
| Poll write | `--out` or `agentbench/data/openrouter_board.json` (gitignored) | Does not read `OPENROUTER_BOARD_PATH` |
| `load_board` / recommend | Explicit path, else that default file if present, else fixture join | Does not read `OPENROUTER_BOARD_PATH` |
| Public board | `backend/app/openrouter_board.py` **does** read `OPENROUTER_BOARD_PATH` | Unset → committed fixture (good). Set but **missing file → 503**, not fixture. |
| Daily workflow | Live poll writes `/tmp/board-live.json` and does not upload it | `/tmp` dies with the runner. Not a durable live board. |
| `.env.example` | Names the key, not the board path | Operators cannot wire the path from the example |

`/tmp` is a fine **throwaway** for a fixture schema smoke. It is not a durable live board. Postgres persist and a committed live snapshot were considered and rejected (GATE-1 #5; owner approach: option 1 only).

### Settled decisions (option 1 only)

1. **One env var, one disk file.** `OPENROUTER_BOARD_PATH` is the durable live Usage Board location. Poll writes it. Recommend and the public board read it when it is set **and the file exists**.
2. **Unset or missing → committed fixture, never live.** Do not 503. Do not invent numbers. Do not set `live=true` on fixture data.
3. **Not git, not Postgres, not `/tmp` as durable.** Live file stays off the tree. Workflow durability is an Actions **artifact** and/or a runner path in `OPENROUTER_BOARD_PATH`.
4. **Explicit `--out` / `snapshot_path=` still wins** for tests and local CLI. That is a caller override, not the public default.
5. **`live` is a property of the snapshot.** The poller labels a Data API join `live=true`. Readers do not upgrade a fixture to live. Citation always uses `meta.as_of`.
6. **No new packages, no new secrets, no new Data API paths.** Same board/poll/recommend seam.

### GATE-1 re-check of this plan

- No `/chat/completions`, `/analytics`, scrape, Arena, Mode B, Folio, FabOps, billing, DNS.
- No new pip/npm package. `actions/upload-artifact` is a workflow action, not a repo dependency.
- No committed key. `.env.example` may name `OPENROUTER_BOARD_PATH=` empty.
- No committed live snapshot.

---

## Architecture (this hop)

```
  poller (GET × 4, env key or fixture)
       │
       │ writes OPENROUTER_BOARD_PATH when set
       │ (explicit --out still allowed for tests / throwaway smokes)
       ▼
  joined JSON snapshot   ←── off git tree
       │
       ├── recommend (MCP / 127.0.0.1 REST / CLI)
       └── public GET /api/v1/openrouter/*
              │
              └── if path unset OR file missing:
                    committed fixture, live=false
```

Cron: fixture smoke may write a throwaway file. Live poll writes `OPENROUTER_BOARD_PATH` (job env, defaulting to the runner temp file) and **uploads that file as an artifact**. Do not treat `/tmp/board-live.json` as the durable destination.

---

## Seams under test (TDD)

Agreed before product code. Tests hit these public interfaces only.

1. **Path-honor (poll write)** — with the env set and no explicit `--out`, poll writes that path.
2. **Path-honor (readers)** — with the env set and the file present, `load_board` / recommend / public board serve that snapshot (including its `as_of` and `live` flag).
3. **Fixture-default** — env unset, or env set and file missing, serve the committed fixture and `live` is false.
4. **Workflow** — live step does not use `/tmp` as the durable live board; artifact and/or `OPENROUTER_BOARD_PATH` only.

Prior art: `agentbench/tests/test_poll_openrouter.py`, `test_board.py`, `test_recommend.py`; `backend/tests/test_openrouter_board.py` (HTTP) plus direct loader tests that do not need a live hop.

## Out of this hop

Mode B, $800 spend, Folio, FabOps, Mini PC hardware board rebuild, secrets, billing, DNS, `/chat/completions`, scrape, Arena, new packages, committed live snapshot, Postgres persist.

## Sequencing

1. This plan + spec + tickets + ADR + glossary (this commit). Publish spec/tickets to GitHub.
2. Failing path-honor + fixture-default tests (next commit).
3. Product code on the same board/poll/recommend/public/workflow seam.
4. CI-equivalent checks + code review. Do not merge.
