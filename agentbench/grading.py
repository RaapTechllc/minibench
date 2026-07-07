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

Grader v2 (anti-gaming): specs may set ``"strict": true`` (minibench suites do).
Strict mode enforces the answer-only output contract the prompts already state,
which closes the decoy-burying holes in v1:

- v1 ``numeric_match`` graded the LAST number anywhere, so burying the gold
  number after wrong guesses could never hurt and spraying candidates could
  help. Strict mode only accepts the whole output, or the last non-empty line,
  as ONE isolated number (an ``Answer:`` prefix is tolerated).
- v1 ``json_fields`` regex-hunted ``{.*}`` through arbitrary prose. Strict mode
  requires the output to BE a JSON object (optionally inside a single fence).
- Strict specs also carry ``max_output_chars`` (verbosity guard) — generous
  enough for honest reasoning-then-answer, but a hard cap on spray attacks.

``unit_test`` v2 additionally rejects solution code that fails a static purity
check (file/network/process/introspection access), because the model's code
executes at import time in the same directory as the hidden test file and could
otherwise read the asserts and special-case them.

Results produced with these graders must record ``GRADER_VERSION``; rows graded
under different versions are not comparable.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GRADER_VERSION = "2"

# Contamination tripwire: published suite files embed canary strings with this
# prefix. A model that emits it saw the benchmark file in training.
CANARY_MARKER = "AGENTBENCH-CANARY"

DEFAULT_MAX_OUTPUT_CHARS = 2000


@dataclass(frozen=True)
class GradeResult:
    passed: bool
    score: float  # 0.0–1.0
    detail: str


_CODE_FENCE = re.compile(r"```(?:[\w+-]*)\n(.*?)```", re.DOTALL)
_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
# One isolated number, tolerating $/%/thousands-commas/trailing period — the
# formats the minibench prompts legitimately elicit ("$1,234.50", "42.").
_ISOLATED_NUMBER = re.compile(
    r"^\**\s*\$?\s*(-?\d{1,3}(?:,\d{3})*(?:\.\d+)?|-?\d+(?:\.\d+)?)\s*%?\s*\.?\s*\**$"
)
_ANSWER_PREFIX = re.compile(r"^\s*\**\s*(?:final\s+)?answer\s*[:=]\s*", re.IGNORECASE)
# Reasoning models emit a hidden-thought block before the answer. Strip a single
# leading <think>…</think> so strict graders judge the ANSWER, consistently
# across categories (numeric_match already tolerates it via last-line parsing;
# without this, json_fields/exact_match would reject the same models).
_THINK_BLOCK = re.compile(r"^\s*<think>.*?</think>\s*", re.DOTALL | re.IGNORECASE)


def _strip_think(text: str) -> str:
    return _THINK_BLOCK.sub("", text, count=1)


def contains_canary(text: str) -> bool:
    """True if the model output echoes a benchmark canary — hard contamination signal."""
    return CANARY_MARKER in (text or "")


def extract_code(text: str) -> str:
    """Return the last fenced code block, or the whole text if unfenced.

    The *last* block is used because models often show scratch work first and
    the final implementation last.
    """
    blocks = _CODE_FENCE.findall(text)
    return blocks[-1].strip() if blocks else text.strip()


def _normalize(s: str) -> str:
    return " ".join(s.strip().lower().split())


def _too_long(output: str, spec_max: int | None) -> GradeResult | None:
    limit = spec_max if spec_max is not None else DEFAULT_MAX_OUTPUT_CHARS
    if len(output) > limit:
        return GradeResult(False, 0.0, f"verbosity: output {len(output)} chars > {limit} limit")
    return None


def exact_match(
    output: str,
    expected: str,
    *,
    strip_fence: bool = False,
    strict: bool = False,
    max_output_chars: int | None = None,
) -> GradeResult:
    if strict:
        long = _too_long(output, max_output_chars)
        if long:
            return long
        output = _strip_think(output)
        candidate = extract_code(output) if "```" in output else output
        lines = [ln for ln in candidate.strip().splitlines() if ln.strip()]
        if len(lines) != 1:
            return GradeResult(False, 0.0, f"expected a single-line answer, got {len(lines)} lines")
        candidate = lines[0]
    else:
        candidate = extract_code(output) if strip_fence else output
    ok = _normalize(candidate) == _normalize(expected)
    return GradeResult(ok, 1.0 if ok else 0.0, "match" if ok else f"expected {expected!r}")


