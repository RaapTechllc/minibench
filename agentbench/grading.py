"""Executable graders — the fix for the prototype's keyword-presence scoring.

Rule zero from the brief: every task needs an *executable oracle*. A grader that
cannot fail a deliberately-bad answer does not discriminate, so each grader here
is designed so that a wrong/empty answer scores 0. Types:

- ``exact_match``   — normalized string equality against a gold answer.
- ``numeric_match`` — parse the final number from the output; compare within tol.
- ``json_fields``   — require a valid JSON object with specific field *values*.
- ``unit_test``     — extract the model's code and run a hidden pytest/unittest
                      module against it in a subprocess sandbox; pass iff tests pass.

``grade(spec, output)`` dispatches on ``spec["type"]``.
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class GradeResult:
    passed: bool
    score: float  # 0.0–1.0
    detail: str


_CODE_FENCE = re.compile(r"```(?:[\w+-]*)\n(.*?)```", re.DOTALL)
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def extract_code(text: str) -> str:
    """Return the last fenced code block, or the whole text if unfenced.

    The *last* block is used because models often show scratch work first and
    the final implementation last.
    """
    blocks = _CODE_FENCE.findall(text)
    return blocks[-1].strip() if blocks else text.strip()


def _normalize(s: str) -> str:
    return " ".join(s.strip().lower().split())


def exact_match(output: str, expected: str, *, strip_fence: bool = False) -> GradeResult:
    candidate = extract_code(output) if strip_fence else output
    ok = _normalize(candidate) == _normalize(expected)
    return GradeResult(ok, 1.0 if ok else 0.0, "match" if ok else f"expected {expected!r}")


def numeric_match(output: str, expected: float, *, tol: float = 1e-6) -> GradeResult:
    matches = _NUMBER.findall(output)
    if not matches:
        return GradeResult(False, 0.0, "no number in output")
    # Grade on the LAST number — the model's final answer, not intermediate work.
    value = float(matches[-1])
    ok = abs(value - expected) <= tol
    return GradeResult(ok, 1.0 if ok else 0.0, f"got {value}, expected {expected}")


def json_fields(output: str, required: dict[str, Any]) -> GradeResult:
    """Require a JSON object whose fields equal the required *values* (not just keys)."""
    match = re.search(r"\{.*\}", output, re.DOTALL)
    if not match:
        return GradeResult(False, 0.0, "no JSON object found")
    try:
        obj = json.loads(match.group())
    except json.JSONDecodeError as e:
        return GradeResult(False, 0.0, f"invalid JSON: {e}")
    if not isinstance(obj, dict):
        return GradeResult(False, 0.0, "JSON is not an object")

    wrong = []
    for key, want in required.items():
        if key not in obj:
            wrong.append(f"missing {key}")
        elif obj[key] != want:
            wrong.append(f"{key}={obj[key]!r} != {want!r}")
    score = (len(required) - len(wrong)) / len(required) if required else 1.0
    return GradeResult(not wrong, score, "ok" if not wrong else "; ".join(wrong))


def unit_test(
    output: str,
    test_source: str,
    *,
    entry_filename: str = "solution.py",
    timeout_s: int = 30,
) -> GradeResult:
    """Run a hidden test module against the model's extracted code.

    ``test_source`` imports from ``solution`` (the model's code) and asserts. It
    runs in a throwaway temp dir via ``python -m pytest``; pass iff pytest exits 0.

    pytest is a HARD requirement here, not optional. The test sources are
    pytest-style (``def test_*(): assert ...``); running them any other way would
    silently misgrade — plain ``python file.py`` never calls the ``test_*``
    functions (exit 0 → everything "passes"), and ``python -m pytest`` with pytest
    absent exits non-zero for the wrong reason (→ correct code marked "failed").
    So if pytest can't be imported we raise instead of returning a bogus score.
    """
    if importlib.util.find_spec("pytest") is None:
        raise RuntimeError(
            "unit_test grading requires pytest, which is not importable. "
            "Install it (it is in agentbench/requirements.txt) — refusing to "
            "grade, because either fallback would produce false scores."
        )

    code = extract_code(output)
    if not code:
        return GradeResult(False, 0.0, "no code in output")

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / entry_filename).write_text(code, encoding="utf-8")
        test_file = d / "test_solution.py"
        test_file.write_text(test_source, encoding="utf-8")

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", str(test_file)],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            return GradeResult(False, 0.0, f"timed out after {timeout_s}s")

    passed = proc.returncode == 0
    detail = "tests passed" if passed else (proc.stdout or proc.stderr or "tests failed")[-500:]
    return GradeResult(passed, 1.0 if passed else 0.0, detail.strip())


def grade(spec: dict[str, Any], output: str) -> GradeResult:
    """Dispatch a task's verification ``spec`` to the matching executable grader."""
    vtype = spec.get("type")
    if vtype == "exact_match":
        return exact_match(output, spec["expected"], strip_fence=spec.get("strip_fence", False))
    if vtype == "numeric_match":
        return numeric_match(output, float(spec["expected"]), tol=float(spec.get("tol", 1e-6)))
    if vtype == "json_fields":
        return json_fields(output, spec.get("required", {}))
    if vtype == "unit_test":
        return unit_test(
            output,
            spec["test_source"],
            entry_filename=spec.get("entry_filename", "solution.py"),
            timeout_s=int(spec.get("timeout_s", 30)),
        )
    return GradeResult(False, 0.0, f"unknown grader type: {vtype!r}")
