"""Minibench generator: determinism, graders that pass gold and fail garbage.

The bad-answer checks below ARE the brief's "pilot each grader against a
deliberately-bad answer" guardrail, encoded as a permanent test.
"""
import json

import pytest

from agentbench.grading import grade
from agentbench.minibench_gen import (
    CANARY,
    DEV_SEED,
    SCENARIO_TYPES,
    SUITES,
    generate_tasks,
    scenario_type_for_task,
    write_suite,
)

ALL_SUITES = sorted(SUITES)


@pytest.mark.parametrize("suite", ALL_SUITES)
def test_same_seed_is_deterministic(suite):
    a = generate_tasks(DEV_SEED, suite=suite)
    b = generate_tasks(DEV_SEED, suite=suite)
    assert a == b


@pytest.mark.parametrize("suite", ALL_SUITES)
def test_different_seed_changes_instances(suite):
    a = generate_tasks(DEV_SEED, suite=suite)
    b = generate_tasks(DEV_SEED + 1, suite=suite)
    assert a != b  # private split must not equal the public dev slice


@pytest.mark.parametrize("suite", ALL_SUITES)
def test_gold_answers_pass_their_grader(suite):
    for task in generate_tasks(DEV_SEED, suite=suite):
        result = grade(task["verification"], task["_gold"])
        assert result.passed, f"{task['id']}: gold failed grader — {result.detail}"


@pytest.mark.parametrize("suite", ALL_SUITES)
def test_deliberately_bad_answers_fail(suite):
    bad_by_type = {
        "numeric_match": "The answer is definitely -99999.5",
        "json_fields": '{"wrong_key": true}',
        "exact_match": "zz not the answer zz",
        "unit_test": "```python\npass\n```",
        # constrained: prose that satisfies no format and violates the vowel ban.
        "regex_match": "here is my answer: aeiou please",
        # calibration: a confident answer in the WRONG direction. For a TRUE
        # claim (outcome 1.0) "0" is maximally miscalibrated → not passed; for a
        # FALSE claim (outcome 0.0) "100" is. Pick the opposite of the gold.
        "calibration": None,
    }
    for task in generate_tasks(DEV_SEED, suite=suite):
        vtype = task["verification"]["type"]
        if vtype == "calibration":
            bad = "0" if task["verification"]["outcome"] == 1.0 else "100"
        else:
            bad = bad_by_type[vtype]
        result = grade(task["verification"], bad)
        assert not result.passed, f"{task['id']}: grader accepted a bad answer"


def test_committed_dev_slice_matches_generator(tmp_path):
    out = tmp_path / "suite.json"
    payload = write_suite(generate_tasks(DEV_SEED), out, seed=DEV_SEED)
    committed = json.loads(
        (out.parents[0] / out.name).read_text(encoding="utf-8")
    )
    assert committed == payload
    assert payload["canary"] == CANARY
    assert payload["generator_seed"] == DEV_SEED
    # published tasks never carry the gold answer
    assert all("_gold" not in t for t in payload["tasks"])
    # 4 categories x 5 tasks
    cats = {t["category"] for t in payload["tasks"]}
    assert cats == {"reasoning", "tool-use", "instruction", "coding"}
    assert len(payload["tasks"]) == 20


@pytest.mark.parametrize("suite,filename", [
    ("core", "minibench-core-v1.json"),
    ("hard", "minibench-hard-v1.json"),
    ("v2", "minibench-v2.json"),
    ("pro", "minibench-pro-v1.json"),
])
def test_repo_suite_file_is_current(suite, filename, tmp_path):
    """The committed suite must equal what the generator produces for its seed —
    regenerate with `python -m agentbench.minibench_gen` if this fails."""
    from pathlib import Path

    suite_path = Path(__file__).resolve().parents[1] / "tasks" / filename
    committed = json.loads(suite_path.read_text(encoding="utf-8"))
    fresh_path = tmp_path / filename
    fresh_payload = write_suite(
        generate_tasks(committed["generator_seed"], suite=suite),
        fresh_path,
        seed=committed["generator_seed"],
        suite=suite,
    )
    fresh = fresh_payload["tasks"]
    assert committed["tasks"] == fresh
    assert committed["suite"] == SUITES[suite]["name"]
    assert committed["canary"] == SUITES[suite]["canary"]
    # Published text-grader specs must be strict (grader v2 anti-gaming mode).
    for t in committed["tasks"]:
        if t["verification"]["type"] != "unit_test":
            assert t["verification"]["strict"] is True
        # Empty exact_match gold is banned (no positive oracle).
        if t["verification"]["type"] == "exact_match":
            assert str(t["verification"]["expected"]).strip(), t["id"]


def test_v2_format_tasks_never_empty_and_struct_has_tol():
    from agentbench.minibench_gen import V2_DEV_SEED

    tasks = generate_tasks(V2_DEV_SEED, suite="v2")
    for t in tasks:
        if t["id"].startswith("mb2-format-"):
            assert t["verification"]["expected"].strip()
        if t["id"].startswith("mb2-struct-") and "net_revenue" in t["verification"].get("required", {}):
            assert t["verification"].get("tol") == 0.01
            assert "Round EACH" in t["prompt"] or "round EACH" in t["prompt"].lower()


def test_v2_tasks_have_arcade_scenario_types():
    from agentbench.minibench_gen import V2_DEV_SEED

    tasks = generate_tasks(V2_DEV_SEED, suite="v2")
    for task in tasks:
        scenario_type = scenario_type_for_task(task)
        assert scenario_type in SCENARIO_TYPES
        if task["category"] == "coding":
            assert scenario_type == "cursor"
        if task["category"] == "reasoning":
            assert scenario_type == "spreadsheet"

    assert {scenario_type_for_task(t) for t in tasks} == SCENARIO_TYPES