def _parse_isolated_number(line: str) -> float | None:
    line = _ANSWER_PREFIX.sub("", line.strip())
    m = _ISOLATED_NUMBER.match(line)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


def numeric_match(
    output: str,
    expected: float,
    *,
    tol: float = 1e-6,
    strict: bool = False,
    max_output_chars: int | None = None,
) -> GradeResult:
    if strict:
        # Anti decoy-burying: only an ISOLATED final answer counts. Either the
        # whole output is one number, or the last non-empty line is one number
        # (optionally "Answer: X"). A final line mixing prose and numbers fails.
        long = _too_long(output, max_output_chars)
        if long:
            return long
        output = _strip_think(output)
        value = _parse_isolated_number(output)
        if value is None:
            lines = [ln for ln in output.strip().splitlines() if ln.strip()]
            if lines:
                value = _parse_isolated_number(lines[-1])
        if value is None:
            return GradeResult(False, 0.0, "no isolated final answer (strict)")
    else:
        matches = _NUMBER.findall(output)
        if not matches:
            return GradeResult(False, 0.0, "no number in output")
        # Grade on the LAST number — the model's final answer, not intermediate work.
        value = float(matches[-1])
    ok = abs(value - expected) <= tol
    return GradeResult(ok, 1.0 if ok else 0.0, f"got {value}, expected {expected}")


def _strict_json_candidate(output: str) -> tuple[str | None, str]:
    """The output must BE a JSON object: either the whole (stripped) text, or the
    content of a single fenced block with nothing but whitespace outside it."""
    stripped = output.strip()
    if stripped.startswith("{"):
        return stripped, "bare"
    fences = _CODE_FENCE.findall(output)
    if len(fences) == 1:
        outside = _CODE_FENCE.sub("", output).strip()
        if outside:
            return None, "prose outside the JSON fence (strict)"
        return fences[0].strip(), "fenced"
    return None, "output is not a JSON object (strict)"


def json_fields(
    output: str,
    required: dict[str, Any],
    *,
    strict: bool = False,
    max_output_chars: int | None = None,
) -> GradeResult:
    """Require a JSON object whose fields equal the required *values* (not just keys)."""
    if strict:
        long = _too_long(output, max_output_chars)
        if long:
            return long
        candidate, why = _strict_json_candidate(_strip_think(output))
        if candidate is None:
            return GradeResult(False, 0.0, why)
        try:
            obj = json.loads(candidate)
        except json.JSONDecodeError as e:
            return GradeResult(False, 0.0, f"invalid JSON: {e}")
    else:
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


# ── unit_test sandbox ─────────────────────────────────────────────────────────

# Modules whose import gives graded code file/network/process/introspection
# reach — enough to read the hidden test file or exfiltrate. Benign algorithmic
# imports (re, math, heapq, itertools, collections, ...) are untouched.
_DENIED_MODULES = frozenset({
    "os", "sys", "io", "pathlib", "socket", "subprocess", "ctypes",
    "importlib", "inspect", "urllib", "http", "requests", "shutil", "glob",
    "builtins", "tempfile", "pickle", "marshal", "codecs", "multiprocessing",
})
# getattr/setattr family is denied: without it a static AST walk can be bypassed
# entirely via getattr(obj, "__globals__")["__builtins__"]["open"] using string
# constants the walk never inspects. Denying the dynamic-access primitives is
# what actually contains the escape.
_DENIED_CALLS = frozenset({
    "open", "eval", "exec", "compile", "__import__", "globals", "vars", "locals",
    "breakpoint", "input", "memoryview", "getattr", "setattr", "delattr", "hasattr",
})
_DENIED_NAMES = frozenset({
    "__file__", "__loader__", "__builtins__", "__globals__", "__subclasses__",
    "__spec__", "__dict__", "__class__", "__bases__", "__mro__", "__code__",
    "__import__", "__getattribute__",
})


