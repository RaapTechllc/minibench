You are the independent cross-vendor validator for an UNHOBBLE run. The producer was OpenAI Codex. You are Google Gemini and must perform a fresh, read-only adversarial review. Do not edit any file.

Repository root:
/Users/timraap/projects/minibench

Objective:
Determine whether the producer removed hobbling from live AI-agent instruction files and nothing else, while preserving machine contracts, environment facts, hard safety invariants, verified commands, archives, and reporting evidence.

Decision test for surviving instruction units:
1. Environment facts the model cannot infer (paths, ports, commands, branch/release convention, provider/tool routing, credential location).
2. Mechanical hard invariants (secrets, spending/live execution, external publication, destructive operations).
3. Rules preventing a documented repeated failure, with the observation cited.
Safety ties KEEP. Other uncertainty belongs in the report watchlist, not the live instruction.

Required files to inspect:
- AGENTS.md
- .claude/audit-state.md
- .claude/commands/goal.md
- eras/GOAL-LOOP.md
- .unhobble-archive/2026-07-28/REPORT.md
- the four corresponding archived originals under .unhobble-archive/2026-07-28/

Producer-declared rewritten source hashes:
- AGENTS.md: 65456ea6791926da359c03212524d2372c55554dc1714ddfd0f188c5fbbda941
- .claude/audit-state.md: dd045f7cc71af8f172249f51fe4d1310a68d6de11045261923db5f900d5cad0f
- .claude/commands/goal.md: ffdd86bea26b8bb09af43151c14ab38256294bd0300e242ce1545c94753b0264
- eras/GOAL-LOOP.md: 84909bea17c4b6a5a447ec23ef25659f2f19eedfbb4aaf4e54a4bfe5a91237a1

Audit mechanically:
- Resolve and state the actual reviewed SHA-256 hashes.
- Verify archive hashes match originals recorded in REPORT.md.
- Verify before/after line counts.
- Verify the slash-command YAML frontmatter is byte-identical and $ARGUMENTS remains exactly once.
- Verify every live target ends with the exact 2026-07-28 / 2027-01-28 stamp.
- Check live scope completeness without treating READMEs, user docs, application code, CI YAML, era output artifacts, or archive trees as targets.
- Check each survivor against the decision test.
- Check that no original category-2 safety invariant was weakened.
- Check stale-fact corrections and whether repository commands are genuinely source-backed.
- Check the report includes per-file deletion verdicts, watchlist, stale corrections, baseline results, integrity hashes, and review provenance section.
- Check git diff is instruction/report/archive only.

Return exactly one verdict:
- ACCEPT: no blocking defects.
- REPAIR: provide a bounded list of at most 5 concrete defects, each with file and required correction.
- REJECT: only for a fundamental scope/integrity failure.

Output this compact structure:

Vendor: Google
Model: <actual model identifier used>
Timestamp (UTC): <ISO-8601>
Reviewed source hashes:
- <path>: <sha256>
Verdict: ACCEPT | REPAIR | REJECT
Findings:
- <concise evidence-backed finding, or "None">
Residual risk:
- <concise item, or "None">

Do not accept based on REPORT.md assertions alone; independently read and hash the files.
