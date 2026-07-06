"""Procedural generator for the canonical ``minibench-*`` capability suites.

Every task instance is generated from a template with randomized parameters and
a *computed* gold answer (GSM-Symbolic / DyVal pattern), so no fixed string can
be memorized. The same command with a different ``--seed`` regenerates a fresh
private split; only the dev slice (seed 20260706) is committed to the repo.

Contamination posture (docs/PIVOT-PLAN.md W3): the committed file is the public
~10% dev slice. The private split is generated on demand and NEVER committed.
Task *concepts* in coding are deliberately simple (cheapness constraint) — the
discrimination comes from instance randomization + format strictness + trials,
not from puzzle novelty.

Usage:
    python -m agentbench.minibench_gen --seed 20260706 \
        --out agentbench/tasks/minibench-core-v1.json          # dev slice
    python -m agentbench.minibench_gen --seed <private-seed> \
        --out /secure/minibench-core-v1-private.json           # private split
"""
from __future__ import annotations

import argparse
import json
import random
import uuid
from pathlib import Path
from typing import Any

SUITE_NAME = "minibench-core-v1"
CANARY = "AGENTBENCH-CANARY-4d9e7b1a-DO-NOT-TRAIN"
DEV_SEED = 20260706

FIRST_NAMES = ["Ava", "Noah", "Mia", "Liam", "Zoe", "Kai", "Ivy", "Eli", "Uma", "Rex"]
SERVICES = ["checkout", "auth", "billing", "search", "inventory", "gateway"]
WORDS = ["quartz", "meadow", "python", "harbor", "signal", "copper", "violet",
         "thunder", "basil", "ember", "willow", "falcon", "indigo", "maple"]


# ── reasoning / math (numeric_match) ─────────────────────────────────────────

def _gen_reasoning(rng: random.Random, n: int) -> list[dict[str, Any]]:
    tasks = []
    for i in range(n):
        kind = i % 3
        if kind == 0:
            h1, m1 = rng.randint(6, 12), rng.randint(0, 59)
            dur = rng.randint(70, 400)
            h2, m2 = h1 + (m1 + dur) // 60, (m1 + dur) % 60
            prompt = (f"A meeting starts at {h1:02d}:{m1:02d} and ends at {h2:02d}:{m2:02d} "
                      "the same day. How many minutes long is it? Answer with the number only.")
            expected: float = dur
            tol = 1e-6
        elif kind == 1:
            price = rng.randint(40, 900)
            tax = rng.choice([5, 8, 10, 12])
            disc = rng.choice([10, 15, 20, 25])
            expected = round(price * (1 + tax / 100) * (1 - disc / 100), 2)
            prompt = (f"An item costs ${price}. Add {tax}% tax, then apply a {disc}% discount "
                      "to the taxed price. What is the final price in dollars, rounded to "
                      "2 decimal places? Answer with the number only.")
            tol = 0.011
        else:
            a0 = rng.randint(2, 30)
            d = rng.randint(3, 17)
            k = rng.randint(10, 60)
            expected = a0 + (k - 1) * d
            prompt = (f"An arithmetic sequence starts at {a0} and increases by {d} each step. "
                      f"What is the {k}th term (the first term is term 1)? "
                      "Answer with the number only.")
            tol = 1e-6
        tasks.append({
            "id": f"mb-reason-{i+1:02d}",
            "category": "reasoning",
            "prompt": prompt,
            "verification": {"type": "numeric_match", "expected": expected, "tol": tol},
            "_gold": str(expected),
        })
    return tasks


# ── structured output / tool-use (json_fields) ───────────────────────────────

def _gen_structured(rng: random.Random, n: int) -> list[dict[str, Any]]:
    tasks = []
    for i in range(n):
        if i % 2 == 0:
            order_id = f"A{rng.randint(1000, 9999)}"
            qty = rng.randint(2, 40)
            unit = round(rng.uniform(1.5, 80), 2)
            total = round(qty * unit, 2)
            text = (f"Order #{order_id}: {qty} units at ${unit:.2f} each, "
                    f"placed by {rng.choice(FIRST_NAMES)}.")
            required = {"order_id": order_id, "qty": qty, "total": total}
            prompt = (
                "Extract the order into JSON. Respond with ONLY a JSON object with keys "
                "`order_id` (string), `qty` (integer) and `total` (number, qty x unit "
                f"price, rounded to 2 decimals). Text: '{text}'"
            )
        else:
            level = rng.choice(["ERROR", "WARN", "INFO"])
            service = rng.choice(SERVICES)
            code = rng.randint(400, 599)
            line = f"2026-07-01T12:{rng.randint(10,59)}:00Z [{level}] {service}: upstream returned {code}"
            required = {"level": level, "service": service, "code": code}
            prompt = (
                "Parse this log line. Respond with ONLY a JSON object with keys `level` "
                "(string, as written), `service` (string) and `code` (integer status "
                f"code). Log line: '{line}'"
            )
        tasks.append({
            "id": f"mb-struct-{i+1:02d}",
            "category": "tool-use",
            "prompt": prompt,
            "verification": {"type": "json_fields", "required": required},
            "_gold": json.dumps(required),
        })
    return tasks


