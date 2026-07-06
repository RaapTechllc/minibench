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
HARD_SUITE_NAME = "minibench-hard-v1"
HARD_CANARY = "AGENTBENCH-CANARY-b27f0c93-DO-NOT-TRAIN"
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


# ── hard variants (minibench-hard-v1): same oracles, more composition ─────────
# The core dev slice saturates on frontier models (7-way 100% tie in the first
# live sweep). These templates add compositional steps — search, aggregation,
# chained transforms, parsing — while keeping prompts short and answers cheap.

def _gen_reasoning_hard(rng: random.Random, n: int) -> list[dict[str, Any]]:
    tasks = []
    for i in range(n):
        kind = i % 3
        if kind == 0:
            digit_sum = rng.randint(14, 24)
            divisor = rng.choice([7, 11, 13, 17])
            x = 1
            while sum(int(c) for c in str(x)) != digit_sum or x % divisor != 0:
                x += 1
            expected: float = x
            prompt = (f"What is the smallest positive integer that is divisible by "
                      f"{divisor} and whose decimal digits sum to exactly {digit_sum}? "
                      "Answer with the number only.")
            tol = 1e-6
        elif kind == 1:
            principal = rng.randint(500, 5000)
            rate = rng.choice([3, 4, 6, 7])
            periods = rng.randint(3, 7)
            expected = round(principal * (1 + rate / 100) ** periods, 2)
            prompt = (f"An account starts with ${principal} and earns {rate}% compound "
                      f"interest per year. What is the balance after {periods} years, "
                      "rounded to 2 decimal places? Answer with the number only.")
            tol = 0.011
        else:
            fill_a = rng.randint(20, 60)
            fill_b = rng.randint(20, 60)
            drain = rng.randint(90, 240)
            minutes = 1 / (1 / fill_a + 1 / fill_b - 1 / drain)
            expected = round(minutes, 1)
            prompt = (f"Pipe A fills a tank in {fill_a} minutes, pipe B fills it in "
                      f"{fill_b} minutes, and an open drain empties it in {drain} "
                      "minutes. With all three open and the tank starting empty, how "
                      "many minutes until it is full? Round to 1 decimal place. "
                      "Answer with the number only.")
            tol = 0.06
        tasks.append({
            "id": f"mbh-reason-{i+1:02d}",
            "category": "reasoning",
            "prompt": prompt,
            "verification": {"type": "numeric_match", "expected": expected, "tol": tol},
            "_gold": str(expected),
        })
    return tasks


def _gen_structured_hard(rng: random.Random, n: int) -> list[dict[str, Any]]:
    tasks = []
    for i in range(n):
        if i % 2 == 0:
            customers = rng.sample(FIRST_NAMES, 4)
            lines, spend = [], {}
            for j in range(5):
                who = customers[j % 4]
                qty = rng.randint(1, 9)
                unit = round(rng.uniform(2, 40), 2)
                amount = round(qty * unit, 2)
                spend[who] = round(spend.get(who, 0) + amount, 2)
                lines.append(f"{who} bought {qty} x ${unit:.2f}")
            top = max(spend, key=lambda c: spend[c])
            # Regenerate on a tie for the top spender so the answer is unique.
            if sorted(spend.values())[-1] == sorted(spend.values())[-2]:
                spend[top] = round(spend[top] + 1.01, 2)
                lines.append(f"{top} bought 1 x $1.01")
            total = round(sum(spend.values()), 2)
            required = {"n_lines": len(lines), "total_revenue": total, "top_customer": top}
            prompt = (
                "Aggregate these order lines. Respond with ONLY a JSON object with "
                "keys `n_lines` (integer count of lines), `total_revenue` (number, "
                "sum of qty x unit price, rounded to 2 decimals) and `top_customer` "
                "(string, customer with the highest total spend). Lines: "
                + "; ".join(lines)
            )
        else:
            services = rng.sample(SERVICES, 3)
            worst = services[0]
            entries, err_count, max_code = [], 0, 0
            for j in range(6):
                svc = worst if j < 3 else services[1 + j % 2]
                level = "ERROR" if (svc == worst or j == 4) else "WARN"
                code = rng.randint(400, 599)
                if level == "ERROR":
                    err_count += 1
                    max_code = max(max_code, code)
                entries.append(f"[{level}] {svc} status={code}")
            required = {"n_errors": err_count, "worst_service": worst, "max_error_code": max_code}
            prompt = (
                "Analyze this log batch. Respond with ONLY a JSON object with keys "
                "`n_errors` (integer, count of ERROR lines), `worst_service` (string, "
                "service with the most ERROR lines) and `max_error_code` (integer, "
                "highest status code among ERROR lines only). Logs: "
                + " | ".join(entries)
            )
        tasks.append({
            "id": f"mbh-struct-{i+1:02d}",
            "category": "tool-use",
            "prompt": prompt,
            "verification": {"type": "json_fields", "required": required},
            "_gold": json.dumps(required),
        })
    return tasks


