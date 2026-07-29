# INDEPENDENT REVIEW PENDING — RUN NON-COMPLETE

# MiniBench unhobbling report — 2026-07-28

## Run summary

- Repository root: `/Users/timraap/projects/minibench` (resolved with `git rev-parse --show-toplevel`).
- Launch state: clean worktree on `main` at `92d847e62eb67fd1412601747b45badd04b7424a`.
- Doctrine: available and read at `/Users/timraap/Projects/unhobbling-report-2026-07-28.md`.
- Live targets: `AGENTS.md`, `.claude/audit-state.md`, `.claude/commands/goal.md`, and `eras/GOAL-LOOP.md`.
- Excluded: READMEs, product/spec/plan documents, era output artifacts, application code, CI configuration, dependencies, caches, and archive trees.
- Process evidence: validator prompts and failed-provider artifacts are under `.omx/artifacts/`; they are not live instructions or application changes.
- Symlinks: no live target is a symlink.
- Effectiveness evidence: deferred by design; the watchlist below is the future-failure surface.

## Machine-contract protection

- `AGENTS.md` remains at the repository root for automatic agent loading.
- `.claude/commands/goal.md` remains at the same command path.
- The three-line YAML frontmatter in `.claude/commands/goal.md` is byte-identical to the archived original.
- The `$ARGUMENTS` placeholder remains present once as a standalone line.
- No target contained marker-bounded generated blocks, hook configuration, or another parsed schema.

## Integrity and size

| Live file | Before | After | Original SHA-256 | Archive SHA-256 | Rewritten SHA-256 |
|---|---:|---:|---|---|---|
| `AGENTS.md` | 35 | 32 | `3159a09702ba790f73cb807d890b9c9a8a0803fa709d01eb0ae9834d5be31c84` | `3159a09702ba790f73cb807d890b9c9a8a0803fa709d01eb0ae9834d5be31c84` | `65456ea6791926da359c03212524d2372c55554dc1714ddfd0f188c5fbbda941` |
| `.claude/audit-state.md` | 95 | 15 | `2f18b8c07156653ae5287d355e41cb1b66c8e34cacd73eec8dbb53ffcd65f4b7` | `2f18b8c07156653ae5287d355e41cb1b66c8e34cacd73eec8dbb53ffcd65f4b7` | `dd045f7cc71af8f172249f51fe4d1310a68d6de11045261923db5f900d5cad0f` |
| `.claude/commands/goal.md` | 35 | 27 | `ff229ff309629a583951b06cf67a0a63f0bb5b0f9197c228dea0fd0aae03ad84` | `ff229ff309629a583951b06cf67a0a63f0bb5b0f9197c228dea0fd0aae03ad84` | `ffdd86bea26b8bb09af43151c14ab38256294bd0300e242ce1545c94753b0264` |
| `eras/GOAL-LOOP.md` | 101 | 31 | `4d66006e1f36a4ccc3898f168ef50cde6405b1f9e040854034c140b1d2ab53a9` | `4d66006e1f36a4ccc3898f168ef50cde6405b1f9e040854034c140b1d2ab53a9` | `84909bea17c4b6a5a447ec23ef25659f2f19eedfbb4aaf4e54a4bfe5a91237a1` |

Archive paths preserve the live relative paths under `.unhobble-archive/2026-07-28/`.

## File verdicts

### `AGENTS.md`

Surviving facts and invariants: setup-script behavior; service ports and proxy; PostgreSQL prerequisite and documented 5438/5432 choices; root-level `agentbench` module execution; offline/live credential boundary; Ollama requirement; CI-equivalent commands; credential, benchmark-integrity, spend, and external-action gates.

Deleted units:

- DELETE — “Cursor Cloud specific” framing and the claim that these notes describe the active VM: stale environment assumption.
- DELETE — PostgreSQL 16 is a native apt install on port 5432: false for this launch and not a portable repository fact.
- DELETE — Docker is unavailable and `pg_ctlcluster 16 main start` is the required startup path: stale OS-specific prescription.
- DELETE — role `minibench` and databases `minibench`/`minibench_test` already exist locally: unverified and contradicted by the unreachable listener.
- DELETE — `.env`, `backend/.env`, and `agentbench/.env` all exist and point to 5432: `agentbench/.env` is absent.
- DELETE — all three virtualenvs currently exist and a startup updater recreates them: only `backend/.venv` exists; the verified fact is that `scripts/setup-dev.sh` creates them.
- DELETE — agents must use `agentbench/.venv/bin/python`: that virtualenv is absent; root-level `python -m agentbench.run` was verified instead.
- DELETE — Ollama is not installed “here” and agents should use `POST /api/v1/submit` as a workaround: ephemeral installation claim plus task prescription.

