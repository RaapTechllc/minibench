# MiniBench audit state

Baseline captured 2026-07-28:

| Gate | Exact command | Result |
|---|---|---|
| Backend | `cd backend && MINIBENCH_TEST_PG_HOST=127.0.0.1 MINIBENCH_TEST_PG_PORT=5432 .venv/bin/pytest` | Red: PostgreSQL was unreachable; 27 setup errors |
| agentbench | `cd agentbench && python3 -m pytest -q` | Green: 271 passed |
| CLI | `cd cli && python3 -m pytest` | Red: local environment lacked `psutil` during collection |
| Frontend | `cd frontend && npm run lint && npm test && npm run build` | Green: 32 tests passed; lint and build completed with warnings |
| Offline smoke | `python -m agentbench.run --config agentbench/presets/moa-v1.yaml --tasks agentbench/tasks/coding-v1.json --trials 2 --dry-run --out /tmp/unhobble-dryrun.json` | Green |

The backend and CLI failures are environment failures, not failures introduced by this instruction-only change.

<!-- unhobbled 2026-07-28; re-ablate after 2027-01-28 -->