def _gen_format_hard(rng: random.Random, n: int) -> list[dict[str, Any]]:
    tasks = []
    for i in range(n):
        words = rng.sample(WORDS, rng.randint(6, 9))
        if i % 2 == 0:
            expected = ";".join(sorted(words, key=lambda w: (len(w), w)))
            prompt = (f"Sort these words by length (shortest first), breaking ties "
                      f"alphabetically. Output them joined by semicolons with no "
                      f"spaces, single line, nothing else: {' '.join(words)}")
        else:
            shift = rng.randint(2, 9)
            def _caesar(w: str) -> str:
                return "".join(chr((ord(c) - 97 + shift) % 26 + 97) for c in w)
            expected = " ".join(_caesar(w) for w in words)
            prompt = (f"Apply a Caesar cipher with shift +{shift} to every word "
                      f"(lowercase a-z wraps around). Output the transformed words "
                      f"space-separated, single line, nothing else: {' '.join(words)}")
        tasks.append({
            "id": f"mbh-format-{i+1:02d}",
            "category": "instruction",
            "prompt": prompt,
            "verification": {"type": "exact_match", "expected": expected},
            "_gold": expected,
        })
    return tasks


def _merge_intervals(intervals: list[list[int]]) -> list[list[int]]:
    out: list[list[int]] = []
    for lo, hi in sorted(intervals):
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def _gen_expression(rng: random.Random, depth: int = 2) -> str:
    if depth == 0:
        return str(rng.randint(1, 20))
    left = _gen_expression(rng, depth - 1)
    right = _gen_expression(rng, depth - 1)
    op = rng.choice(["+", "-", "*"])
    return f"({left} {op} {right})" if rng.random() < 0.5 else f"{left} {op} {right}"


def _gen_coding_hard(rng: random.Random, n: int) -> list[dict[str, Any]]:
    tasks = []
    for i in range(n):
        if i % 2 == 0:
            cases = []
            for _ in range(4):
                iv = [[a := rng.randint(0, 50), a + rng.randint(1, 12)] for _ in range(rng.randint(3, 6))]
                cases.append((iv, _merge_intervals(iv)))
            asserts = "\n".join(
                f"    assert merge_intervals({iv!r}) == {gold!r}" for iv, gold in cases
            )
            test_source = ("from solution import merge_intervals\n\n"
                           f"def test_values():\n{asserts}\n"
                           "def test_single():\n    assert merge_intervals([[1, 2]]) == [[1, 2]]\n")
            prompt = ("Write a Python function `merge_intervals(intervals)` that takes a "
                      "list of [start, end] integer intervals (unsorted, possibly "
                      "overlapping) and returns the merged, sorted list of disjoint "
                      "intervals as lists. Touching intervals (end == next start) merge. "
                      "Return only a fenced python block.")
            gold = ("```python\ndef merge_intervals(intervals):\n"
                    "    out = []\n"
                    "    for lo, hi in sorted(intervals):\n"
                    "        if out and lo <= out[-1][1]:\n"
                    "            out[-1][1] = max(out[-1][1], hi)\n"
                    "        else:\n"
                    "            out.append([lo, hi])\n"
                    "    return out\n```")
        else:
            exprs = [_gen_expression(rng, 2) for _ in range(4)]
            asserts = "\n".join(
                f"    assert evaluate({e!r}) == {eval(e)}" for e in exprs  # noqa: S307 - generated operands only
            )
            test_source = ("import pathlib\n"
                           "import re as _re\n"
                           "from solution import evaluate\n\n"
                           f"def test_values():\n{asserts}\n"
                           "def test_precedence():\n    assert evaluate('2 + 3 * 4') == 14\n"
                           "def test_no_eval():\n"
                           "    src = pathlib.Path('solution.py').read_text()\n"
                           "    assert not _re.search(r'\\b(eval|exec)\\s*\\(', src)\n")
            prompt = ("Write a Python function `evaluate(expr)` that evaluates an "
                      "arithmetic expression string containing non-negative integers, "
                      "+, -, *, parentheses and spaces, honoring precedence. Do NOT use "
                      "eval or exec (the hidden tests reject them). "
                      "Return only a fenced python block.")
            gold = ("```python\nimport re\n\n"
                    "def evaluate(expr):\n"
                    "    tokens = re.findall(r'\\d+|[+\\-*()]', expr)\n"
                    "    pos = 0\n"
                    "    def parse_expr():\n"
                    "        nonlocal pos\n"
                    "        val = parse_term()\n"
                    "        while pos < len(tokens) and tokens[pos] in '+-':\n"
                    "            op = tokens[pos]; pos += 1\n"
                    "            rhs = parse_term()\n"
                    "            val = val + rhs if op == '+' else val - rhs\n"
                    "        return val\n"
                    "    def parse_term():\n"
                    "        nonlocal pos\n"
                    "        val = parse_atom()\n"
                    "        while pos < len(tokens) and tokens[pos] == '*':\n"
                    "            pos += 1\n"
                    "            val = val * parse_atom()\n"
                    "        return val\n"
                    "    def parse_atom():\n"
                    "        nonlocal pos\n"
                    "        tok = tokens[pos]; pos += 1\n"
                    "        if tok == '(':\n"
                    "            val = parse_expr()\n"
                    "            pos += 1\n"
                    "            return val\n"
                    "        return int(tok)\n"
                    "    return parse_expr()\n```")
        tasks.append({
            "id": f"mbh-code-{i+1:02d}",
            "category": "coding",
            "prompt": prompt,
            "verification": {"type": "unit_test", "test_source": test_source},
            "_gold": gold,
        })
    return tasks


