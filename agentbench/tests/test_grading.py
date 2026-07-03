from agentbench.grading import (
    exact_match,
    numeric_match,
    json_fields,
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


def test_grade_dispatch():
    assert grade({"type": "exact_match", "expected": "yes"}, "YES").passed
    assert grade({"type": "numeric_match", "expected": 7}, "the total is 7").passed
    assert not grade({"type": "unknown"}, "x").passed
