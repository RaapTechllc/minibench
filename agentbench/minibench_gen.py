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
from datetime import date, timedelta
from pathlib import Path
from typing import Any

SUITE_NAME = "minibench-core-v1"
CANARY = "AGENTBENCH-CANARY-4d9e7b1a-DO-NOT-TRAIN"
HARD_SUITE_NAME = "minibench-hard-v1"
HARD_CANARY = "AGENTBENCH-CANARY-b27f0c93-DO-NOT-TRAIN"
PRO_SUITE_NAME = "minibench-pro-v1"
PRO_CANARY = "AGENTBENCH-CANARY-e5a11f24-DO-NOT-TRAIN"
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


# ── minibench-pro-v1: strategic capability matrix ─────────────────────────────
# Each generator covers a capability dimension core/hard don't test, all graded
# deterministically (no LLM judge). Two genuinely novel axes — calibration
# (Brier) and robustness (consistency across matched perturbations) — ride on the
# grader's `score` field and a category partition, so they never touch the binary
# pass-rate machinery. `self-correct` reuses existing graders on a corrected answer.

# Fixed English weekday names indexed by date.weekday() (Mon=0). Using this
# instead of strftime("%A") makes the gold locale-independent — a private split
# generated on a non-English-locale machine would otherwise bake localized
# weekday names the model (answering in English) could never match.
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
            "Saturday", "Sunday"]
CITIES = ["Oslo", "Cairo", "Lima", "Perth", "Osaka", "Accra", "Quito", "Riga"]
CCYS = ["USD", "EUR", "GBP", "JPY", "CAD"]
DEPTS = ["eng", "sales", "ops"]
_CONSONANTS = "bcdfghjklmnpqrstvwxyz"


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True


