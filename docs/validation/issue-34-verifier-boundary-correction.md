# Issue #34 verifier-boundary correction

## Goal and boundary

Correct PR #40's latest-head P1 verifier defects in the existing isolated `codex/issue-34-generated-repository-repair` worktree. No merge, deployment, issue closure, or production workflow is authorized.

## Acceptance criteria

- Candidate read/decode failures become sanitized `verification_failed` results.
- Private candidate import and behavioral probes run in a killable, hard-timeout subprocess.
- `BaseException`, child failure, and timeout become sanitized verification failures.
- Existing equivalence, collateral, determinism, and secrecy tests remain green.

## Deterministic checks and stop

Run the focused generated-repair suite, full AgentBench suite, and `git diff --check`. Stop on any failure. If clean, commit and push one correction to PR #40, then leave CI/review for independent verification. Never merge.