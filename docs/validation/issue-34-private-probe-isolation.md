# Issue #34 private-probe isolation

**Boundary:** `codex/issue-34-generated-repository-repair` in its existing isolated worktree.

## Acceptance contract

- Candidate code executes in a spawned process that cannot inherit the fixture or gold source.
- Gold-source evaluation and expected-result comparison remain in the parent verifier.
- Candidate hangs and all child failures remain bounded, sanitized verification failures.
- A frame-introspection regression cannot recover the gold source from candidate frames.

## Deterministic checks

Run the focused generated-repair suite, the complete AgentBench suite, and `git diff --check` before publication. PR #40 must remain unmerged and requires green latest-head CI plus a fresh Codex review.
