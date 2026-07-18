# Issue #34 benchmark-validity correction receipt

**Timestamp:** 2026-07-17 05:19:12 CDT  
**Branch:** `codex/issue-34-generated-repository-repair`  
**PR:** https://github.com/RaapTechllc/minibench/pull/40

## Goal

Correct the two latest-head P1 review findings without weakening hidden verification:

1. accept behaviorally equivalent repairs rather than requiring the single generated gold source byte-for-byte;
2. keep exact private assertions and their test files out of the agent-visible prepared workspace.

## Implementation

- Generated public workspaces now contain only the small broken application repository and symptom prompt; generated test files and exact assertions remain private fixture state.
- Verification identifies the single permitted target privately, requires an unchanged file set, requires every non-target file to remain byte-identical, rejects no-op target content, and evaluates the target through private behavioral/regression probes.
- Added deterministic coverage for three non-gold equivalent implementations, workspace secrecy across all three templates, and continued no-op, test-only, collateral, runtime-cache, timeout, and artifact-sanitization rejection/handling.

## Deterministic evidence

- `agentbench/.venv/bin/python -m pytest agentbench/tests -q` — **213 passed** in 18.92s.
- Two-trial offline run (`--seed 20260717 --trials 2`) — pass rate **1.0**, zero infrastructure errors, zero canary flags, all workspaces disposed.
- `git diff --check` — passed.

## Stop condition

Stop after a coherent committed/pushed correction slice. Do not merge or close issue #34. CI and a fresh latest-head review remain required before acceptance.
