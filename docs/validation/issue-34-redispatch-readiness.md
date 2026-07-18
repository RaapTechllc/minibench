# Issue #34 production redispatch readiness

**Timestamp:** 2026-07-17 01:09:30 CDT  
**Repository:** `RaapTechllc/minibench`  
**Branch/worktree:** `codex/issue-34-generated-repository-repair` in `/Users/timraap/Projects/minibench-worktrees/issue-34-generated-repository-repair`

## Selected goal

Redispatch GitHub issue #34 (`Agent Cabinet: generated repository-repair slice`) through the locally corrected Codex-only `archon-plan-to-pr` workflow. This is the highest-priority unblocked portfolio goal: both Archon P0 repairs have deterministic evidence, issue #34 is open and ready for an agent, its environment blocker is cleared, no matching PR exists, and the Archon production slot is empty.

## Boundary and acceptance criteria

- Mutate only this isolated branch/worktree; preserve all other worktrees, branches, untracked files, stashes, unpublished commits, and running services.
- Treat `docs/issue-34-work-brief.md` and GitHub issue #34 as authoritative.
- Satisfy all issue criteria with deterministic offline evidence, including at least three distinct mutation families, seeded replay/variation, symptom-only prompts, positive and negative oracle cases, sanitized provenance, and an offline dry run.
- Open a reviewed PR with `Closes #34`; never merge, deploy, release, spend money, use live model keys, or weaken hidden verification.
- Use only OpenAI Codex/GPT-5.5 or newer for agentic implementation.

## Pre-dispatch deterministic checks

```text
Archon runs: running=0, paused=0
Issue #34: OPEN, label ready-for-agent
Matching PRs: none
PRESENT agentbench/.venv/bin/python
PRESENT backend/.venv/bin/pytest
PRESENT cli/.venv/bin/pytest
AgentBench contract baseline: 31 passed in 1.38s
git diff --check: pass
```

## Stop condition

Dispatch detached from the corrected local Archon stack with `--no-worktree`, capture run/conversation/worker/log identities, inspect the actual log, and stop this cycle as soon as the run reaches a valid first node with Codex/GPT-5.5+ resolution. If any prohibited provider resolves, abort and record the blocker. Do not start an overlapping workflow.
