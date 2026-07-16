# Work Brief — MiniBench Issue #31

## Selection

**Project:** MiniBench  
**Issue:** [#31 — Agent Cabinet: task contract + offline tracer fixture](https://github.com/RaapTechllc/minibench/issues/31)  
**Branch:** `codex/agent-cabinet-task-contract`  
**Worktree:** `/Users/timraap/projects/minibench-worktrees/agent-cabinet-task-contract`

## Why this project now

MiniBench has the clearest dependency-unlocking production task in the active portfolio. Issue #31 is the unblocked foundation for the Real-Work Agent Cabinet. Issues #32, #33, and #34 depend directly on it; #35 depends on #34; #36 depends on #32–#35; and #37 depends on #36. Finishing #31 unlocks the entire seven-story product sequence.

This is also aligned with RaapTech's current objective: measure whether model-plus-agent systems complete real repository and terminal work rather than merely answer prompts.

## Existing implementation found

The Agent Cabinet lifecycle implementation from `bf6bac7` is already present on
`origin/main` as `c818e10` with:

- `agentbench/agent_tasks.py`
- `agentbench/tasks/minibench-agent-v1-offline.json`
- `agentbench/tests/test_agent_tasks.py`
- AgentBench documentation updates

The current branch has no code diff against `origin/main` for these four files.

## Verification completed

```text
cd agentbench && ../agentbench/.venv/bin/python -m pytest tests/test_agent_tasks.py -q
31 passed in 1.29s
```

## Acceptance target

Before opening a PR, verify that the implementation fully satisfies issue #31:

1. Versioned manifest validation covers identity, category, fixture, prompt, verification strategy, capabilities, and budgets.
2. Stable prepare → execute → verify → dispose contract hides fixture internals.
3. Offline deterministic fake-agent smoke requires no API key.
4. External verification cannot be replaced by agent narration.
5. Success, verification failure, timeout, malformed result, and preparation failure produce explicit terminal outcomes.
6. Every path disposes the environment and repeated trials are clean.
7. Artifact remains backward-compatible with model-only summaries.
8. Contract, cleanup, isolation, compatibility, and smoke tests pass.

## Immediate next steps

1. Review `agent_tasks.py` against issue #31 line by line, prioritizing disposal guarantees and trust boundaries.
2. Run the complete AgentBench test suite, not only the 31 targeted tests.
3. Run formatting/lint/static checks configured by MiniBench.
4. Check branch drift against `origin/main` and rebase or merge safely if required.
5. Open a PR linked with `Closes #31` only after all gates pass.

## Guardrails

- Preserve the existing local-only `e2e-verify-jul4` branch and its five unpublished commits.
- Do not combine model-only, MoA, and Real-Work Agent Cabinet scores.
- Hidden verification stays outside the agent-accessible workspace.
- No paid provider or API key is required for this story's smoke path.
