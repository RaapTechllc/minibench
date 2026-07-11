# The Goal Loop — MiniBench Eras

An **era** is one autonomous, self-verifying goal run against this repo: pick the
highest-value goals the evidence supports, build them, try to kill them, package
the result, and **seed the next era on completion**. The loop never ends with
"done" — it ends with "here is what Era N+1 should do, and why."

This file is the protocol. It is deliberately mission-agnostic; each era's
specifics live in `eras/era-N/MISSION.md`.

---

## The contract

1. **The ledger is the single source of truth.** `eras/era-N/LEDGER.md`, written
   in handoff format at every phase boundary: *state proven by commands · last
   actions · in-flight · landmines · verify-first*. Assume the process will be
   killed and resumed by a fresh instance that has only the ledger. If the
   ledger wouldn't get it to full speed, the ledger is incomplete.
2. **Never ask.** Every question you'd ask the owner, answer yourself with
   research and reasoning, then log the question, your answer, and why in the
   ledger.
3. **Blocked is not an option.** Same obstacle survives 3 *distinct* approaches
   (different strategies, not retried variations) or 30 minutes → the approach
   is dead. Ship the strong 80%, log the cut, advance.
4. **Invent nothing.** Every claim in the recap traces to a command that was
   actually run, a file:line that exists, or a URL that was actually fetched.
   Inference is labeled as inference. Benchmark data is never fabricated;
   dry-run/synthetic data is always labeled as such — this is a benchmarking
   project, data honesty *is* the product.
5. **Adversarially verify every important claim.** Skeptic agents whose only
   job is to refute; a completeness critic before any phase is called done;
   a fresh-agent audit (an agent that built nothing) before the era closes.
6. **Green gates or it didn't happen.** The four CI gates — backend pytest,
   cli pytest, agentbench pytest + dry-run smoke, frontend lint/test/build —
   must be green before an era closes. UI changes are additionally verified
   with a live backend and screenshots (desktop + mobile widths).

## Guardrails (every era, non-negotiable)

- **No new spending.** Only credentials already present in `.env` files may be
  used. No new paid services, no signups, no purchases. Live model runs require
  `OPENROUTER_API_KEY`; without it, everything ships offline-verified
  (dry-run, seeds, committed result artifacts) and is labeled accordingly.
- **Publish nothing outside the repo.** Branch + draft PR is the shipping
  surface. No deploys, no posts, no messages to real people.
- **Don't break the products.** The hardware CLI path, the submit API contract,
  and committed agentbench presets/tasks are load-bearing; CI dry-run guards
  drift — keep it passing.
- **Legal stops (the only two):** an action would violate a guardrail with no
  route around, or a load-bearing claim cannot satisfy the evidence rule.
  Then: write the ledger, state situation / options / recommendation in one
  paragraph, halt. Everything else routes around.

## The arc (default phases — reorder/merge when the destination is better served; log the deviation)

| Phase | Name | Exit criterion |
|-------|------|----------------|
| 0 | **Bootstrap** | Dev env up; all four gates run and their baseline status recorded in the ledger |
| 1 | **Recon** | Claimed gaps verified against code with file:line evidence (fan-out scouts) |
| 2 | **Goal selection** | 2–4 goals picked; each has: evidence it's open, value rationale, offline verification plan; rejected candidates logged |
| 3 | **Build** | Per goal: implemented → gates green → end-to-end verified (live API / browser screenshots for UI) |
| 4 | **Red team** | Skeptics attacked the era's claims; completeness critic ran; every finding fixed or documented in `RED-TEAM.md` |
| 5 | **Recap + audit** | `RECAP.md` links every deliverable; self-grade against definition of done; fresh-agent audit passed or findings addressed |
| 6 | **Ship + seed** | Committed, pushed, draft PR open; recap ends with the **Era N+1 seed** |

## Definition of done (per era — grade yourself before closing)

- [ ] Every guardrail held.
- [ ] Every selected goal shipped, or explicitly cut with rationale in the ledger.
- [ ] All four gates green, output captured in the ledger.
- [ ] UI changes screenshot-verified at desktop and mobile widths against a live backend.
- [ ] Every claim in the recap traces to a command, file:line, or fetched URL.
- [ ] Red team ran; objections visible in `RED-TEAM.md`; each fixed or answered.
- [ ] `RECAP.md` links every deliverable and every link resolves.
- [ ] Fresh-agent audit (built nothing, default verdict *fail*) ran; every finding fixed or documented.
- [ ] Ledger is complete enough to cold-start a successor instance.
- [ ] Recap ends with the Era N+1 seed: candidate goals + evidence + why.
- [ ] Nothing in the package is a placeholder pretending to be finished work.

## Goal run on completion (the loop)

Closing an era **is** opening the next one:

1. The recap's final section is `## Era N+1 seed` — 3–5 candidate goals, each
   with the evidence found during this era (red-team findings, cut scope,
   newly-verified gaps) and a one-line value case.
2. To start the next era, a fresh instance reads: `eras/GOAL-LOOP.md` (this
   protocol) → the latest era's `RECAP.md` (the seed) → that era's `LEDGER.md`
   (landmines). Then it creates `eras/era-N+1/MISSION.md` and begins at Phase 0.
3. The seed is advisory, not binding — Phase 1 recon re-verifies it. Evidence
   that has gone stale is discarded, and that discard is logged.

## Era index

| Era | Branch | Status | Recap |
|-----|--------|--------|-------|
| 1 | `claude/company-builder-experiment-qaaexr` ([PR #29](https://github.com/RaapTechllc/minibench/pull/29)) | complete | [era-1/RECAP.md](era-1/RECAP.md) |
