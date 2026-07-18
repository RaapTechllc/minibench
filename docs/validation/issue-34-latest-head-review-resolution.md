# Issue #34 latest-head review resolution

Date: 2026-07-17

PR #40 latest-head Codex review of `f1a2a5d` found that the explicit-zero
oracle did not preserve the generated seed-specific default and that private
probe exceptions could be misclassified as infrastructure failures. This
slice preserves the expected default behavior without requiring gold-source
equality and contains all private probe execution inside the verification
failure boundary.

The two earlier MEDIUM findings are also resolved: preparation now rejects
incompatible fixture/preparation/verification metadata before creating a
workspace, and a digest-mismatch regression proves preparation failure cleans
the partial workspace.

Deterministic checks:

```text
agentbench/.venv/bin/python -m pytest agentbench/tests/test_generated_repairs.py -q
agentbench/.venv/bin/python -m pytest agentbench/tests -q
git diff --check
```

Stop condition: commit and push one coherent latest-head review correction,
then leave PR #40 open and unmerged for CI and another latest-head review.