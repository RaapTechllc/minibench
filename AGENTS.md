# AGENTS.md

## Cursor Cloud specific instructions

Standard setup/test/run commands live in `README.md` (root) and `agentbench/README.md`.
The notes below only cover things that differ in the Cursor Cloud VM or are easy to get wrong.

### Services

| Service | How to run | Port |
|---------|-----------|------|
| PostgreSQL 16 | native apt install (no Docker) — see below | **5432** |
| Backend API (FastAPI) | `cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 3070` (creates tables + seeds on startup) | 3070 |
| Frontend (Vite dev) | `cd frontend && npm run dev` (proxies `/api` + `/health` → `:3070`) | 5173 |

### Non-obvious caveats

- **No Docker in this VM.** Ignore the `docker compose up` instructions in the README.
  PostgreSQL is installed natively. It is **not** auto-started — start it each session with:
  `sudo pg_ctlcluster 16 main start` (verify with `pg_isready` / `pg_lsclusters`).
- **Postgres runs on port 5432, not 5438.** The README/docker examples assume `5438`. Here the
  role `minibench` (password `minibench`, CREATEDB) and databases `minibench` + `minibench_test`
  already exist on `localhost:5432`. The committed `.env`, `backend/.env`, and `agentbench/.env`
  already point at `5432`.
- **Backend tests** need Postgres and default to port `5438`, so override it:
  `cd backend && MINIBENCH_TEST_PG_HOST=127.0.0.1 MINIBENCH_TEST_PG_PORT=5432 pytest`.
- **Per-component Python venvs** live at `backend/.venv`, `cli/.venv`, and `agentbench/.venv`.
  Activate the relevant one (or call its `.venv/bin/python`) before running Python commands; there
  is no shared/root venv. The startup update script (re)creates them and runs `npm ci` in `frontend/`.
- **agentbench must be run as a module from the repo root**, e.g.
  `python -m agentbench.run --config agentbench/presets/moa-v1.yaml --tasks agentbench/tasks/coding-v1.json --trials 2 --dry-run`.
  Running it from inside `agentbench/` fails with `No module named 'agentbench'`. Use `agentbench/.venv/bin/python`.
- Live agent/MoA runs and `--publish` need `OPENROUTER_API_KEY`; `--dry-run` works offline. The CLI
  `minibench run` needs a local Ollama daemon (not installed here) — use the API `POST /api/v1/submit`
  to create benchmark data without Ollama.
