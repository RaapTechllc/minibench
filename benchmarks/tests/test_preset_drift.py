"""Smoke test: the runner's presets must match moa-presets.yaml.

This is the guard the brief asked for — config drift (the runner hardcoding
preset names the YAML no longer defines) is now caught in CI instead of failing
silently against a live API.
"""
import sys
from pathlib import Path

import yaml

BENCH_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH_DIR))

import run_moa_benchmark as runner  # noqa: E402


def _yaml_presets():
    data = yaml.safe_load((BENCH_DIR / "moa-presets.yaml").read_text())
    return set((data["moa"]["presets"]).keys())


def test_runner_presets_match_yaml():
    assert set(runner.PRESETS), "runner derived an empty preset list"
    assert set(runner.PRESETS) <= _yaml_presets()


def test_no_stale_hardcoded_presets():
    # The names that caused the original drift bug must not reappear.
    stale = {"budget-open", "balanced-hybrid", "high-quality"}
    assert stale.isdisjoint(set(runner.PRESETS))


def test_load_presets_is_the_source_of_truth():
    assert set(runner.PRESETS) == set(runner.load_presets())