### `.claude/audit-state.md`

Surviving facts: only the dated, actually-run baseline commands and their results.

Deleted units:

- DELETE — historical explanation of `/goal`, the nonexistent `/audit`, and how to interpret past audits: workflow lore, not current environment.
- DELETE — `last_build_sha`, `last_audit_sha`, branch, PR, and old green baseline: stale snapshot.
- DELETE — capability-pivot slices W1–W4 and their delivery narrative: historical changelog material.
- DELETE — manual-submission slice narrative and browser walkthrough: historical delivery report.
- DELETE — pagination-metadata slice narrative: historical delivery report.
- DELETE — benchmark-detail slice narrative: historical delivery report.
- DELETE — ADR/sign-off declarations: approval and output ritual with no live gate.
- DELETE — open/deferred roadmap list: product planning content, not an instruction-file survivor.
- DELETE — recommended next feature: goal prescription unsupported by current recon.

### `.claude/commands/goal.md`

Surviving machine contracts: frontmatter and `$ARGUMENTS`. Surviving behavior: one bounded evidence-backed goal, one next candidate, hard safety/integrity gates, release convention, and exact repository checks.

Deleted units:

- DELETE — “follow `GOAL-LOOP.md` exactly; this command is only ignition”: rigid delegation to a procedural prompt.
- DELETE — mandatory read order across protocol, recap, ledger, and fallback planning documents: procedural micromanagement.
- DELETE — create `LEDGER.md` first and execute seven named phases in order: output-format and phase ritual.
- DELETE — never ask the owner; answer and log every question yourself: approval theater that suppresses materially necessary escalation.
- DELETE — mandatory scout, skeptic, completeness-critic, and fresh-auditor fan-out: unproven agent choreography.
- DELETE — close only through a named checklist and exact `## Era N+2 seed` heading: output-format ritual.
- DELETE — arguments may constrain only “Phase 2”: stale coupling to deleted phases; steering semantics remain.

### `eras/GOAL-LOOP.md`

Surviving behavior: one bounded goal, current-evidence selection, one next candidate, documented environment facts, hard safety/integrity gates, dedicated-branch/draft-PR convention, and executable verification.

Deleted units:

- DELETE — rhetoric that an era never ends and must always seed another full era: autonomy theater beyond the compact goal.
- DELETE — ledger as single source of truth with mandatory handoff fields at every boundary: output-format ritual.
- DELETE — never ask the owner and self-answer every question: approval theater.
- DELETE — exactly three strategies or 30 minutes, then ship 80%: arbitrary retry/time policy without repeated-failure evidence.
- DELETE — every recap claim must use a prescribed command/file/URL citation form: reporting ritual; accurate claims remain required by the task itself.
- DELETE — mandatory skeptic agents, completeness critic, and fresh-agent audit: unproven orchestration.
- DELETE — “green gates or it didn’t happen” slogan and mandatory desktop/mobile screenshots: behavior-correction prose; exact gates remain.
- DELETE — generic “don’t break the products” sermon and load-bearing-component list: current models can infer this from scope and tests.
- DELETE — exactly two “legal stops” plus a required one-paragraph halt format: artificial blocker taxonomy and output ritual.
- DELETE — seven-phase arc and its table of phase-specific artifacts: procedural micromanagement.
- DELETE — eleven-item self-grading checklist: duplicated verification and output ritual.
- DELETE — three-step successor bootstrap and exact seed size/heading: procedure and format ritual; one evidence-backed next candidate remains.
- DELETE — Era 1 branch/PR/status index: historical state, not a durable instruction.

## Stale-fact corrections

| File | Before | After |
|---|---|---|
| `AGENTS.md` | Active environment is a no-Docker Cursor Cloud VM with native PostgreSQL on 5432. | Current launch is Darwin; Docker CLI exists but its daemon is inaccessible; PostgreSQL answered on neither 5432 nor 5438. The file now states only the repo-documented 5438 Docker mapping and 5432 local option. |
| `AGENTS.md` | Three virtualenvs and three component `.env` files already exist. | Only `backend/.venv`, root `.env`, and `backend/.env` exist. The file now states the verified setup-script behavior rather than current presence. |
| `AGENTS.md` | Use `agentbench/.venv/bin/python`. | That path is absent; root-level `python -m agentbench.run ... --dry-run` completed successfully. |
| `.claude/audit-state.md` | Build state was branch `claude/benchmark-detail-page` at `50950b3`, with old 12/12-era gate counts. | Launch state was `main` at `92d847e62eb67fd1412601747b45badd04b7424a`; the file now records the 2026-07-28 executed baseline only. |
| `.claude/audit-state.md` | Frontend baseline was 12 tests and historical backend/agentbench counts varied by slice. | Current run: frontend 32 tests green; agentbench 271 tests green; backend 27 setup errors from unavailable PostgreSQL; CLI collection error from missing `psutil`. |

