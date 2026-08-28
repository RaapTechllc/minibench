# Real-Work Agent Cabinet — operator manual

This cabinet scores **agent harnesses** on pinned task fixtures. It is not Solo
Cabinet (single-model capability) and not Multiplayer Cabinet (MoA). Scores are
never combined into a composite.

Publication and comparison reuse `agentbench.agent_cabinet`
(`AGENT_CABINET_POLICY = "agent-cabinet-gates-v1"`). There is **no**
`--allow-infra` override on this path.

## Authoring

A task is a frozen manifest (`manifest_version: "1"`) plus a hidden verifier.

Required fields:

- `suite`, `task_id`, `category` (raw backend key, not an Arcade label)
- `scenario_type`, `public_prompt`
- `fixture.reference` and `fixture.digest`
- `preparation.strategy`, `verification.strategy`
- `required_capabilities` (non-empty)
- `budget` (`max_turns`, `wall_time_seconds`, `max_tokens`, `max_cost_usd`)
- `private` (boolean)

Surface prompt rules: name a concrete artifact, keep gold / hidden tests /
seeds out of the prompt, and write something a developer would paste into
Cursor. The verifier stays inside the environment.

Offline lifecycle smoke (no secrets, writes `dry_run: true`):

```bash
python -m agentbench.agent_tasks \
    --manifest agentbench/tasks/minibench-agent-v1-offline.json \
    --trials 2 --out /tmp/minibench-agent-smoke.json
```

## Fixture validation

Fixtures are pinned as `name@version` plus a `sha256:` digest.

- `fixture.reference` must contain `@` and must **not** use `@latest`
- `fixture.digest` must be `sha256:` followed by 64 hex characters
- Preparation must reproduce that digest; a mismatch is an infrastructure error

Examples:

| Reference | Result |
|-----------|--------|
| `offline-text-repair@1` | Accepted |
| `offline-text-repair` | Rejected (no version) |
| `offline-text-repair@latest` | Rejected (`mutable_fixture_reference`) |

## Gold / bad self-checks

Before a task is trusted, both directions of the oracle must hold:

- **Gold:** the known-good repair (or `_gold` answer) must pass hidden
  verification.
- **Bad:** a known-wrong edit must fail hidden verification.

If either check fails, set `provenance.self_check` to `failed` (or
`gold_self_check_failed` / `self_check_failed`). Publication then refuses with
`invalid_task_self_check`. Do not publish a task whose gold fails or whose bad
case passes.

## Budget checks

Every trial is metered before and after the adapter:

- `max_turns` — adapter-side turn counter
- `wall_time_seconds` — hard kill of the child process
- `max_tokens` — prompt + completion
- `max_cost_usd` — billed USD

Exceeding a budget is `timeout`, not a pass. Over-budget or malformed adapter
results never count as completion.

## Private-split handling

Official scores use `private: true`. The published identifier is
`private_split_id = sha256(suite|private-or-public|fixture_digest)`.

Never write the raw seed (`MINIBENCH_SEED`, `seed`, workspace paths, gold
files, hidden tests, or private rows) into an artifact. Provenance
sanitization drops those keys. A private-split run **supersedes** a public
run for the same identity key even when its completion is lower.

## Dry runs

`python -m agentbench.agent_tasks` always writes `dry_run: true`. Offline CLI
artifacts are not leaderboard data.

Publication tests (and a live publish) use an **in-memory** copy with
`dry_run: false` only. Gold CLI files stay dry-run. Do not treat them as
published scores.

## Comparison

Pairwise comparison is two steps:

1. `comparability_receipt(a, b)` — same task snapshot, fixture, harness
   contract, tool-contract hash, budgets, grader version, and private-split id.
2. If `comparable`, `compare_pair` applies the existing McNemar + task-bootstrap
   policy.

`GET /api/v1/agent-cabinet/compare?a=&b=` returns 409 with the receipt when the
pair is incomparable. Solo/MoA/hardware IDs are an `evaluation_type` mismatch
(409). Do not call `/api/v1/compare` (hardware) with cabinet runs.

