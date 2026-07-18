# Issue #34 environment preflight receipt

**Timestamp:** 2026-07-16 23:07:27 CDT  
**Repository:** `RaapTechllc/minibench`  
**Branch/worktree:** `codex/issue-34-generated-repository-repair` in `/Users/timraap/Projects/minibench-worktrees/issue-34-generated-repository-repair`

## Purpose

Restore the repository-native component environments that blocked Archon run `8fb49f16f9cc63c9d3fb92ce7ebab548`, without entering implementation or starting another production workflow.

## Result

- The host default `python3` is Python 3.13.1. Installing the pinned backend dependencies there failed while compiling `asyncpg` and `psycopg2-binary`; those pinned versions are incompatible with Python 3.13 on this host.
- Recreated the three ignored, worktree-local virtual environments with installed Python 3.12 and the repository-declared dependency files:
  - `backend/.venv`: `backend/requirements.txt` + `backend/requirements-dev.txt`
  - `cli/.venv`: editable `cli` package + `pytest`
  - `agentbench/.venv`: `agentbench/requirements.txt` + `agentbench/requirements-dev.txt`
- No tracked source file, other worktree, stash, service, credential, or production run was altered by environment setup.

## Deterministic evidence

```text
PRESENT agentbench/.venv/bin/python
PRESENT backend/.venv/bin/pytest
PRESENT cli/.venv/bin/pytest
BACKEND_IMPORT_OK
CLI_IMPORT_OK
AGENTBENCH_IMPORT_OK
31 passed in 1.85s
```

Commands:

```bash
agentbench/.venv/bin/python -m pytest agentbench/tests/test_agent_tasks.py -q
backend/.venv/bin/python -c 'import asyncpg, fastapi'
cli/.venv/bin/python -c 'import pytest'
agentbench/.venv/bin/python -c 'import pytest, yaml'
git diff --check
git status --short --branch
git stash list
```

`git diff --check` passed. The only untracked paths remain the prior run artifacts `.archon/` and `.omx/`. The stash list remains empty.

## Dispatch readiness and stop condition

The missing-environment blocker is cleared. Stop here after committing this receipt; do not dispatch in the same cycle. Before redispatch, recheck the sole production slot and verify the detached log resolves only to OpenAI Codex/GPT-5.5 or newer.
