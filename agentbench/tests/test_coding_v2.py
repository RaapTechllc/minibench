"""Grader smoke tests for the harder coding-v2 suite.

These verify each oracle can fail deliberately-bad answers — a suite where cheap
models still score 100% is not useful.
"""
from agentbench.grading import grade
from agentbench.resources import CODING_V2
from agentbench.run import load_tasks


def _load_v2_tasks():
    _, tasks = load_tasks(CODING_V2)
    return {t["id"]: t for t in tasks}


def test_coding_v2_topo_sort_fails_naive_cycle():
    tasks = _load_v2_tasks()
    bad = "```python\ndef topo_sort(n, edges):\n    return list(range(n))\n```"
    assert not grade(tasks["code-topo-sort"]["verification"], bad).passed


def test_coding_v2_sliding_window_fails_wrong():
    tasks = _load_v2_tasks()
    wrong = "```python\ndef max_sliding_window(nums, k):\n    return [0] * (len(nums) - k + 1)\n```"
    assert not grade(tasks["code-sliding-window-max"]["verification"], wrong).passed


def test_coding_v2_min_stack_fails_broken_getmin():
    tasks = _load_v2_tasks()
    broken = "```python\nclass MinStack:\n    def __init__(self):\n        self.s = []\n    def push(self, x):\n        self.s.append(x)\n    def pop(self):\n        self.s.pop()\n    def top(self):\n        return self.s[-1]\n    def getMin(self):\n        return self.s[0]\n```"
    assert not grade(tasks["code-min-stack"]["verification"], broken).passed


def test_coding_v2_clock_angle_trap():
    tasks = _load_v2_tasks()
    assert not grade(tasks["reason-clock-angle"]["verification"], "90").passed
    assert grade(tasks["reason-clock-angle"]["verification"], "7.5").passed


def test_coding_v2_average_speed_trap():
    tasks = _load_v2_tasks()
    assert not grade(tasks["reason-average-speed-trap"]["verification"], "45").passed
    assert grade(tasks["reason-average-speed-trap"]["verification"], "40 mph").passed
