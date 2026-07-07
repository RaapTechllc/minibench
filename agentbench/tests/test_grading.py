import pytest

from agentbench.grading import (
    GRADER_VERSION,
    calibration,
    check_solution_purity,
    contains_canary,
    exact_match,
    numeric_match,
    json_fields,
    regex_match,
    unit_test,
    grade,
    extract_code,
)


def test_exact_match_normalizes_whitespace_and_case():
    assert exact_match("  Tokyo\n", "tokyo").passed
    assert not exact_match("Kyoto", "Tokyo").passed


def test_numeric_match_uses_last_number():
    # "first I thought 3, but the answer is 4" -> grades on 4.
    assert numeric_match("first 3, answer is 4", 4).passed
    assert not numeric_match("answer is 5", 4).passed
    assert not numeric_match("no digits here", 4).passed


def test_json_fields_checks_values_not_just_keys():
    out = 'Here you go: {"status": "URGENT", "count": 2}'
    assert json_fields(out, {"status": "URGENT", "count": 2}).passed
    # Right key, wrong value must fail (keyword matching would pass this).
    assert not json_fields(out, {"status": "LOW"}).passed
    assert not json_fields("not json", {"a": 1}).passed


def test_extract_code_returns_last_block():
    text = "scratch:\n```py\nx=1\n```\nfinal:\n```py\ndef f():\n    return 42\n```"
    assert "return 42" in extract_code(text)
    assert "x=1" not in extract_code(text)


UNIT_TEST_SRC = "from solution import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"


def test_unit_test_passes_correct_code():
    good = "```python\ndef add(a, b):\n    return a + b\n```"
    assert unit_test(good, UNIT_TEST_SRC).passed


def test_unit_test_fails_deliberately_bad_code():
    # Rule zero: a grader that can't fail a bad answer doesn't discriminate.
    bad = "```python\ndef add(a, b):\n    return a - b\n```"
    assert not unit_test(bad, UNIT_TEST_SRC).passed


def test_unit_test_fails_empty_output():
    assert not unit_test("no code here at all", UNIT_TEST_SRC).passed


def test_unit_test_raises_when_pytest_missing(monkeypatch):
    # If pytest can't be imported, grading must refuse (raise) rather than emit a
    # bogus score — silently passing or failing would corrupt every unit_test run.
    import agentbench.grading as g

    monkeypatch.setattr(g.importlib.util, "find_spec", lambda name: None)
    good = "```python\ndef add(a, b):\n    return a + b\n```"
    with pytest.raises(RuntimeError, match="requires pytest"):
        g.unit_test(good, UNIT_TEST_SRC)


def test_grade_dispatch():
    assert grade({"type": "exact_match", "expected": "yes"}, "YES").passed
    assert grade({"type": "numeric_match", "expected": 7}, "the total is 7").passed
    assert not grade({"type": "unknown"}, "x").passed


# ── grader v2: strict mode (anti decoy-burying / anti prompt-maxing) ──────────


def test_grader_version_is_2():
    assert GRADER_VERSION == "2"


def test_strict_numeric_accepts_isolated_final_answers():
    assert numeric_match("42", 42, strict=True).passed
    assert numeric_match("  42.\n", 42, strict=True).passed
    assert numeric_match("$1,234.50", 1234.5, strict=True).passed
    assert numeric_match("I compute step by step.\n3 * 14 = 42\nAnswer: 42", 42, strict=True).passed
    assert numeric_match("**42**", 42, strict=True).passed


def test_strict_numeric_rejects_decoy_burying():
    # v1 graded the LAST number anywhere, so spraying candidates could pass.
    assert not numeric_match("Maybe 41? Or 43? It could be 42", 42, strict=True).passed
    sprayed = "Candidates: 40, 41, 42, 43.\nOne of these is right: 42 43"
    assert not numeric_match(sprayed, 42, strict=True).passed
    # A final line mixing prose and the number is not an isolated answer.
    assert not numeric_match("The journey is 42 minutes.", 42, strict=True).passed
    # But non-strict (legacy suites) keeps the v1 behavior.
    assert numeric_match("The journey is 42 minutes long, so 42", 42).passed