def check_solution_purity(code: str) -> str | None:
    """Static check that graded code cannot read the hidden test file, touch the
    network/filesystem, or introspect its way out. Returns a reason string if
    impure, else None. Runs on the AST BEFORE the code is written to disk."""
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"not valid Python: {e}"
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in _DENIED_MODULES:
                    return f"denied import: {alias.name}"
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in _DENIED_MODULES or node.level > 0:
                return f"denied import: from {node.module or '.'}"
        elif isinstance(node, ast.Name):
            if node.id in _DENIED_CALLS or node.id in _DENIED_NAMES:
                return f"denied name: {node.id}"
        elif isinstance(node, ast.Attribute):
            if node.attr in _DENIED_NAMES or node.attr in _DENIED_CALLS:
                return f"denied attribute: {node.attr}"
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # Close the string-literal channel: getattr(x, "__globals__") /
            # subscript["__builtins__"] smuggle dunders past the identifier
            # checks. Only dunders are flagged, so benign string data is safe.
            v = node.value
            if len(v) > 4 and v.startswith("__") and v.endswith("__"):
                return f"denied dunder via string literal: {v!r}"
    return None


def _sandbox_env() -> dict[str, str]:
    """Minimal env for the pytest subprocess so API keys and proxy settings are
    never inherited by graded code."""
    keep = ("PATH", "SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP", "TMPDIR",
            "PATHEXT", "COMSPEC", "WINDIR", "HOME", "USERPROFILE", "LANG", "LC_ALL")
    return {k: os.environ[k] for k in keep if k in os.environ}


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

    Anti-gaming: the solution executes at import time in the same directory as
    the test file, so before anything touches disk the extracted code must pass
    ``check_solution_purity`` (no file/network/process/introspection access),
    the test filename is randomized per trial, and the subprocess gets a
    minimal environment.
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
    impure = check_solution_purity(code)
    if impure:
        return GradeResult(False, 0.0, f"solution failed purity check: {impure}")

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / entry_filename).write_text(code, encoding="utf-8")
        # Randomized name: hardcoding 'test_solution.py' in the solution to read
        # the asserts stops working (defense in depth behind the purity check).
        test_file = d / f"test_{uuid.uuid4().hex}.py"
        # Legacy hard-suite tests read solution.py by its literal name for the
        # no-eval source assertion; keep that path working.
        test_file.write_text(test_source, encoding="utf-8")

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(test_file)],
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=_sandbox_env(),
            )
        except subprocess.TimeoutExpired:
            return GradeResult(False, 0.0, f"timed out after {timeout_s}s")

    passed = proc.returncode == 0
    detail = "tests passed" if passed else (proc.stdout or proc.stderr or "tests failed")[-500:]
    return GradeResult(passed, 1.0 if passed else 0.0, detail.strip())


def _strict_single_line(output: str, max_output_chars: int | None) -> tuple[str | None, GradeResult | None]:
    """Shared strict-mode reduction: verbosity cap, strip a leading <think>
    block, then require exactly one non-empty line (unwrapping a lone fence).
    Returns (candidate, None) on success or (None, failing GradeResult)."""
    long = _too_long(output, max_output_chars)
    if long:
        return None, long
    text = _strip_think(output)
    candidate = extract_code(text) if "```" in text else text
    lines = [ln for ln in candidate.strip().splitlines() if ln.strip()]
    if len(lines) != 1:
        return None, GradeResult(False, 0.0, f"expected a single-line answer, got {len(lines)} lines")
    return lines[0], None


def regex_match(
    output: str,
    pattern: str,
    *,
    must_match: bool = True,
    flags: int = 0,
    strict: bool = False,
    max_output_chars: int | None = None,
) -> GradeResult:
    """Constrained generation / negative constraints.

    ``must_match=True``  → the answer MUST satisfy ``pattern`` (e.g. a required
    format ``^[A-Z]{3}-\\d{4}$``). ``must_match=False`` → the answer must NOT
    contain ``pattern`` (negative constraint, e.g. "without the letter e").
    Strict mode reduces to a single answer line first, so a model can't bury a
    conforming token among prose.
    """
    if strict:
        candidate, fail = _strict_single_line(output, max_output_chars)
        if fail:
            return fail
    else:
        candidate = output
    try:
        hit = re.search(pattern, candidate, flags) is not None
    except re.error as e:
        return GradeResult(False, 0.0, f"bad pattern: {e}")
    ok = hit == must_match
    detail = "match" if ok else (
        f"must match {pattern!r} but did not" if must_match
        else f"must NOT match {pattern!r} but did"
    )
    return GradeResult(ok, 1.0 if ok else 0.0, detail)


