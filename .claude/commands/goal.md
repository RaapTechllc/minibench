---
description: Run the next MiniBench era — an autonomous, self-verifying goal run that seeds its successor
---

Run one bounded MiniBench era: choose the highest-value improvement supported by current repository evidence, complete it, verify it, and leave one evidence-backed candidate for the next era. Treat the arguments below as steering.

Hard guardrails:

- Never commit credentials or present dry-run or synthetic data as live benchmark results.
- Do not incur new spending, deploy, post, or message people. Use offline verification.
- A dedicated branch and draft pull request are the only shipping surface.

Repository verification commands:

```bash
cd backend && pytest
cd agentbench && pytest -q
cd cli && pytest
cd frontend && npm run lint && npm test && npm run build
python -m agentbench.run --config agentbench/presets/moa-v1.yaml --tasks agentbench/tasks/coding-v1.json --trials 2 --dry-run --out /tmp/dryrun.json
```

Backend tests require a reachable PostgreSQL instance. Report any current environment failure without treating it as a regression from unrelated work.

$ARGUMENTS

<!-- unhobbled 2026-07-28; re-ablate after 2027-01-28 -->