def test_strict_numeric_verbosity_guard():
    long_output = ("filler " * 500) + "\n42"
    r = numeric_match(long_output, 42, strict=True)
    assert not r.passed
    assert "verbosity" in r.detail


def test_strict_json_requires_object_only_output():
    gold = {"a": 1}
    assert json_fields('{"a": 1}', gold, strict=True).passed
    assert json_fields('```json\n{"a": 1}\n```', gold, strict=True).passed
    # Prose around the object fails strict (v1's greedy regex accepted it).
    assert not json_fields('Sure! Here you go: {"a": 1}', gold, strict=True).passed
    assert json_fields('Sure! Here you go: {"a": 1}', gold).passed  # legacy mode
    # Prose outside a fence also fails strict.
    assert not json_fields('Here:\n```json\n{"a": 1}\n```\nHope that helps!', gold, strict=True).passed


def test_strict_exact_match_requires_single_line():
    assert exact_match("alpha, beta", "alpha, beta", strict=True).passed
    assert not exact_match("Here is the answer:\nalpha, beta", "alpha, beta", strict=True).passed


# ── unit_test sandbox hardening ───────────────────────────────────────────────


def test_purity_check_blocks_file_and_process_access():
    assert check_solution_purity("import os\ndef add(a, b):\n    return a + b") is not None
    assert check_solution_purity("def add(a, b):\n    return open('x').read()") is not None
    assert check_solution_purity("def f():\n    return __import__('os')") is not None
    assert check_solution_purity("from pathlib import Path") is not None
    assert check_solution_purity("def f():\n    return eval('1+1')") is not None
    assert check_solution_purity("x = __file__") is not None


def test_purity_check_allows_benign_algorithmic_code():
    assert check_solution_purity("import re\nimport math\ndef f(s):\n    return len(re.findall(r'a', s))") is None
    assert check_solution_purity("from collections import Counter\nimport itertools") is None


def test_unit_test_rejects_test_peeking_solution():
    # Classic attack: read the hidden test file at import time and special-case
    # the asserts. The purity check must fail this before it touches disk.
    peeker = (
        "```python\n"
        "import glob\n"
        "src = open(glob.glob('test_*.py')[0]).read()\n"
        "def add(a, b):\n    return a + b\n"
        "```"
    )
    r = unit_test(peeker, UNIT_TEST_SRC)
    assert not r.passed
    assert "purity" in r.detail


def test_unit_test_rejects_unparseable_code():
    r = unit_test("```python\nthis is not python at all!!\n```", UNIT_TEST_SRC)
    assert not r.passed


def test_purity_blocks_getattr_globals_sandbox_escape():
    # The escape found in adversarial review: reach open/__import__ through
    # getattr + string constants, bypassing an identifier-only denylist, then
    # read the hidden test file. The getattr-family and dunder-string bans must
    # kill it before it touches disk.
    escape = (
        "def solve(n):\n    return n\n"
        "_g = getattr((lambda: 0), \"__globals__\")\n"
        "_b = _g[\"__builtins__\"]\n"
        "_open = _b[\"open\"]\n"
    )
    assert check_solution_purity(escape) is not None
    # Each channel independently blocked:
    assert check_solution_purity("x = getattr(o, 'y')") is not None      # getattr call
    assert check_solution_purity("x = (lambda:0).__globals__") is not None  # dunder attr
    assert check_solution_purity("x = d['__builtins__']") is not None     # dunder string


def test_purity_still_allows_normal_dunder_free_code():
    assert check_solution_purity(
        "import re\n"
        "def evaluate(expr):\n"
        "    return sum(int(x) for x in re.findall(r'\\d+', expr))\n"
    ) is None