# ── instruction / format adherence (exact_match) ─────────────────────────────

def _gen_format(rng: random.Random, n: int) -> list[dict[str, Any]]:
    tasks = []
    for i in range(n):
        words = rng.sample(WORDS, rng.randint(5, 8))
        if i % 2 == 0:
            expected = ", ".join(sorted(words))
            prompt = (f"Sort these words alphabetically and output them comma-separated "
                      f"(single line, lowercase, exactly `word, word, ...`), and nothing "
                      f"else: {' '.join(words)}")
        else:
            shuffled = words + rng.sample(words, 3)
            deduped = list(dict.fromkeys(shuffled))
            expected = " ".join(deduped)
            prompt = (f"Remove duplicate words, keeping the FIRST occurrence of each, "
                      f"preserving order. Output the result as a single space-separated "
                      f"line and nothing else: {' '.join(shuffled)}")
        tasks.append({
            "id": f"mb-format-{i+1:02d}",
            "category": "instruction",
            "prompt": prompt,
            "verification": {"type": "exact_match", "expected": expected},
            "_gold": expected,
        })
    return tasks


# ── coding (unit_test, hidden randomized test values) ────────────────────────

def _digit_sum(x: int) -> int:
    return sum(int(c) for c in str(abs(x)))


def _rle(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        j = i
        while j < len(s) and s[j] == s[i]:
            j += 1
        out.append(f"{s[i]}{j - i}")
        i = j
    return "".join(out)


def _gen_coding(rng: random.Random, n: int) -> list[dict[str, Any]]:
    tasks = []
    for i in range(n):
        if i % 2 == 0:
            vals = [rng.randint(10, 10**6) for _ in range(4)]
            asserts = "\n".join(
                f"    assert digit_sum({v}) == {_digit_sum(v)}" for v in vals
            )
            test_source = ("from solution import digit_sum\n\n"
                           f"def test_values():\n{asserts}\n"
                           f"def test_negative():\n    assert digit_sum(-{vals[0]}) == {_digit_sum(vals[0])}\n")
            prompt = ("Write a Python function `digit_sum(n)` returning the sum of the "
                      "decimal digits of the integer n (ignore any sign). "
                      "Return only a fenced python block.")
            gold = ("```python\ndef digit_sum(n):\n"
                    "    return sum(int(c) for c in str(abs(n)))\n```")
        else:
            strs = ["".join(rng.choice("abc") for _ in range(rng.randint(4, 10))) for _ in range(4)]
            asserts = "\n".join(
                f"    assert rle({s!r}) == {_rle(s)!r}" for s in strs
            )
            test_source = ("from solution import rle\n\n"
                           f"def test_values():\n{asserts}\n"
                           "def test_empty():\n    assert rle('') == ''\n")
            prompt = ("Write a Python function `rle(s)` that run-length encodes a string: "
                      "each maximal run of a repeated character becomes the character "
                      "followed by the run length (e.g. 'aab' -> 'a2b1'). "
                      "Return only a fenced python block.")
            gold = ("```python\ndef rle(s):\n"
                    "    out, i = [], 0\n"
                    "    while i < len(s):\n"
                    "        j = i\n"
                    "        while j < len(s) and s[j] == s[i]:\n"
                    "            j += 1\n"
                    "        out.append(f'{s[i]}{j - i}')\n"
                    "        i = j\n"
                    "    return ''.join(out)\n```")
        tasks.append({
            "id": f"mb-code-{i+1:02d}",
            "category": "coding",
            "prompt": prompt,
            "verification": {"type": "unit_test", "test_source": test_source},
            "_gold": gold,
        })
    return tasks


# ── assembly ──────────────────────────────────────────────────────────────────

def generate_tasks(seed: int, per_category: int = 5) -> list[dict[str, Any]]:
    """Deterministic task list for a seed. ``_gold`` is a correct answer used by
    the grader self-tests; ``write_suite`` strips it from the published file."""
    rng = random.Random(seed)
    return (
        _gen_reasoning(rng, per_category)
        + _gen_structured(rng, per_category)
        + _gen_format(rng, per_category)
        + _gen_coding(rng, per_category)
    )


def write_suite(tasks: list[dict[str, Any]], out: Path, *, seed: int) -> dict[str, Any]:
    public_tasks = [{k: v for k, v in t.items() if k != "_gold"} for t in tasks]
    payload = {
        "suite": SUITE_NAME,
        "notes": (
            "Canonical capability minibenchmark, dev slice. Procedurally generated "
            f"(agentbench.minibench_gen, seed {seed}); the private split uses an "
            "uncommitted seed. Budget: see agentbench/cost_check.py."
        ),
        "canary": CANARY,
        "generator_seed": seed,
        "tasks": public_tasks,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate a minibench-core suite.")
    ap.add_argument("--seed", type=int, default=DEV_SEED)
    ap.add_argument("--per-category", type=int, default=5)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    tasks = generate_tasks(args.seed, args.per_category)
    write_suite(tasks, Path(args.out), seed=args.seed)
    print(f"Wrote {len(tasks)} tasks to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
