# MiniBench project status and direction

Reviewed 2026-09-04 against `main` at `924affa` and the cleanup that follows it.
This is the starting point for current scope. Historical build briefs remain
available as records, not a queue of instructions to execute again.

## Active engineering goal

Tell a developer whether a model-plus-agent setup can finish real work, at what
cost and latency, and with what reliability. Measure completion with hidden
checks on fixed tasks and environments. Record the model and harness separately.

The accepted [Real-Work Agent Cabinet PRD, #30](https://github.com/RaapTechllc/minibench/issues/30)
and merged PRs [#58](https://github.com/RaapTechllc/minibench/pull/58),
[#59](https://github.com/RaapTechllc/minibench/pull/59),
[#60](https://github.com/RaapTechllc/minibench/pull/60),
[#61](https://github.com/RaapTechllc/minibench/pull/61), and
[#62](https://github.com/RaapTechllc/minibench/pull/62) establish the current
engineering workstream. The last of these landed on August 31.

Keep the evidence types separate:

| Surface | Role |
|---|---|
| Real-Work Agent Cabinet, `/agent-cabinet` | Active engineering focus. Stateful agent task completion and reproducibility receipts. |
| Solo Cabinet, `/models` | Fast single-model capability screening before more expensive agent evaluation. |
| Multiplayer Cabinet, `/agents` | MoA configurations measured independently of Solo and Agent Cabinet. |
| OpenRouter Usage Board, `/usage` | Cited hosted-model usage, price, and external eval context. Separate from MiniBench measurements. |
| Hardware, CLI, legacy dashboard and compare | Retained local-inference reference data. Not the primary engineering roadmap. |

There is no universal score combining these surfaces. Agent Cabinet runs are
unranked and newest-first; only compatible pairs can support comparison claims.
The current homepage still contains legacy hardware charts. This cleanup does
not imply that a full product redesign has shipped.

## What works and what remains unproven

| Area | Repository evidence | Remaining limit |
|---|---|---|
| Agent task lifecycle | Offline prepare/execute/verify/dispose contract and CI smoke | A lifecycle smoke is not a model evaluation. |
| Task families | Generated repository repair, feature implementation, SQL repair, terminal operations, and self-review | Shipped CLIs use deterministic fake/gold reference agents. |
| Trust gates | Provenance, budget/disposal checks, recomputed statistics, publication and exact comparability receipts | These validate artifact structure and consistency, not the authenticity of an arbitrary submitter. |
| Product/API | Agent Cabinet list/detail/compare endpoints, frontend and Technician mode, operator manual | No verified deployed real-agent campaign was established by this audit. |
| Solo/MoA | Runners, executable graders, committed result artifacts and importer | Historical runs must retain their suite, dates and provider provenance. |
| Usage Board | GET-only poller, cached board, fixture fallback, recommendation adapters and scheduled workflow | September 4 scheduled run used fixtures because no API key was configured; it uploaded no live board artifact. Deployment of a live snapshot is not established. |

The baseline [main CI run](https://github.com/RaapTechllc/minibench/actions/runs/33390214010)
passed all four jobs. The [September 4 Usage Board run](https://github.com/RaapTechllc/minibench/actions/runs/33868072517)
explicitly logged `No OPENROUTER_API_KEY; fixture path only (not live).`
Neither run is evidence of production deployment or real Agent Cabinet results.

The next product milestone is **one genuine, reproducible agent evaluation from
execution through the product receipt**. Before specifying a new adapter or
runner, run the RaapTech technical reuse preflight against the current adapter
contract and available upstream implementations. Then choose a bounded task,
frozen configuration and budget. Paid calls, benchmark publication and deployment
need their own explicit authorization. Do not flip `dry_run` to manufacture a
live result. OpenRouter Mode B remains parked.

## Why the repository had conflicting visions

| Record | Interpretation now |
|---|---|
| March `TSD.md`, `TASK-BRIEF.md`, `SPRINT-1.md` | Original Mini PC hardware product, historical. |
| July `SPRINT-PLAN-FABLE5.md` | Historical hardware plus MoA continuation plan; not the current backlog. |
| July `docs/PIVOT-PLAN.md`, PR #17 | Implemented capability-first pivot. Hardware became a controlled/reference variable. |
| ADR 0001 and Arcade tickets | Accepted presentation rules for Solo/Multiplayer. Its old homepage wording is historical. |
| PRD #30 and August Agent Cabinet PRs | Current real-work evaluation workstream. |
| ADRs 0002/0003 and Usage Board PRs | Additive hosted-model data helper, not a replacement for Agent Cabinet. |
| July Arena rescue branch | Older voting/dashboard experiment; conflicts with the later no-Arena-clone boundary. Archived. |
| Local `hermes/value-intelligence-audit` checkout | Unfinished July Value Terminal proposal with uncommitted code; not accepted mainline work. Preserved separately. |

## Branch reconciliation

The initial inventory had ten non-main remote branches and no open PRs.
Never interpret a squash-merged branch's ahead count as new work by itself.

| Branch | Original head | Disposition |
|---|---|---|
| `cursor/agent-cabinet-api-hop-a-9091` | `e50a82a` | Already an ancestor of main, PR #60. |
| `cursor/agent-cabinet-feature-impl-dc80` | `899c209` | Already an ancestor of main, PR #58. |
| `cursor/agent-cabinet-frontend-hop-b-1f81` | `a216c2c` | Already an ancestor of main, PR #61. |
| `cursor/agent-cabinet-gate-hardening-eae9` | `eeb5352` | Already an ancestor of main, PR #62. |
| `cursor/agent-cabinet-gates-73c2` | `d519316` | Already an ancestor of main, PR #59. |
| `cursor/minibench-persist-live-a2-5163` | `3a81c9b` | Already an ancestor of main, PR #57. |
| `cursor/openrouter-mode-a-board-2ddf` | `cae205a` | Already an ancestor of main, PR #53. |
| `codex/issue-34-generated-repository-repair` | `7483f66` | Exact head of squash-merged PR #40. Preserve as `archive/2026-09-04/issue-34`; do not reintroduce pre-hardening code. |
| `cursor/e2e-full-sweep-0e57` | `03589ed` | Recover missing database upgrade and latency units. Preserve full branch as `archive/2026-09-04/e2e-full-sweep`. |
| `rescue/mac-local-2026-07-28` | `344c660` | Recover CLI publication error handling. Preserve obsolete Arena and short-prompt experiment as `archive/2026-09-04/mac-local`. |

The E2E experiment adds a separate Playwright dependency and tests that depend on
a pre-seeded stack, omit newer routes, or conditionally skip key assertions.
It is retained for future test work, not installed as proof of current coverage.
The recovered schema fix uses the existing explicit SQL migration convention
instead of adding automatic DDL on every API startup.

Archive tags retain the complete original histories. To resume an archived
experiment, create a new branch from its tag and reassess it against current main.
The dirty local Value Terminal checkout is left intact; its tracked patch,
untracked files and Git history are backed up in the cleanup task's work folder.

## Current work tracking

GitHub issues are the current backlog. [#37](https://github.com/RaapTechllc/minibench/issues/37)
tracks the delivered Agent Cabinet API/UI/operator documentation slice.
[#30](https://github.com/RaapTechllc/minibench/issues/30) remains the parent for
real-agent evidence and release readiness. Old sprint files and Era 1 receipts
describe their own dates and must not be treated as today's verification status.