def test_strict_graders_tolerate_reasoning_think_block_consistently():
    # Reasoning models emit <think>…</think> before the answer. All three strict
    # text graders must judge the ANSWER, not reject the model for thinking —
    # otherwise thinking models are penalized differentially by category.
    think = "<think>let me work through this carefully...\nstep 2...</think>\n"
    assert numeric_match(think + "42", 42, strict=True).passed
    assert json_fields(think + '{"a": 1}', {"a": 1}, strict=True).passed
    assert exact_match(think + "alpha, beta", "alpha, beta", strict=True).passed


# ── pro graders: regex_match (constrained gen + negative constraints) ─────────


def test_regex_match_constrained_generation():
    pat = r"^[A-Z]{3}-\d{4}$"
    assert regex_match("ABC-1234", pat, strict=True).passed
    assert not regex_match("abc-1234", pat, strict=True).passed
    assert not regex_match("ABC-12", pat, strict=True).passed


def test_regex_match_negative_constraint():
    # "answer without using the letter e"
    assert regex_match("solution", r"e", must_match=False, strict=True).passed
    assert not regex_match("theme", r"e", must_match=False, strict=True).passed


def test_regex_match_strict_rejects_burying():
    # A conforming token buried among prose fails: strict wants a single line.
    pat = r"^[A-Z]{3}-\d{4}$"
    sprayed = "Here are options:\nABC-1234\nXYZ-9999"
    assert not regex_match(sprayed, pat, strict=True).passed


def test_regex_match_grade_dispatch():
    assert grade({"type": "regex_match", "pattern": r"^\d{3}$", "strict": True}, "123").passed
    assert grade({"type": "regex_match", "pattern": r"z", "must_match": False,
                  "strict": True}, "abc").passed


# ── pro graders: calibration (Brier) ──────────────────────────────────────────


def test_calibration_perfect_and_worst():
    # Perfectly confident and correct → brier 0 → score 1, passed (gold path).
    assert calibration("100", 1.0, strict=True).passed
    assert calibration("0", 0.0, strict=True).passed
    assert abs(calibration("100", 1.0).score - 1.0) < 1e-9
    # Perfectly confident and WRONG → brier 1 → score 0.
    assert abs(calibration("100", 0.0).score - 0.0) < 1e-9


def test_calibration_percentage_scale_and_clamps():
    # The prompt mandates 0-100; parsing is percentage-only and monotonic.
    assert abs(calibration("50", 1.0).score - 0.75) < 1e-9   # hedge → brier 0.25
    assert abs(calibration("50%", 1.0).score - 0.75) < 1e-9  # % suffix tolerated
    # A compliant "1" means 1% (under-confident on a true claim), NOT certainty:
    # brier = (0.01 - 1)^2 ≈ 0.9801, monotonic with "2" (0.02). This is the bug
    # the review caught — "1" must not collapse to p=1.0.
    assert calibration("1", 1.0).score < 0.05
    assert calibration("1", 1.0).score < calibration("2", 1.0).score
    # Out-of-range clamps rather than crashing.
    assert 0.0 <= calibration("999", 1.0).score <= 1.0


def test_calibration_no_answer_is_maximally_miscalibrated():
    r = calibration("I'm not sure", 1.0, strict=True)
    assert not r.passed
    assert r.score == 0.0  # brier 1.0


def test_calibration_tolerates_think_block():
    assert calibration("<think>hmm, the 7th prime is 17</think>\n100", 1.0, strict=True).passed


def test_calibration_grade_dispatch():
    assert grade({"type": "calibration", "outcome": 1.0, "strict": True}, "100").passed
    assert grade({"type": "calibration", "outcome": 0.0, "strict": True}, "0").passed


# ── active canaries ───────────────────────────────────────────────────────────


def test_contains_canary():
    assert contains_canary("blah AGENTBENCH-CANARY-4d9e7b1a-DO-NOT-TRAIN blah")
    assert not contains_canary("a normal answer: 42")
    assert not contains_canary("")
