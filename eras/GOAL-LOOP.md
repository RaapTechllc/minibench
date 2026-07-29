# MiniBench goal loop

## Goal

Each `/goal` run completes one high-value, bounded improvement supported by current repository evidence, then leaves one evidence-backed candidate for the next run. Existing era recaps and ledgers are context; re-check claims against the current checkout.

## Environment

- Run `agentbench` modules from the repository root.
- Backend verification requires PostgreSQL. The documented Docker host port is 5438; the documented local-Postgres example uses 5432.
- `python -m agentbench.run --dry-run` is offline. Live OpenRouter runs require `OPENROUTER_API_KEY`.

## Hard invariants

- Never commit credentials or represent dry-run or synthetic benchmark data as live.
- Do not incur new spending, deploy, post, or message people. Use offline verification.
- A dedicated branch and draft pull request are the only shipping surface.

## Verification

```bash
cd backend && pytest
cd agentbench && pytest -q
cd cli && pytest
cd frontend && npm run lint && npm test && npm run build
python -m agentbench.run --config agentbench/presets/moa-v1.yaml --tasks agentbench/tasks/coding-v1.json --trials 2 --dry-run --out /tmp/dryrun.json
```

An era exits when its bounded goal is complete, relevant checks have run, current failures are reported accurately, and the next candidate is grounded in evidence.

<!-- unhobbled 2026-07-28; re-ablate after 2027-01-28 -->
