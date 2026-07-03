"""Filesystem locations of bundled presets and task suites.

Importable as ``from agentbench.resources import MOA_V1`` from any working
directory, so both callers and tests reference data files without hardcoding a
cwd-relative path.
"""
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent
PRESET_DIR = PKG_ROOT / "presets"
TASK_DIR = PKG_ROOT / "tasks"
RESULTS_DIR = PKG_ROOT / "results"

MOA_V1 = str(PRESET_DIR / "moa-v1.yaml")
SELF_MOA = str(PRESET_DIR / "self-moa-baseline.yaml")
CODING_V1 = str(TASK_DIR / "coding-v1.json")