## Repository-health evidence

Commands were discovered from `.github/workflows/ci.yml`, `README.md`, `agentbench/README.md`, and `frontend/package.json`.

| Command run | Baseline |
|---|---|
| `cd backend && MINIBENCH_TEST_PG_HOST=127.0.0.1 MINIBENCH_TEST_PG_PORT=5432 .venv/bin/pytest` | Red (pre-existing environment): 27 setup errors because PostgreSQL was unreachable. |
| `cd agentbench && python3 -m pytest -q` | Green: 271 passed in 40.12s. |
| `cd cli && python3 -m pytest` | Red (pre-existing environment): collection stopped because `psutil` is not installed in the invoked interpreter. |
| `cd frontend && npm run lint && npm test && npm run build` | Green: lint completed with three warnings; 32 tests passed; production build completed with a chunk-size warning. |
| `python -m agentbench.run --config agentbench/presets/moa-v1.yaml --tasks agentbench/tasks/coding-v1.json --trials 2 --dry-run --out /tmp/unhobble-dryrun.json` | Green: offline dry-run completed and wrote the temporary artifact. |

No deploy, publish, migration, live model call, message, or metered operation was run.

## Watchlist hypotheses

- If fresh instances repeatedly cannot resume useful work from ordinary git state and current docs, test a single-sentence ledger requirement before restoring the prior handoff schema.
- If agents repeatedly stall on one obstacle, measure the failures before restoring a retry count or time limit.
- Era 1 documented one premature close-out claim in `eras/era-1/AUDIT.md`; if that failure repeats, restore one narrow “evidence must exist before the claim” rule and cite both incidents.
- If UI regressions repeatedly pass the existing frontend gates, add a repository-owned visual verification command before restoring screenshot choreography.
- If goal runs repeatedly choose diffuse or low-value work, add the smallest evidence-backed selection constraint rather than restoring the seven-phase protocol.
- If Cursor Cloud again becomes a supported execution environment, generate its port/service facts from that environment and document repeated setup failures before restoring VM-specific prose.

## Independent review

No independent verdict was reachable:

- Anthropic Claude CLI 2.1.193, requested model `opus`, attempted 2026-07-29T00:44:16Z through the canonical `omx ask claude` path. Result: exit 1, `Not logged in · Please run /login`. Artifact: `.omx/artifacts/claude-you-are-the-independent-cross-vendor-validator-for-an-unhobb-2026-07-29T00-44-16-300Z.md`.
- Google Gemini CLI, model unknown because no response, attempted directly and through `omx ask gemini` before 2026-07-29T00:44:46Z. Both processes produced no output and were terminated after bounded waits. Artifact: `.omx/artifacts/gemini-unhobble-validator-2026-07-29T00-44-46Z.md`.

Neither vendor reviewed source hashes or returned ACCEPT / REPAIR / REJECT. A same-vendor check is not being represented as independent. Until a different vendor returns ACCEPT or a human waiver is recorded, this run remains NON-COMPLETE.

## Producer self-adversarial critique (not independent acceptance)

- Scope challenge: `eras/GOAL-LOOP.md` is the only live standalone workflow outside the explicit agent directories. `eras/era-1/{MISSION,LEDGER,RECAP,AUDIT,RED-TEAM}.md` are completed-run evidence artifacts, not live prompts; product briefs, PRDs, sprint plans, READMEs, and `tickets.md` are user documentation. No other live target was found.
- Contract challenge: the slash-command frontmatter and `$ARGUMENTS` token were mechanically compared with the archive; all live locations and stamps remain. No generated marker block was present to preserve.
- Safety challenge: the original no-spend, no-deploy/post/message, benchmark-honesty, credential-location, and dedicated-branch/draft-PR constraints remain in compact form. The general `AGENTS.md` adds an explicit owner gate for paid or external actions rather than authorizing them.
- Fact challenge: the largest rewrite risk was replacing Cursor-Cloud assumptions. Current host checks disproved them, while every replacement port/path/command is traceable to the README, setup script, Vite config, CI workflow, or an executed dry-run.
- Verification challenge: backend and CLI are red for missing local infrastructure/dependencies. The report labels them pre-existing and does not claim repository-wide green health; agentbench and frontend evidence is current.
- Residual concern: the repeated verification blocks add duplication, but the master prompt explicitly requires every rewritten file to name an exact repository verify command. No functional instruction was added solely to reach a line-count target.

Producer conclusion: no self-identified blocking defect, but this is not a verdict and does not complete the run.