def calibration(
    output: str,
    outcome: float,
    *,
    tol: float = 1e-9,
    strict: bool = False,
    max_output_chars: int | None = None,
) -> GradeResult:
    """Calibration via Brier score (novel deterministic axis).

    The prompt states a claim with a COMPUTED truth value and asks for a single
    confidence AS A PERCENTAGE FROM 0 TO 100 that the claim is true. ``outcome``
    is the ground truth (1.0 or 0.0). We parse one isolated number, interpret it
    on the 0-100 percentage scale the prompt mandates (``p = value / 100``,
    clamped to [0,1]), compute ``brier = (p - outcome)**2`` and report
    ``score = 1 - brier`` (higher is better, stays in [0,1]).

    Percentage-only parsing is deliberate: a dual "0-1 or 0-100" heuristic is
    non-monotonic at the boundary (it would read a compliant "1" — i.e. 1% — as
    certainty 1.0, identical to "100"), corrupting the axis. The prompt is
    explicit, so grading matches the instruction.

    ``passed`` marks a (near-)perfect probability — it exists only so the gold
    self-check gate accepts the gold answer; the real signal is the mean Brier
    reported as a suite-level axis, and calibration is EXCLUDED from the binary
    pass-rate pool. Empty/unparseable → Brier 1.0 (rule zero: a non-answer is
    maximally miscalibrated)."""
    if strict:
        long = _too_long(output, max_output_chars)
        if long:
            return long
        output = _strip_think(output)
    value = _parse_isolated_number(output)
    if value is None:
        lines = [ln for ln in output.strip().splitlines() if ln.strip()]
        value = _parse_isolated_number(lines[-1]) if lines else None
    if value is None:
        return GradeResult(False, 0.0, "no probability given (brier=1.0)")
    p = min(1.0, max(0.0, value / 100.0))  # prompt mandates a 0-100 percentage
    brier = (p - outcome) ** 2
    return GradeResult(brier <= tol, 1.0 - brier, f"p={p} outcome={outcome} brier={brier:.4f}")


def grade(spec: dict[str, Any], output: str) -> GradeResult:
    """Dispatch a task's verification ``spec`` to the matching executable grader."""
    vtype = spec.get("type")
    strict = bool(spec.get("strict", False))
    max_chars = spec.get("max_output_chars")
    if vtype == "exact_match":
        return exact_match(
            output,
            spec["expected"],
            strip_fence=spec.get("strip_fence", False),
            strict=strict,
            max_output_chars=max_chars,
        )
    if vtype == "numeric_match":
        return numeric_match(
            output,
            float(spec["expected"]),
            tol=float(spec.get("tol", 1e-6)),
            strict=strict,
            max_output_chars=max_chars,
        )
    if vtype == "json_fields":
        return json_fields(
            output,
            spec.get("required", {}),
            strict=strict,
            max_output_chars=max_chars,
        )
    if vtype == "unit_test":
        return unit_test(
            output,
            spec["test_source"],
            entry_filename=spec.get("entry_filename", "solution.py"),
            timeout_s=int(spec.get("timeout_s", 30)),
        )
    if vtype == "regex_match":
        return regex_match(
            output,
            spec["pattern"],
            must_match=bool(spec.get("must_match", True)),
            flags=re.IGNORECASE if spec.get("ignorecase") else 0,
            strict=strict,
            max_output_chars=max_chars,
        )
    if vtype == "calibration":
        return calibration(
            output,
            float(spec["outcome"]),
            strict=strict,
            max_output_chars=max_chars,
        )
    return GradeResult(False, 0.0, f"unknown grader type: {vtype!r}")
