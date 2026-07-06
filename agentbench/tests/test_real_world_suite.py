"""Prove every real-world-v1 oracle actually discriminates.

The value of a benchmark is entirely in whether a wrong answer fails. A suite
whose graders pass everything (or fail everything) produces the un-trustworthy
numbers we are explicitly trying to avoid. So for every task we assert:

  - the embedded gold answer PASSES,
  - a plausible-but-wrong answer FAILS,
  - an empty answer FAILS.

The gold/wrong answers live in the suite JSON (`_gold` / `_wrong`) so they are
audited in the same file as the task and version-controlled beside it. run.py
ignores those keys — only id/category/prompt/verification drive a live run.
"""
import json

import pytest

from agentbench.grading import grade
from agentbench.resources import REAL_WORLD_V1

with open(REAL_WORLD_V1, encoding="utf-8") as fh:
    _SUITE = json.load(fh)
_TASKS = _SUITE["tasks"]
_IDS = [t["id"] for t in _TASKS]


def test_suite_metadata_and_uniqueness():
    assert _SUITE["suite"] == "real-world-v1"
    assert _SUITE.get("canary"), "suite must carry a canary string for contamination checks"
    assert len(_IDS) == len(set(_IDS)), "task ids must be unique"
    assert len(_TASKS) >= 10, "real-world suite should be broad enough to discriminate"


@pytest.mark.parametrize("task", _TASKS, ids=_IDS)
def test_every_task_has_gold_and_wrong(task):
    assert task.get("_gold"), f"{task['id']} missing a gold answer"
    assert task.get("_wrong"), f"{task['id']} missing a wrong answer"
    assert "verification" in task and "type" in task["verification"]


@pytest.mark.parametrize("task", _TASKS, ids=_IDS)
def test_gold_answer_passes(task):
    result = grade(task["verification"], task["_gold"])
    assert result.passed, f"{task['id']} gold answer should pass but did not: {result.detail}"


@pytest.mark.parametrize("task", _TASKS, ids=_IDS)
def test_wrong_answer_fails(task):
    result = grade(task["verification"], task["_wrong"])
    assert not result.passed, f"{task['id']} wrong answer should fail but passed: {result.detail}"


@pytest.mark.parametrize("task", _TASKS, ids=_IDS)
def test_empty_answer_fails(task):
    result = grade(task["verification"], "")
    assert not result.passed, f"{task['id']} empty answer must fail (rule zero)"