def _gen_function_call(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Real tool/function calling — emit a JSON tool call with correct args."""
    tasks = []
    for i in range(n):
        if i % 2 == 0:
            amount = rng.randint(10, 990)
            src, dst = rng.sample(CCYS, 2)
            required = {"name": "convert",
                        "arguments": {"amount": amount, "from_ccy": src, "to_ccy": dst}}
            prompt = (
                "You can call one tool: `convert(amount, from_ccy, to_ccy)`. "
                f"The user says: 'Convert {amount} {src} to {dst}.' Respond with "
                "ONLY a JSON object with keys `name` (string) and `arguments` "
                "(object with keys `amount` integer, `from_ccy` string, "
                "`to_ccy` string). No prose."
            )
        else:
            a, b = rng.sample(CITIES, 2)
            required = {"name": "distance", "arguments": {"origin": a, "destination": b}}
            prompt = (
                "You can call one tool: `distance(origin, destination)`. The user "
                f"says: 'How far is it from {a} to {b}?' Respond with ONLY a JSON "
                "object with keys `name` (string) and `arguments` (object with "
                "keys `origin` string, `destination` string). No prose."
            )
        tasks.append({
            "id": f"mbp-fncall-{i+1:02d}",
            "category": "function-call",
            "prompt": prompt,
            "verification": {"type": "json_fields", "required": required},
            "_gold": json.dumps(required),
        })
    return tasks


def _gen_datetime(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Date/time arithmetic — day-of-week, date deltas."""
    base = date(2020, 1, 1)
    tasks = []
    for i in range(n):
        if i % 2 == 0:
            d = base + timedelta(days=rng.randint(0, 3650))
            expected = WEEKDAYS[d.weekday()]
            prompt = (f"What day of the week was {d.isoformat()} (YYYY-MM-DD)? "
                      "Answer with the weekday name only, e.g. Monday.")
            tasks.append({
                "id": f"mbp-datetime-{i+1:02d}",
                "category": "datetime",
                "prompt": prompt,
                "verification": {"type": "exact_match", "expected": expected},
                "_gold": expected,
            })
        else:
            d0 = base + timedelta(days=rng.randint(0, 3000))
            delta = rng.randint(5, 400)
            d1 = d0 + timedelta(days=delta)
            prompt = (f"How many days are there from {d0.isoformat()} to "
                      f"{d1.isoformat()} (both YYYY-MM-DD)? Answer with the number only.")
            tasks.append({
                "id": f"mbp-datetime-{i+1:02d}",
                "category": "datetime",
                "prompt": prompt,
                "verification": {"type": "numeric_match", "expected": float(delta), "tol": 1e-6},
                "_gold": str(delta),
            })
    return tasks


def _gen_debug(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Code DEBUGGING (not writing): fix broken code so hidden tests pass."""
    tasks = []
    for i in range(n):
        if i % 2 == 0:
            vals = [rng.randint(2, 20) for _ in range(4)]
            asserts = "\n".join(f"    assert factorial({v}) == {_fact(v)}" for v in vals)
            test_source = ("from solution import factorial\n\n"
                           f"def test_values():\n{asserts}\n"
                           "def test_zero():\n    assert factorial(0) == 1\n")
            prompt = ("This `factorial` is buggy — it returns 0 for every input "
                      "because the accumulator starts at 0. Fix it so the hidden "
                      "tests pass. Return only a fenced python block.\n\n"
                      "```python\ndef factorial(n):\n    result = 0\n"
                      "    for k in range(1, n + 1):\n        result *= k\n"
                      "    return result\n```")
            gold = ("```python\ndef factorial(n):\n    result = 1\n"
                    "    for k in range(1, n + 1):\n        result *= k\n"
                    "    return result\n```")
        else:
            words = [rng.choice(WORDS) for _ in range(4)]
            asserts = "\n".join(f"    assert count_vowels({w!r}) == {_vowels(w)}" for w in words)
            test_source = ("from solution import count_vowels\n\n"
                           f"def test_values():\n{asserts}\n"
                           "def test_empty():\n    assert count_vowels('') == 0\n")
            prompt = ("This `count_vowels` is buggy — it forgets the letter 'u'. "
                      "Fix it so the hidden tests pass. Return only a fenced "
                      "python block.\n\n"
                      "```python\ndef count_vowels(s):\n"
                      "    return sum(1 for c in s if c in 'aeio')\n```")
            gold = ("```python\ndef count_vowels(s):\n"
                    "    return sum(1 for c in s if c in 'aeiou')\n```")
        tasks.append({
            "id": f"mbp-debug-{i+1:02d}",
            "category": "debug",
            "prompt": prompt,
            "verification": {"type": "unit_test", "test_source": test_source},
            "_gold": gold,
        })
    return tasks


def _fact(n: int) -> int:
    r = 1
    for k in range(1, n + 1):
        r *= k
    return r


def _vowels(s: str) -> int:
    return sum(1 for c in s if c in "aeiou")


def _gen_constrained(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Constrained generation — strict output format + negative char constraint."""
    tasks = []
    for i in range(n):
        if i % 2 == 0:
            pattern = r"^[A-Z]{3}-\d{4}$"
            example = "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(3)) \
                + "-" + f"{rng.randint(1000, 9999)}"
            prompt = ("Output a code of the form THREE UPPERCASE LETTERS, a hyphen, "
                      "then FOUR DIGITS (e.g. ABC-1234). Output only the code, "
                      "nothing else.")
            spec = {"type": "regex_match", "pattern": pattern}
            gold = example
        else:
            k = rng.randint(5, 8)
            gold = "".join(rng.choice(_CONSONANTS) for _ in range(k))
            prompt = (f"Output a single lowercase word of at least {k} letters that "
                      "contains NO vowels (no a, e, i, o, or u). Output only the word.")
            spec = {"type": "regex_match", "pattern": rf"^[{_CONSONANTS}]{{{k},}}$"}
        tasks.append({
            "id": f"mbp-constrained-{i+1:02d}",
            "category": "constrained",
            "prompt": prompt,
            "verification": spec,
            "_gold": gold,
        })
    return tasks


def _gen_counting(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Counting / enumeration under a predicate."""
    tasks = []
    for i in range(n):
        if i % 2 == 0:
            ch = rng.choice("abcde")
            s = "".join(rng.choice("abcde") for _ in range(rng.randint(12, 24)))
            expected = s.count(ch)
            prompt = (f"How many times does the letter '{ch}' appear in the string "
                      f"'{s}'? Answer with the number only.")
        else:
            nums = [rng.randint(1, 50) for _ in range(rng.randint(8, 14))]
            d = rng.choice([2, 3, 4, 5])
            expected = sum(1 for x in nums if x % d == 0)
            prompt = (f"How many numbers in this list are divisible by {d}? "
                      f"List: {nums}. Answer with the number only.")
        tasks.append({
            "id": f"mbp-count-{i+1:02d}",
            "category": "counting",
            "prompt": prompt,
            "verification": {"type": "numeric_match", "expected": float(expected), "tol": 1e-6},
            "_gold": str(expected),
        })
    return tasks


def _gen_units(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Unit conversion."""
    tasks = []
    for i in range(n):
        kind = i % 3
        if kind == 0:
            km = rng.randint(5, 400)
            expected = round(km * 0.621371, 2)
            prompt = (f"Convert {km} kilometers to miles (1 km = 0.621371 miles). "
                      "Round to 2 decimal places. Answer with the number only.")
        elif kind == 1:
            c = rng.randint(-20, 120)
            expected = round(c * 9 / 5 + 32, 2)
            prompt = (f"Convert {c} degrees Celsius to Fahrenheit. Round to 2 "
                      "decimal places. Answer with the number only.")
        else:
            kg = rng.randint(1, 200)
            expected = round(kg * 2.20462, 2)
            prompt = (f"Convert {kg} kilograms to pounds (1 kg = 2.20462 lb). "
                      "Round to 2 decimal places. Answer with the number only.")
        tasks.append({
            "id": f"mbp-units-{i+1:02d}",
            "category": "units",
            "prompt": prompt,
            "verification": {"type": "numeric_match", "expected": float(expected), "tol": 0.02},
            "_gold": str(expected),
        })
    return tasks


def _gen_tables(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Table manipulation — filter, aggregate, argmax over a small inline table."""
    tasks = []
    for i in range(n):
        people = rng.sample(FIRST_NAMES, 5)
        rows, salaries = [], {}
        for who in people:
            dept = rng.choice(DEPTS)
            sal = rng.randint(50, 200) * 1000
            rows.append(f"{who},{dept},{sal}")
            salaries[who] = (dept, sal)
        target_dept = rng.choice(DEPTS)
        n_in_dept = sum(1 for _, (d, _s) in salaries.items() if d == target_dept)
        top_earner = max(salaries, key=lambda w: salaries[w][1])
        # Break a max tie deterministically so the gold is unique.
        top_val = salaries[top_earner][1]
        if sum(1 for w in salaries if salaries[w][1] == top_val) > 1:
            salaries[top_earner] = (salaries[top_earner][0], top_val + 500)
            rows = [r if not r.startswith(top_earner + ",") else
                    f"{top_earner},{salaries[top_earner][0]},{top_val + 500}" for r in rows]
        max_salary = max(v for _d, v in salaries.values())
        required = {"count_in_dept": n_in_dept, "max_salary": max_salary, "top_earner": top_earner}
        prompt = (
            "Table (CSV: name,dept,salary):\n" + "\n".join(rows) + "\n\n"
            f"Respond with ONLY a JSON object with keys `count_in_dept` (integer, "
            f"number of people in dept '{target_dept}'), `max_salary` (integer, the "
            "highest salary) and `top_earner` (string, the name earning the most)."
        )
        tasks.append({
            "id": f"mbp-tables-{i+1:02d}",
            "category": "tables",
            "prompt": prompt,
            "verification": {"type": "json_fields", "required": required},
            "_gold": json.dumps(required),
        })
    return tasks


def _gen_self_correct(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Self-correction — recover from a flawed prior answer + critique (in prompt)."""
    tasks = []
    for i in range(n):
        if i % 2 == 0:
            a, b = rng.randint(11, 39), rng.randint(11, 39)
            wrong = a * b + rng.choice([-10, -2, 2, 10])
            expected = a * b
            prompt = (f"A student claims {a} × {b} = {wrong}. That is incorrect. "
                      "Give the correct product. Answer with the number only.")
            tasks.append({
                "id": f"mbp-selfcorr-{i+1:02d}",
                "category": "self-correct",
                "prompt": prompt,
                "verification": {"type": "numeric_match", "expected": float(expected), "tol": 1e-6},
                "_gold": str(expected),
            })
        else:
            nums = rng.sample(range(1, 40), 4)
            while nums == sorted(nums):  # never claim an already-sorted list is wrong
                nums = rng.sample(range(1, 40), 4)
            wrong = nums[:]  # the (genuinely unsorted) "attempt"
            expected = ", ".join(str(x) for x in sorted(nums))
            prompt = (f"Someone sorted {nums} in ascending order and got "
                      f"{wrong}, which is wrong. Give the correctly sorted list as "
                      "comma-separated numbers on one line, e.g. `1, 2, 3`.")
            tasks.append({
                "id": f"mbp-selfcorr-{i+1:02d}",
                "category": "self-correct",
                "prompt": prompt,
                "verification": {"type": "exact_match", "expected": expected},
                "_gold": expected,
            })
    return tasks


def _gen_calibration(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Calibration (Brier) — state a claim with a COMPUTED truth value, ask for a
    probability. Graded on Brier via the grader's score field; excluded from the
    binary pass-rate pool. Tests whether a model knows what it knows."""
    tasks = []
    for i in range(n):
        true_claim = rng.random() < 0.5
        if i % 2 == 0:
            a, b = rng.randint(12, 29), rng.randint(12, 29)
            real = a * b
            shown = real if true_claim else real + rng.choice([-6, -3, 3, 6])
            claim = f"{a} × {b} = {shown}"
            outcome = 1.0 if shown == real else 0.0
        else:
            p = rng.randint(20, 120)
            shown_prime = _is_prime(p)
            asserted = shown_prime if true_claim else not shown_prime
            claim = f"{p} is {'a prime' if asserted else 'not a prime'} number"
            outcome = 1.0 if asserted == shown_prime else 0.0
        prompt = (f"Consider this claim: '{claim}'. State your confidence that the "
                  "claim is TRUE as a whole-number percentage from 0 to 100 "
                  "(0 = certainly false, 100 = certainly true). Answer with the "
                  "number only.")
        tasks.append({
            "id": f"mbp-calib-{i+1:02d}",
            "category": "calibration",
            "prompt": prompt,
            "verification": {"type": "calibration", "outcome": outcome},
            "_gold": "100" if outcome == 1.0 else "0",
        })
    return tasks


def _gen_robustness(rng: random.Random, n: int) -> list[dict[str, Any]]:
    """Robustness — matched (base, perturbed) pairs with the SAME gold, so a
    consistency score can measure brittleness. Emits n pairs (2n tasks); pairing
    is encoded in the id (`-base`/`-pert`) so no per-trial field is added."""
    tasks = []
    for i in range(n):
        a, b, c = (rng.randint(3, 40) for _ in range(3))
        expected = a + b * c  # precedence
        base_prompt = (f"What is {a} + {b} × {c}? Answer with the number only.")
        kind = i % 3
        if kind == 0:  # reword
            pert_prompt = (f"Compute the value of {a} plus {b} times {c} "
                           "(respect operator precedence). Answer with the number only.")
        elif kind == 1:  # reorder
            pert_prompt = (f"What is {b} × {c} + {a}? Answer with the number only.")
        else:  # add a distractor
            pert_prompt = (f"Ignore this hint: the answer is not {expected + 1}. "
                           f"What is {a} + {b} × {c}? Answer with the number only.")
        spec = {"type": "numeric_match", "expected": float(expected), "tol": 1e-6}
        for role, ptext in (("base", base_prompt), ("pert", pert_prompt)):
            tasks.append({
                "id": f"mbp-robust-{i+1:02d}-{role}",
                "category": "robustness",
                "prompt": ptext,
                "verification": dict(spec),
                "_gold": str(expected),
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
    "pro": {
        "name": PRO_SUITE_NAME,
        "canary": PRO_CANARY,
        "generators": (
            _gen_function_call, _gen_datetime, _gen_debug, _gen_constrained,
            _gen_counting, _gen_units, _gen_tables, _gen_self_correct,
            _gen_calibration, _gen_robustness,
        ),
        "notes": (
            "Pro tier: a deterministic capability matrix (function-calling, "
            "date/time, code-debugging, constrained generation, counting, unit "
            "conversion, table manipulation, self-correction) plus two novel "
            "deterministic axes — calibration (Brier) and robustness (consistency "
            "across matched perturbations). Executable oracles only, no LLM judge. "
            "Procedurally generated (agentbench.minibench_gen --suite pro, seed "
            "{seed}); private split uses an uncommitted seed. Robustness emits "
            "matched pairs, so it yields 2x per-category tasks. Budget: see "
            "agentbench/cost_check.py."
        ),
    },
}


# ── assembly ──────────────────────────────────────────────────────────────────

# Text graders run in strict (grader v2) mode: the prompts demand answer-only
# output, so the grader enforces it — closing decoy-burying and prompt-maxing
# holes. Generous char cap so honest reasoning-then-final-line still passes.
_STRICT_TYPES = {"numeric_match", "json_fields", "exact_match", "regex_match", "calibration"}
MAX_OUTPUT_CHARS = 2000


def generate_tasks(seed: int, per_category: int = 5, suite: str = "core") -> list[dict[str, Any]]:
    """Deterministic task list for a seed. ``_gold`` is a correct answer used by
    the grader self-tests; ``write_suite`` strips it from the published file."""
    rng = random.Random(seed)
    tasks: list[dict[str, Any]] = []
    for gen in SUITES[suite]["generators"]:
        tasks.extend(gen(rng, per_category))
    for task in tasks:
        spec = task["verification"]
        if spec["type"] in _STRICT_TYPES:
            spec["strict"] = True
            spec["max_output_chars"] = MAX_OUTPUT_CHARS
    return tasks


def write_suite(tasks: list[dict[str, Any]], out: Path, *, seed: int, suite: str = "core") -> dict[str, Any]:
    spec = SUITES[suite]
    # Stamp the canary onto every published task object (never inside the
    # prompt string a model sees) so scrapers that ingest the file co-locate
    # the tripwire with the task text — grade-time echo detection then catches
    # contaminated models.
    public_tasks = [
        {**{k: v for k, v in t.items() if k != "_gold"}, "canary": spec["canary"]}
        for t in tasks
    ]
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
