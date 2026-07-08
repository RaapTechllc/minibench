"""Procedural generator for the MoA-native ``moa-lite-v1`` disagreement suite.

Unlike ``minibench-*`` (single-model contract — MoA rejected by ``run.py``), this
suite is *designed* for cheap MoA / Self-MoA discrimination:

- Conflicting documents with explicit precedence (majority trap vs authority).
- Multi-constraint packs where the arithmetic-naive answer violates a rule.
- Partial tool / evidence gaps that must yield ``unknown`` rather than a flashy
  root cause.
- Proposal arbitration: two candidate answers, aggregator must pick/repair.

Target calibration (cheap flash singles): ~40–60% capability. MoA should have
headroom vs Self-MoA when proposers disagree. Executable oracles only — no Docker,
no LLM judge. SWE-bench-inspired *shape* (open scaffold, cost-light, gold
self-check), not a SWE-bench port.

Usage:
    python -m agentbench.moa_lite_gen --seed 20260708 \\
        --out agentbench/tasks/moa-lite-v1.json
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

SUITE_NAME = "moa-lite-v1"
CANARY = "AGENTBENCH-CANARY-moa-lite-a7c2e91f-DO-NOT-TRAIN"
DEV_SEED = 20260708
MAX_OUTPUT_CHARS = 2000

_STRICT_TYPES = {"numeric_match", "json_fields", "exact_match", "regex_match"}

SERVICES = ["checkout", "billing", "auth", "gateway", "inventory", "search"]
OWNERS = ["Ava", "Noah", "Mia", "Liam", "Zoe", "Kai"]


def _money(x: float) -> float:
    return round(x + 1e-12, 2)


# ── doc-conflict: authority / recency / supersede vs majority trap ───────────

def _gen_doc_conflict(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Conflicting memos; gold follows explicit precedence, not headcount."""
    tasks = []
    # Compact role legend — models that invent their own hierarchy fail.
    legend = (
        "Role tags in brackets are authoritative: "
        "[STD]=policy, [M]=memo, [D]=draft, [T]=ticket. "
        "Order: STD > M > D > T. Later date wins only within the same tag. "
        "Lines without a tag are noise."
    )
    for i in range(n):
        kind = i % 3
        topic = rng.choice(["retention_days", "page_threshold_p95_ms", "max_retries"])
        if kind == 0:
            wrong = rng.randint(14, 21)
            right = wrong + rng.choice([7, 14, 30])
            near = right - 1
            docs = [
                f"(2026-01-0{1+j}) {OWNERS[j]}: {topic} should be {wrong}"
                for j in range(3)
            ]
            docs.append(f"(2026-03-28) thread consensus: {topic}={wrong}")
            docs.append(f"(2026-03-29) trial note: {topic}={near}")
            docs.append(f"[M 2026-03-27] {OWNERS[4]}: temporary {topic}={wrong}")
            docs.append(f"[STD 2026-03-15] published {topic}={right}")
            rng.shuffle(docs)
            required = {"value": right, "source": "policy", "trusts_majority": False}
        elif kind == 1:
            older = rng.randint(100, 180)
            newer = older + rng.choice([15, 25, 35, 45])
            docs = [
                f"[M 2026-02-01] {OWNERS[0]}: {topic}={older}",
                f"[M 2026-04-10] {OWNERS[1]}: {topic}={newer}",
                f"[T 2026-04-18] agrees {older}",
                f"[D 2026-04-19] {topic}={older}",
                f"[D 2026-04-20] {topic}={older}",
                f"(2026-04-21) 'policy sync' chat: everyone {older}",
                f"(2026-04-22) changelog default={older}",
                # Tempting: a later STD-looking untagged line.
                f"(2026-04-23 STD?) rumor {topic}={older}",
            ]
            rng.shuffle(docs)
            required = {"value": newer, "source": "memo", "trusts_majority": False}
        else:
            old_v = rng.randint(3, 8)
            new_v = old_v + rng.choice([2, 3, 4])
            decoy = new_v + rng.choice([1, 2])
            docs = [
                f"[STD 2025-11-01] EFFECTIVE IMMEDIATELY: {topic}={old_v}",
                f"[STD 2026-05-01] §3.2 now {topic}={new_v}; 2025-11-01 §3.2 withdrawn",
                f"[M 2026-05-28] prod still {old_v}",
                f"[M 2026-05-29] lobby {decoy}",
                f"[D 2026-05-30] restore {old_v}",
                f"[T 2026-05-31] configured={old_v}",
                f"(2026-06-01) all-hands slide still shows {old_v}",
            ]
            rng.shuffle(docs)
            required = {"value": new_v, "source": "policy", "trusts_majority": False}
        prompt = (
            f"Resolve authoritative `{topic}`.\n{legend}\n"
            "Respond with ONLY JSON keys `value` (int), `source` "
            "(policy|memo|draft|ticket mapped from the tag you used; STD→policy), "
            "`trusts_majority` (bool: true iff you used the most common cited number "
            "among tagged lines).\nDocuments:\n- " + "\n- ".join(docs)
        )
        tasks.append({
            "id": f"moal-doc-{i+1:02d}",
            "category": "doc-conflict",
            "prompt": prompt,
            "verification": {"type": "json_fields", "required": required},
            "_gold": json.dumps(required, separators=(",", ":")),
        })
    return tasks


