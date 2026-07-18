# Issue #34 work brief — generated repository-repair slice

## Authority and boundary

- Issue: https://github.com/RaapTechllc/minibench/issues/34 (`Agent Cabinet: generated repository-repair slice`).
- Parent/dependency: #30; #31 is complete on `main` through PRs #38/#39.
- Branch: `codex/issue-34-generated-repository-repair`, based on current `origin/main` at `143c949`.
- Work only in the isolated issue-34 worktree. Preserve every other worktree, branch, untracked file, stash, unpublished commit, and running service.
- Open a reviewed PR with `Closes #34`; never merge, deploy, release, spend money, use live model keys, or weaken/bypass hidden verification.

## Goal

Add an offline generated repository-repair task family to Agent Cabinet. A trial must create a clean real-shaped repository, deterministically seed a defect without exposing its location or cause, present only an observable symptom, and grade the resulting workspace with private behavioral and regression checks.

## Required implementation behavior

1. Add at least three genuinely distinct deterministic mutation templates (different failure modes, not renamed copies).
2. Define stable seeded generation: identical seed + fixture version yields byte-equivalent public fixture/gold outcome; different seeds yield valid variants.
3. Keep public prompts symptom-only: never reveal mutation identity, target file, private seed, hidden assertion, or repair.
4. Build an oracle that accepts the known-good narrow repair and rejects representative no-op, symptom-only, and over-broad/collateral repairs.
5. Verify requested behavior, preserved existing behavior, and forbidden collateral changes where relevant.
6. Emit sanitized artifacts containing fixture version, mutation/template identity hash, seed hash, harness, budgets, and terminal outcome, while excluding private seed and hidden-test content.
7. Provide a documented offline dry-run command for this family; no model/API key may be required.
8. Integrate with existing Agent Cabinet contracts and conventions rather than introducing a parallel task/result model.

## Implementation sequence

1. Inspect the issue-31 task contract, tracer fixture, existing task loaders, graders, artifact schemas, and test conventions.
2. Record a concise design mapping each acceptance criterion to files and deterministic tests.
3. Implement the smallest cohesive generated-repair family, fixtures/templates, oracle, sanitizer/provenance output, and dry-run entry point.
4. Add tests for same-seed replay, different-seed variation, template diversity, prompt secrecy, gold repair, negative repairs, collateral-change rejection, and artifact sanitization.
5. Run the targeted suite first, then all relevant offline AgentBench tests and repository-native static checks. Report unavailable checks as `NOT CONFIGURED`, never as pass.
6. Review the final diff for hidden-test leakage, nondeterminism, scope creep, and over-broad filesystem/network access. Fix all CRITICAL/HIGH findings.
7. Commit coherent changes, push the branch, and open a ready-for-human-review PR using the repository template with `Closes #34`. Do not merge.

## Deterministic acceptance checks

Use repository-native commands discovered from `README.md`, `agentbench/README.md`, package configuration, and CI. At minimum, evidence must include:

- focused generator/oracle tests for every required positive and negative case;
- two independent invocations proving same-seed replay and different-seed valid variation;
- automated assertions that public prompts and published artifacts exclude private seed, target path/cause, and hidden checks;
- offline dry run of the generated repository-repair family;
- the full relevant AgentBench offline suite;
- applicable lint/type/build checks used by CI;
- `git diff --check`;
- GitHub PR and CI state after publication.

Do not claim success unless all issue acceptance criteria are mapped to passing deterministic evidence. If business intent, hidden-test secrecy, environment prerequisites, or safe publication cannot be resolved, stop with a durable blocker receipt instead of guessing.
