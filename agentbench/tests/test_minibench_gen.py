"""Minibench generator: determinism, graders that pass gold and fail garbage.

The bad-answer checks below ARE the brief's "pilot each grader against a
deliberately-bad answer" guardrail, encoded as a permanent test.
"""
import json

import pytest

from agentbench.grading import grade
from agentbench.minibench_gen import CANARY, DEV_SEED, SUITES, generate_tasks, write_suite

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
    }
    for task in generate_tasks(DEV_SEED, suite=suite):
        bad = bad_by_type[task["verification"]["type"]]
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
])
def test_repo_suite_file_is_current(suite, filename):
    """The committed suite must equal what the generator produces for its seed —
    regenerate with `python -m agentbench.minibench_gen` if this fails."""
    from pathlib import Path

    suite_path = Path(__file__).resolve().parents[1] / "tasks" / filename
    committed = json.loads(suite_path.read_text(encoding="utf-8"))
    fresh = [
        {k: v for k, v in t.items() if k != "_gold"}
        for t in generate_tasks(committed["generator_seed"], suite=suite)
    ]
    assert committed["tasks"] == fresh
    assert committed["suite"] == SUITES[suite]["name"]
    assert committed["canary"] == SUITES[suite]["canary"]
