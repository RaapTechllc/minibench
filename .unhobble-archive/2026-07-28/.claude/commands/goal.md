---
description: Run the next MiniBench era — an autonomous, self-verifying goal run that seeds its successor
---

Run one full **era** against this repo, following the protocol in
`eras/GOAL-LOOP.md` exactly. That file is the contract; this command is only
the ignition.

Steps:

1. **Orient.** Read `eras/GOAL-LOOP.md`, then the highest-numbered
   `eras/era-N/RECAP.md` (its final section is the seed for this era) and that
   era's `LEDGER.md` (landmines + verify-first). If no era exists yet, this is
   Era 1 — derive candidate goals from `docs/SPRINT-PLAN-FABLE5.md`,
   `.claude/audit-state.md`, and fresh recon instead of a seed.
2. **Open the era.** Create `eras/era-N+1/LEDGER.md` first, then work the
   phases: Bootstrap → Recon → Goal selection (write `MISSION.md`) → Build →
   Red team → Recap + fresh-agent audit → Ship + seed. Update the era index
   table in `eras/GOAL-LOOP.md`.
3. **Hold the guardrails.** No new spending; nothing published outside the
   repo; no fabricated benchmark data (dry-run/synthetic always labeled);
   never ask the owner questions — log question, answer, and rationale in the
   ledger instead.
4. **Verify adversarially.** Fan out scout agents in recon, run skeptic +
   completeness-critic agents before closing, and finish with a fresh-agent
   audit that built nothing and defaults to "fail".
5. **Close = seed.** The era is done only when the definition-of-done
   checklist in `GOAL-LOOP.md` passes and `RECAP.md` ends with the
   `## Era N+2 seed` section. Ship on a dedicated branch with a draft PR.

If the user passed arguments, treat them as steering for goal selection
(e.g. `/goal focus on the hardware product`) — they constrain Phase 2, not
the protocol.

$ARGUMENTS