# ── constraint-pack: calc vs ban / cap / residual ─────────────────────────────

def _gen_constraint_pack(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Multi-constraint shopping / capacity — naïve math violates a rule."""
    tasks = []
    for i in range(n):
        kind = i % 3
        if kind == 0:
            # Two-SKU mix required: banned SKU + residual/spend mods + mix rule.
            # Gold mix is unique; max single-SKU looks better but is illegal.
            found = None
            for _ in range(150):
                budget = rng.choice([90, 100, 110, 120, 130, 140])
                pa = rng.choice([6, 7, 8])   # banned
                pb = rng.choice([9, 11, 13])
                pc = rng.choice([10, 14, 15])
                cap = rng.choice([4, 5, 6])
                # Must buy ≥1 of B and ≥1 of C; A banned; total units ≤ cap;
                # spend % 3 == 0; residual % 4 == 0; maximize spend.
                best = None
                for qb in range(1, cap):
                    for qc in range(1, cap - qb + 1):
                        if qb + qc > cap:
                            continue
                        sp = qb * pb + qc * pc
                        if sp > budget:
                            continue
                        res = budget - sp
                        if sp % 3 != 0 or res % 4 != 0:
                            continue
                        key = (sp, qb + qc, qb)  # max spend, then min units, then max B
                        if best is None or key > best[0]:
                            best = (key, qb, qc, sp, res)
                if best is None:
                    continue
                # Naïve: all-B or all-C under cap (single SKU) often looks better.
                naive = max(
                    (min(cap, budget // pb) * pb),
                    (min(cap, budget // pc) * pc),
                    (min(cap, budget // pa) * pa),
                )
                if naive <= best[0][0]:
                    continue
                _, qb, qc, sp, res = best
                found = (budget, pa, pb, pc, cap, qb, qc, sp, res)
                break
            assert found is not None
            budget, pa, pb, pc, cap, qb, qc, sp, res = found
            required = {
                "qty_b": qb,
                "qty_c": qc,
                "spend": _money(sp),
                "residual": _money(res),
            }
            prompt = (
                f"Budget ${budget}. SKUs: A@${pa} (banned), B@${pb}, C@${pc}. "
                f"Must buy a MIX: ≥1 B and ≥1 C, A forbidden, total units ≤ {cap}, "
                f"spend divisible by 3, residual divisible by 4. "
                f"Maximize spend; then minimize units; then maximize qty_b. "
                "Respond with ONLY JSON keys `qty_b`, `qty_c` (ints), "
                "`spend`, `residual` (numbers, 2 decimals)."
            )
        elif kind == 1:
            p1, p2 = 5, 7
            candidates = [
                47, 54, 61, 67, 68, 74, 75, 81, 82, 87, 88, 94, 95, 101, 102,
                107, 108, 114, 115, 121, 122, 128,
            ]
            target = rng.choice(candidates)
            pairs = []
            for aa in range(1, target // p1 + 1):
                rem = target - p1 * aa
                if rem >= p2 and rem % p2 == 0:
                    bb = rem // p2
                    if bb >= 1:
                        pairs.append((aa, bb))
            legal = [(aa, bb) for aa, bb in pairs if aa % 4 == 0 and bb <= 6]
            assert legal
            legal.sort(key=lambda t: (t[0] + t[1], -t[0]))
            a, b = legal[0]
            required = {"qty_alpha": a, "qty_beta": b, "spend": float(target)}
            prompt = (
                f"Pack exactly ${target} with alpha@${p1}, beta@${p2}. "
                f"Need ≥1 each, exact spend, qty_alpha % 4 == 0, qty_beta ≤ 6; "
                f"minimize units then maximize alpha. "
                "Respond with ONLY JSON keys `qty_alpha`, `qty_beta`, `spend`."
            )
        else:
            # Constructed dual-ban reject: two heavy jobs (≥ soft_ban) plus a
            # uniquely short job A cannot take → impossible though sum ≤ 2*cap.
            cap_w = rng.choice([10, 11, 12])
            soft_ban = min(7, cap_w - 3)
            # Pattern: two soft_ban jobs, one mid, one unique short.
            short = 3
            mid = max(4, soft_ban - 1)
            jobs = [soft_ban, soft_ban, mid, short]
            rng.shuffle(jobs)
            # Verify reject under dual ban; if somehow feasible, force reject gold
            # by shrinking capacity (still announce the shrunk cap).
            a_ban_job = min(range(4), key=lambda j: (jobs[j], j))
            indexed = sorted(enumerate(jobs), key=lambda t: -t[1])

            def try_assign(cap: int) -> bool:
                loads = [0, 0]
                for idx, dur in indexed:
                    order_w = [0, 1] if loads[0] <= loads[1] else [1, 0]
                    placed = False
                    for w in order_w:
                        if w == 1 and dur >= soft_ban:
                            continue
                        if w == 0 and idx == a_ban_job:
                            continue
                        if loads[w] + dur <= cap:
                            loads[w] += dur
                            placed = True
                            break
                    if not placed:
                        return False
                return True

            while try_assign(cap_w) and cap_w > max(jobs):
                cap_w -= 1
            assert not try_assign(cap_w)
            required = {"status": "reject", "load_a": 0, "load_b": 0}
            job_s = ", ".join(f"J{j}={jobs[j]}" for j in range(4))
            prompt = (
                f"Workers A/B capacity {cap_w}. Jobs: {job_s}. "
                f"B cannot take duration ≥ {soft_ban}. "
                f"A cannot take uniquely shortest job J{a_ban_job}. "
                "LPT; lighter worker then A; skip illegal. "
                "Impossible → reject with loads 0. "
                "Respond with ONLY JSON keys `status` ('ok'|'reject'), "
                "`load_a`, `load_b`."
            )
        tasks.append({
            "id": f"moal-constraint-{i+1:02d}",
            "category": "constraint-pack",
            "prompt": prompt,
            "verification": {
                "type": "json_fields",
                "required": required,
                "tol": 0.01 if "spend" in required or "residual" in required else None,
            },
            "_gold": json.dumps(required, separators=(",", ":")),
        })
    return tasks


# ── evidence-gap: partial tools must yield unknown / incomplete ───────────────

def _gen_evidence_gap(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Incomplete telemetry — overconfident root_cause must fail."""
    tasks = []
    # Deliberately short rubric: no recipe naming the gold for each vignette.
    rubric = (
        "Use live facts only. "
        "deploy if post-deploy live error_rate_pct>5 and deps OK; "
        "dependency if a dependency is currently DOWN; "
        "else unknown. "
        "page_now only for those actionable live cases."
    )
    for i in range(n):
        kind = i % 3
        svc = rng.choice(SERVICES)
        if kind == 0:
            # Looks like a classic deploy incident; scraper timed out.
            lines = [
                f"[{svc}] deploy d{rng.randint(100,999)} shipped 35m ago",
                f"[{svc}] p95={rng.randint(1000,2500)}ms",
                f"[{svc}] error_rate_scraper status=timeout",
                f"[{svc}] deps=OK",
                f"[{svc}] yesterday_error_rate_pct={rng.choice([7.1, 9.0, 11.2])}",
                f"[pager] suspected_cause=deploy",
            ]
        elif kind == 1:
            # Number present but coverage tag contradicts actionability.
            er = rng.choice([6.4, 8.8, 12.1])
            lines = [
                f"[{svc}] deploy d{rng.randint(100,999)} shipped 10m ago",
                f"[{svc}] error_rate_pct={er} meta=pre_deploy_window",
                f"[{svc}] deps=OK",
                f"[{svc}] rollback=ready",
                f"[ops] rollback now — it's the deploy",
            ]
        else:
            # DEGRADED + sparse rate — not DOWN, not complete deploy proof.
            er = rng.choice([5.5, 6.9, 8.0])
            lines = [
                f"[{svc}] deploy d{rng.randint(100,999)} shipped 50m ago",
                f"[{svc}] error_rate_pct={er} meta=sparse_n=3",
                f"[{svc}] deps=DEGRADED payments-api",
                f"[{svc}] history: redis DOWN→OK 4h ago",
                f"[draft-PM] cause=deploy",
            ]
        required = {
            "service": svc,
            "root_cause": "unknown",
            "needs_more_data": True,
            "page_now": False,
        }
        prompt = (
            "Triage. ONLY JSON: `service`, `root_cause` "
            "(deploy|dependency|unknown), `needs_more_data`, `page_now`.\n"
            f"{rubric}\nTelemetry:\n- " + "\n- ".join(lines)
        )
        tasks.append({
            "id": f"moal-evidence-{i+1:02d}",
            "category": "evidence-gap",
            "prompt": prompt,
            "verification": {"type": "json_fields", "required": required},
            "_gold": json.dumps(required, separators=(",", ":")),
        })
    return tasks


# ── proposal-arbitrate: aggregator must judge conflicting proposals ───────────

def _gen_proposal_arbitrate(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Two proposals; silent reject_reason trap is the discriminator."""
    tasks = []
    for i in range(n):
        kind = i % 3
        if kind == 0:
            d1, d2 = 60, 90
            s1, s2 = 60, 30
            correct = float(d1 + d2) / (d1 / s1 + d2 / s2)  # 37.5
            arithmetic = float(s1 + s2) / 2  # 45
            if rng.random() < 0.5:
                prop_a, prop_b, winner = arithmetic, correct, "B"
            else:
                prop_a, prop_b, winner = correct, arithmetic, "A"
            required = {
                "winner": winner,
                "answer": float(correct),
                "reject_reason": "arithmetic_mean",
            }
            prompt = (
                f"A trip is {d1} mi @ {s1} mph then {d2} mi @ {s2} mph. "
                "Average trip speed (mph)?\n"
                f"Proposal A: {prop_a}\nProposal B: {prop_b}\n"
                "ONLY JSON: `winner` (A|B|neither), `answer` (number), "
                "`reject_reason` (arithmetic_mean|constraint_violation|calc_error|none)."
            )
        elif kind == 1:
            price = rng.randint(80, 200)
            disc = rng.choice([15, 20, 25])
            fee = rng.choice([5, 8, 12])
            correct = _money(price * (1 - disc / 100) + fee)
            wrong = _money((price + fee) * (1 - disc / 100))
            if rng.random() < 0.5:
                prop_a, prop_b, winner = correct, wrong, "A"
            else:
                prop_a, prop_b, winner = wrong, correct, "B"
            required = {
                "winner": winner,
                "answer": correct,
                "reject_reason": "calc_error",
            }
            prompt = (
                f"Price ${price}; take {disc}% off the price, then add ${fee} fee "
                f"(fee not discounted). Final $, 2 decimals.\n"
                f"Proposal A: {prop_a}\nProposal B: {prop_b}\n"
                "ONLY JSON: `winner` (A|B|neither), `answer` (number), "
                "`reject_reason` (arithmetic_mean|constraint_violation|calc_error|none)."
            )
        else:
            budget = rng.choice([90, 100, 120])
            price = rng.choice([25, 30, 35])
            cap = 2
            gold_qty = min(cap, budget // price)
            gold_spend = float(gold_qty * price)
            prop_a = {"qty": cap + 1, "spend": min(budget, (cap + 1) * price)}
            prop_b = {"qty": gold_qty, "spend": gold_spend + price}
            required = {
                "winner": "neither",
                "answer": gold_spend,
                "reject_reason": "constraint_violation",
            }
            prompt = (
                f"Item@${price}, budget ${budget}, ≤{cap} units; max legal spend.\n"
                f"Proposal A: qty={prop_a['qty']} spend={prop_a['spend']}\n"
                f"Proposal B: qty={prop_b['qty']} spend={prop_b['spend']}\n"
                "ONLY JSON: `winner` (A|B|neither), `answer` (correct spend), "
                "`reject_reason` (arithmetic_mean|constraint_violation|calc_error|none)."
            )
        tasks.append({
            "id": f"moal-arbitrate-{i+1:02d}",
            "category": "proposal-arbitrate",
            "prompt": prompt,
            "verification": {
                "type": "json_fields",
                "required": required,
                "tol": 0.01,
            },
            "_gold": json.dumps(required, separators=(",", ":")),
        })
    return tasks


SUITE = {
    "name": SUITE_NAME,
    "canary": CANARY,
    "generators": (
        _gen_doc_conflict,
        _gen_constraint_pack,
        _gen_evidence_gap,
        _gen_proposal_arbitrate,
    ),
    "notes": (
        "MoA-native light suite (disagreement / multi-constraint / evidence-gap / "
        "proposal arbitration). NOT a minibench-* suite — MoA and Self-MoA configs "
        "are allowed. Procedurally generated (agentbench.moa_lite_gen, seed {seed}). "
        "Target: cheap single ~40–60% capability; MoA should have room vs Self-MoA. "
        "Executable oracles only."
    ),
}


def generate_tasks(seed: int, per_category: int = 3) -> list[dict[str, Any]]:
    """Deterministic task list. ``_gold`` for self-check; stripped on publish."""
    rng = random.Random(seed)
    tasks: list[dict[str, Any]] = []
    for gen in SUITE["generators"]:
        tasks.extend(gen(rng, per_category))
    for task in tasks:
        spec = task["verification"]
        if spec["type"] in _STRICT_TYPES:
            spec["strict"] = True
            spec["max_output_chars"] = MAX_OUTPUT_CHARS
        if spec.get("tol") is None:
            spec.pop("tol", None)
    return tasks


def write_suite(tasks: list[dict[str, Any]], out: Path, *, seed: int) -> dict[str, Any]:
    public_tasks = [
        {**{k: v for k, v in t.items() if k != "_gold"}, "canary": CANARY}
        for t in tasks
    ]
    payload = {
        "suite": SUITE_NAME,
        "notes": SUITE["notes"].format(seed=seed),
        "canary": CANARY,
        "generator_seed": seed,
        "tasks": public_tasks,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate moa-lite-v1 suite.")
    ap.add_argument("--seed", type=int, default=DEV_SEED)
    ap.add_argument("--per-category", type=int, default=3)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    tasks = generate_tasks(args.seed, args.per_category)
    write_suite(tasks, Path(args.out), seed=args.seed)
    print(f"Wrote {len(tasks)} tasks to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
