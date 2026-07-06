# MiniBench Arena Dashboard Research + Implementation Notes

Generated: 2026-07-04 CT  
Repo audited: `/Users/timraap/projects/minibench`  
Branch: `e2e-verify-jul4`

## Executive conclusion

Kyle's diagnosis is right: the shipped `/` dashboard was still primarily a **hardware throughput dashboard**. It showed local benchmark submissions, memory bandwidth, HEI, and hardware tables. The repo had a separate `/agents` page and backend agent-run API, but the public landing page did not present MiniBench as a model arena / LM Arena competitor.

I updated the product direction in code by making the home dashboard **Arena-first**:

- model catalog cards for frontier LLM/image models,
- task-specific tabs: overall, agentic coding, image/design, long-running, research,
- anonymous vote buttons per model/task,
- source/reference cards for LMArena, Artificial Analysis, LiveBench, SWE-bench,
- hardware runs moved into a secondary infrastructure layer.

## Local project audit

### What existed before this pass

| Area | Status found | Gap vs target |
|---|---|---|
| `/` Dashboard | Hardware-only: t/s, quality, bandwidth regression, Pareto frontier over local hardware submissions | Wrong default experience for an LM Arena-style site |
| `/leaderboard` | Hardware leaderboard by HEI / tokens/sec / bandwidth | Useful, but should be secondary |
| `/agents` | Agent run leaderboard with pass rate, cost/task, Pareto frontier | Good start, but isolated from home page and no public voting |
| Backend | Hardware tables + agent run tables | Missing model arena catalog and votes |
| Data ingestion | Seeded hardware specs and local model quality table | Missing external LLM leaderboard/source model layer |
| Voting | None | Core requirement missing |

### Files changed

| File | Change |
|---|---|
| `backend/app/models.py` | Added `ArenaModel` and `ArenaVote` tables |
| `backend/app/schemas.py` | Added arena model/vote response schemas |
| `backend/app/arena_router.py` | New `/api/v1/arena/models` and `/api/v1/arena/votes` router |
| `backend/app/main.py` | Registered arena router |
| `backend/app/seed.py` | Added initial arena model catalog seed data |
| `backend/tests/test_arena_api.py` | Added API tests for seeded models, filtering, vote de-dupe |
| `frontend/src/api.ts` | Added Arena API types + client methods |
| `frontend/src/pages/Dashboard.tsx` | Rebuilt home dashboard into Arena-first experience |

## Reference sites and patterns to copy

### 1. LMArena / Chatbot Arena

Source: <https://lmarena.ai/leaderboard> and HF mirror/search result for Chatbot Arena.  
Relevant pattern: blind human preference voting over model outputs, leaderboard rank/Elo, domain-specific arenas including text and image.

**MiniBench implication:**
MiniBench needs voting as a first-class object, not a bolt-on. The current implementation starts with simple per-task model votes. Next step should be pairwise prompt battles with hidden model identities, then Elo/Bradley-Terry scoring.

### 2. Artificial Analysis

Source: <https://artificialanalysis.ai/>  
Relevant pattern: puts model quality, speed, cost per task, token pricing, and context window into the same decision surface.

**MiniBench implication:**
MiniBench should not show only “best model.” It should show **best model for task × speed × cost × context × local hardware feasibility**. I added those fields to the arena model schema: `intelligence_index`, `output_speed_tps`, `cost_per_million_tokens`, `context_window`.

### 3. LiveBench

Source: <https://livebench.ai/>  
Relevant pattern: objective contamination-resistant benchmark suites for LLMs.

**MiniBench implication:**
User votes are necessary, but insufficient. The product should pair votes with objective benchmark tracks so the leaderboard is not just popularity/brand sentiment.

### 4. SWE-bench / Terminal-Bench style agent benchmarks

Source: <https://swebench.com/>  
Relevant pattern: agentic coding should be measured by completed executable work, not vibe-based chat answers.

**MiniBench implication:**
The existing `agentbench/` module is directionally right: executable graders, pass rate, pass^k, cost/task, latency. It needs to become visible on the home page and integrated with model profiles.

## Product architecture recommendation

MiniBench should become a **3-layer benchmark graph**:

1. **Model layer** — global LLM/image/model metadata from sources like LMArena, Artificial Analysis, LiveBench, OpenRouter, provider APIs.
2. **Task layer** — user preference votes and objective task suites: coding, image, long-running, research, writing, tool use.
3. **Hardware layer** — local inference throughput, HEI, price/perf, memory bandwidth, watts/token.

The differentiator is not “another leaderboard.” It is: **which model should I use for this job, and can I run it efficiently on my hardware or should I call an API?**

## API surface added

### `GET /api/v1/arena/models?task=agentic_coding`

Returns arena model rows filtered by task tag, including vote counts.

Key fields:

- `model_id`
- `display_name`
- `provider`
- `modality`
- `task_tags`
- `arena_rank`
- `arena_score`
- `intelligence_index`
- `output_speed_tps`
- `cost_per_million_tokens`
- `context_window`
- `strengths`
- `source_name`
- `source_url`
- `vote_count`

### `POST /api/v1/arena/votes`

Payload:

```json
{ "task": "agentic_coding", "model_id": "openai/gpt-5.5" }
```

Behavior:

- validates model exists,
- validates model is listed for the task,
- hashes client IP,
- de-dupes one vote per `task + model_id + ip_hash`,
- returns updated vote count.

## Important caveat about seed data

The initial model catalog is **reference-inspired seed data**, not a live scrape. The schema and UI now support the product direction, but the next production step is to replace seeded rows with scheduled ingestion from:

- LMArena leaderboard exports/pages,
- Artificial Analysis model/provider data,
- LiveBench task scores,
- OpenRouter/provider model catalogs,
- MiniBench's own `agentbench` published runs.

## Verification run

### Frontend

Command:

```bash
cd frontend && npm run lint && npm run build
```

Result:

- ESLint passed.
- TypeScript compile passed.
- Vite production build passed.
- Warning only: main chunk >500 KB, existing app-level code-splitting issue.

### Backend

Command:

```bash
cd backend && ./.venv/bin/python -m py_compile app/models.py app/schemas.py app/arena_router.py app/main.py app/seed.py
cd backend && ./.venv/bin/python - <<'PY'
from app.main import app
print(sorted(r.path for r in app.routes if '/arena' in r.path))
PY
```

Result:

```text
routes ['/api/v1/arena/models', '/api/v1/arena/votes']
```

### Backend tests

Command attempted:

```bash
cd backend && ./.venv/bin/pytest tests/test_arena_api.py tests/test_agents_api.py
```

Blocked by local environment, not code failure:

```text
psycopg2.OperationalError: connection to server at "127.0.0.1", port 5438 failed: Connection refused
```

Docker is also unavailable on this workstation (`docker: command not found`), so I could not start the repo's Postgres service locally. The test files were added and are ready to run once Postgres is reachable on `5438`.

## Next build phase

1. Add real ingestion jobs/scripts for LMArena + Artificial Analysis + LiveBench.
2. Upgrade votes from simple model upvotes to pairwise blind battles.
3. Compute per-task Elo or Bradley-Terry scores.
4. Join `agent_runs` to arena model profiles so the model card shows MiniBench's own agentic coding pass rate.
5. Add account/session-level voting protection beyond IP hash.
6. Code-split the frontend bundle.