Held constant: the shipped `COMPARABILITY_FIELDS`. Changed variables that may
differ across listed runs are `model_route` and/or `harness`.

## Publication gates

`publication_receipt` is the only publish decision. `publishable` → persist on
`POST /api/v1/agent-cabinet/runs`. Otherwise **422** `{ "detail": <receipt> }`.

The seven refuse reasons (no eighth, no `--allow-infra`):

| Reason | When |
|--------|------|
| `dry_run` | Artifact `dry_run` is true |
| `infrastructure_errors` | Summary or trial infra / preparation / execution failure |
| `canary_flags` | Summary or trial canary echo |
| `mutable_fixture_reference` | Missing `@version` or `@latest` |
| `missing_provenance` | Any required provenance key absent |
| `incomplete_disposal` | A trial left `workspace_disposed: false` |
| `invalid_task_self_check` | Gold/bad self-check failed |

Comparability mismatch never publish-refuses a run.

Importer:

```bash
# Prints destination=/api/v1/agent-cabinet/runs (or /api/v1/agents/runs for Solo/MoA)
python -m agentbench.import_results path/to/artifact.json --check

python -m agentbench.import_results path/to/artifact.json --api http://localhost:3070
```

`--allow-infra-errors` is ignored for cabinet artifacts.

## In-memory publishable example (not a live result)

This block is a documentation fixture: an in-memory `dry_run: false` copy of
the shape `build_agent_artifact` emits. It is **not** a live host result.

```json
{
  "generated_at": "2026-08-28T00:00:00+00:00",
  "dry_run": false,
  "provenance": {
    "model": "deterministic-fake-agent",
    "provider": "offline",
    "model_route": "offline/deterministic-fake-agent",
    "harness": "minibench-reference",
    "harness_version": "1",
    "tool_contract": ["filesystem"],
    "tool_contract_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "prompt_config_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "fixture_reference": "offline-text-repair@1",
    "fixture_digest": "sha256:760554a0320df97ccce509047ac3825878a252a4a2852f22f8ced20da7a5aa2c",
    "generator_sha256": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    "suite": "minibench-agent-v1",
    "task_set_sha256": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
    "budgets": {
      "max_turns": 1,
      "wall_time_seconds": 5,
      "max_tokens": 100,
      "max_cost_usd": 0.0
    },
    "git_commit": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
    "grader_version": "agent-1",
    "private_split": false,
    "private_split_id": "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
    "policy_version": "agent-cabinet-gates-v1"
  },
  "summary": {
    "suite": "minibench-agent-v1",
    "moa_config": {
      "name": "minibench-reference",
      "self_moa": false,
      "models": ["deterministic-fake-agent"]
    },
    "grader_version": "agent-1",
    "n_tasks": 1,
    "n_trials": 2,
    "pass_rate": 0.5,
    "pass_hat_k": 0.0,
    "pass_rate_ci95": [0.0945, 0.9055],
    "pass_rate_ci95_boot": [0.0, 1.0],
    "n_infra_errors": 0,
    "n_canary_flags": 0,
    "cost_usd_per_task": 0.01,
    "latency_p50_ms": 12,
    "evaluation_type": "agent_harness",
    "false_verification_rate": 0.0,
    "regression_rate": null,
    "termination_reasons": {"completed": 2}
  },
  "trials": [
    {
      "task_id": "mba-offline-text-repair-001",
      "category": "repository-repair",
      "trial": 1,
      "outcome": "success",
      "passed": true,
      "workspace_disposed": true,
      "agent_claimed_success": true,
      "termination_reason": "completed"
    },
    {
      "task_id": "mba-offline-text-repair-001",
      "category": "repository-repair",
      "trial": 2,
      "outcome": "verification_failed",
      "passed": false,
      "workspace_disposed": true,
      "agent_claimed_success": false,
      "termination_reason": "completed"
    }
  ]
}
```

Default view of that example: `completion` 50, `category_completion` of
`repository-repair` 50, `cost_usd_per_task` 0.01, `latency_p50_ms` 12.
Technician mode nests every required provenance key plus reliability fields,
CIs, `pass_hat_k`, budgets, and trials.