SUITES = {
    "core": {
        "name": SUITE_NAME,
        "canary": CANARY,
        "generators": (_gen_reasoning, _gen_structured, _gen_format, _gen_coding),
        "notes": (
            "Canonical capability minibenchmark, dev slice. Procedurally generated "
            "(agentbench.minibench_gen, seed {seed}); the private split uses an "
            "uncommitted seed. Budget: see agentbench/cost_check.py."
        ),
    },
    "hard": {
        "name": HARD_SUITE_NAME,
        "canary": HARD_CANARY,
        "generators": (_gen_reasoning_hard, _gen_structured_hard, _gen_format_hard, _gen_coding_hard),
        "notes": (
            "Hard tier: compositional search/aggregation/parsing tasks to separate "
            "models that saturate minibench-core-v1. Procedurally generated "
            "(agentbench.minibench_gen --suite hard, seed {seed}); private split "
            "uses an uncommitted seed. Budget: see agentbench/cost_check.py."
        ),
    },
}


# ── assembly ──────────────────────────────────────────────────────────────────

def generate_tasks(seed: int, per_category: int = 5, suite: str = "core") -> list[dict[str, Any]]:
    """Deterministic task list for a seed. ``_gold`` is a correct answer used by
    the grader self-tests; ``write_suite`` strips it from the published file."""
    rng = random.Random(seed)
    tasks: list[dict[str, Any]] = []
    for gen in SUITES[suite]["generators"]:
        tasks.extend(gen(rng, per_category))
    return tasks


def write_suite(tasks: list[dict[str, Any]], out: Path, *, seed: int, suite: str = "core") -> dict[str, Any]:
    spec = SUITES[suite]
    public_tasks = [{k: v for k, v in t.items() if k != "_gold"} for t in tasks]
    payload = {
        "suite": spec["name"],
        "notes": spec["notes"].format(seed=seed),
        "canary": spec["canary"],
        "generator_seed": seed,
        "tasks": public_tasks,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate a minibench suite.")
    ap.add_argument("--seed", type=int, default=DEV_SEED)
    ap.add_argument("--per-category", type=int, default=5)
    ap.add_argument("--suite", choices=sorted(SUITES), default="core")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    tasks = generate_tasks(args.seed, args.per_category, suite=args.suite)
    write_suite(tasks, Path(args.out), seed=args.seed, suite=args.suite)
    print(f"Wrote {len(tasks)} tasks to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
