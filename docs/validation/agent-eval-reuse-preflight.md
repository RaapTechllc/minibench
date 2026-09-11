# Agent evaluation reuse preflight

Reviewed against `main` at `cbc0912` before adding a genuine-eval dogfood
path. This is the technical reuse check required by
[docs/PROJECT-STATUS.md](../PROJECT-STATUS.md) and PRD #30 leftovers: do not
specify a new runner until the existing contract is exhausted.

## Decision

**Reuse the shipped Agent Cabinet contract.** Do not add a second lifecycle,
publication policy, or HTTP adapter family.

| Existing piece | Role reused |
|---|---|
| `AgentAdapter.execute(prompt, workspace, budget)` | Sole agent seam |
| `OfflineTextEnvironment` + `run_agent_trial` | prepare → execute → hidden verify → dispose |
| `execute_agent_with_budget` | Turn / token / cost / wall-time metering |
| `build_agent_artifact` + `apply_agent_cabinet_to_artifact` | Provenance + reliability fields |
| `publication_receipt` / `comparability_receipt` | Product publish and pairwise gates |
| `OpenAICompatClient` + injectable `Transport` | Model calls (same client as Solo/MoA) |
| `import_results --check` | Destination + honesty preview; no production POST |
| `minibench-agent-v1` offline text-repair fixture | Bounded dogfood task (same digest) |

The new `python -m agentbench.agent_eval` module is a **binding**, not a new
adapter framework: it implements `AgentAdapter` with the existing client and
writes a local product receipt. Family CLIs (`generated_repairs`,
`generated_features`, `generated_sql_repairs`, `terminal_operations`,
`self_review`) stay offline gold/fake reference runners.

## Rejected alternatives

| Option | Why not |
|---|---|
| New harness / task-environment protocol | Duplicates `agent_tasks.py` |
| Flip `dry_run` on gold/offline artifacts | Explicitly forbidden; not live evidence |
| Paid OpenRouter / Ollama Cloud campaign | Needs owner authorization; Mode B parked |
| Production `POST /api/v1/agent-cabinet/runs` | Out of scope; this PR does not publish |
| Usage Board fixture republish | Different surface; not an agent evaluation |
| Folio / FabOps / secrets | Do not touch |

## Evaluation classes (honest labels)

| Class | What ran | `dry_run` | Publishable? |
|---|---|---|---|
| `offline-reference` | `DeterministicFakeAgent` / gold CLIs | always `true` | no |
| `injected-transport` | Model adapter + scripted `Transport` | always `true` | no |
| `live-local` | Model adapter + local Ollama daemon | `false` | only if publication gates pass; this CLI still does not POST |
| `live-paid` | OpenRouter / Ollama Cloud | **refused** by this CLI | n/a |

`injected-transport` proves the genuine **path** (workspace inspect → model
completion → edit → hidden verify → scorecard + publication receipt). It is
not a live provider result. Do not relabel it live.

## Live-provider blocker (this environment)

- `OPENROUTER_API_KEY` is unset.
- No local `ollama` binary or daemon on `127.0.0.1:11434`.
- An `OLLAMA_API_KEY` may exist in some agent environments; this CLI **does
  not use it**. Ollama Cloud is treated as a paid live call and is refused
  without explicit owner authorization.

A live-local receipt therefore requires an operator machine with Ollama
installed. A paid campaign is a separate authorized task.

## Dogfood command

See [docs/operators/agent-cabinet.md](../operators/agent-cabinet.md)
(Genuine dogfood).
