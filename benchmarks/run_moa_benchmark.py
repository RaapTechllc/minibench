#!/usr/bin/env python3
"""
Hermes MoA Benchmark Runner

Runs representative tasks across 3 MoA presets, verifies outputs,
and produces a comparison report.

Usage:
  export OPENROUTER_API_KEY=sk-or-...
  python benchmarks/run_moa_benchmark.py [--preset glm-tool-moa] [--trials 1] [--dry-run]

  Preset names are read from moa-presets.yaml (never hardcoded). Run with
  --list-tasks to see tasks; omit --preset to run every enabled preset.

Requires: hermes CLI on PATH, OpenRouter API key in ~/.hermes/.env or OPENROUTER_API_KEY
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BENCHMARK_DIR = Path(__file__).resolve().parent
TASKS_FILE = BENCHMARK_DIR / "tasks.json"
RESULTS_DIR = BENCHMARK_DIR / "results"
PRESETS_FILE = BENCHMARK_DIR / "moa-presets.yaml"


def load_presets(path: Path = PRESETS_FILE) -> list[str]:
    """Read the enabled preset names straight from moa-presets.yaml.

    The runner used to hardcode ``["budget-open", "balanced-hybrid",
    "high-quality"]`` while the YAML was rewritten to entirely different names —
    so a live run called a --model that no longer existed. Deriving the list from
    the config is the single source of truth; the CI smoke test (tests/) asserts
    this never drifts again.
    """
    import yaml  # local import so importing this module never hard-requires pyyaml

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    presets = (data.get("moa") or {}).get("presets") or {}
    return [name for name, cfg in presets.items() if (cfg or {}).get("enabled", True)]


# Derived at import from the YAML — never hardcoded (that was the drift bug).
PRESETS = load_presets()


@dataclass
class TaskResult:
    task_id: str
    preset: str
    trial: int
    success: bool
    score: float
    latency_s: float
    output_preview: str
    verification_detail: str
    error: str | None = None
    session_id: str | None = None


@dataclass
class PresetSummary:
    preset: str
    tasks_run: int = 0
    pass_count: int = 0
    pass_rate: float = 0.0
    avg_score: float = 0.0
    avg_latency_s: float = 0.0
    total_latency_s: float = 0.0
    errors: list[str] = field(default_factory=list)


def load_tasks() -> list[dict[str, Any]]:
    data = json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    tasks: list[dict[str, Any]] = []
    for cat_name, cat in data.get("categories", {}).items():
        for task in cat.get("tasks", []):
            tasks.append({**task, "category": cat_name})
    return tasks


def extract_code_block(text: str) -> str:
    match = re.search(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    return match.group(1) if match else text


def verify_output(output: str, verification: dict[str, Any]) -> tuple[bool, float, str]:
    vtype = verification.get("type", "contains_all")
    text = output.lower()
    code = extract_code_block(output).lower()

    if vtype == "contains_all":
        terms = verification.get("terms", [])
        missing = [t for t in terms if t.lower() not in text]
        if missing:
            return False, len(terms) - len(missing), f"Missing: {missing}"
        return True, 1.0, "All terms present"

    if vtype == "json_fields":
        try:
            # Try to find JSON in output
            json_match = re.search(r"\{[^{}]*\}", output, re.DOTALL)
            if not json_match:
                return False, 0.0, "No JSON object found"
            obj = json.loads(json_match.group())
            required = verification.get("required_fields", [])
            missing_fields = [f for f in required if f not in obj]
            if missing_fields:
                return False, 0.5, f"Missing fields: {missing_fields}"
            for term in verification.get("contains", []):
                if term.lower() not in json.dumps(obj).lower():
                    return False, 0.7, f"JSON missing term: {term}"
            return True, 1.0, "JSON valid with required fields"
        except json.JSONDecodeError as e:
            return False, 0.0, f"JSON parse error: {e}"

    if vtype == "code_block":
        terms = verification.get("contains", [])
        missing = [t for t in terms if t.lower() not in code]
        if missing:
            return False, max(0.0, 1.0 - len(missing) / max(len(terms), 1)), f"Code missing: {missing}"
        return True, 1.0, "Code block contains required elements"

    if vtype == "bullet_count":
        bullets = re.findall(r"^[\s]*[-*•]\s+", output, re.MULTILINE)
        min_bullets = verification.get("min_bullets", 3)
        terms = verification.get("contains", [])
        term_ok = all(t.lower() in text for t in terms)
        count_ok = len(bullets) >= min_bullets
        score = (0.5 if count_ok else 0.0) + (0.5 if term_ok else 0.0)
        detail = f"Bullets: {len(bullets)}/{min_bullets}, terms_ok={term_ok}"
        return score >= 1.0, score, detail

    if vtype == "numbered_steps":
        steps = re.findall(r"^\s*\d+[\.)]\s+", output, re.MULTILINE)
        min_steps = verification.get("min_steps", 3)
        terms = verification.get("contains", [])
        term_ok = all(t.lower() in text for t in terms)
        count_ok = len(steps) >= min_steps
        score = (0.5 if count_ok else 0.0) + (0.5 if term_ok else 0.0)
        detail = f"Steps: {len(steps)}/{min_steps}, terms_ok={term_ok}"
        return score >= 1.0, score, detail

    return False, 0.0, f"Unknown verification type: {vtype}"


def run_hermes_task(prompt: str, preset: str, timeout_s: int = 300) -> tuple[str, float, str | None, str | None]:
    """Run a single task via hermes -z with MoA preset."""
    env = os.environ.copy()
    env["PATH"] = f"{os.path.expanduser('~/.local/bin')}:{env.get('PATH', '')}"

    cmd = [
        "hermes",
        "-z", prompt,
        "--provider", "moa",
        "--model", preset,
        "--yolo",
    ]

    start = time.monotonic()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
            cwd=str(BENCHMARK_DIR),
        )
        latency = time.monotonic() - start
        output = result.stdout.strip() or result.stderr.strip()
        if result.returncode != 0:
            return output, latency, f"exit code {result.returncode}: {result.stderr[:500]}", None
        return output, latency, None, None
    except subprocess.TimeoutExpired:
        return "", time.monotonic() - start, f"timeout after {timeout_s}s", None
    except FileNotFoundError:
        return "", 0.0, "hermes CLI not found on PATH", None


def check_prerequisites() -> list[str]:
    issues: list[str] = []
    env_path = Path.home() / ".hermes" / ".env"
    if not env_path.exists() and not os.environ.get("OPENROUTER_API_KEY"):
        issues.append("No ~/.hermes/.env and no OPENROUTER_API_KEY — API calls will fail")
    try:
        subprocess.run(
            ["hermes", "moa", "list"],
            capture_output=True,
            timeout=30,
            env={**os.environ, "PATH": f"{os.path.expanduser('~/.local/bin')}:{os.environ.get('PATH', '')}"},
        )
    except FileNotFoundError:
        issues.append("hermes CLI not installed")
    return issues


def run_benchmark(
    presets: list[str],
    trials: int = 1,
    task_filter: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    tasks = load_tasks()
    if task_filter:
        tasks = [t for t in tasks if task_filter in t.get("id", "") or task_filter in t.get("category", "")]

    results: list[TaskResult] = []
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    for preset in presets:
        for task in tasks:
            for trial in range(1, trials + 1):
                task_id = task["id"]
                prompt = task["prompt"]
                print(f"[{preset}] {task_id} trial {trial}/{trials}...", flush=True)

                if dry_run:
                    results.append(TaskResult(
                        task_id=task_id, preset=preset, trial=trial,
                        success=False, score=0.0, latency_s=0.0,
                        output_preview="(dry run)", verification_detail="skipped",
                    ))
                    continue

                output, latency, error, session_id = run_hermes_task(prompt, preset)
                if error:
                    results.append(TaskResult(
                        task_id=task_id, preset=preset, trial=trial,
                        success=False, score=0.0, latency_s=latency,
                        output_preview=output[:300], verification_detail="",
                        error=error, session_id=session_id,
                    ))
                    continue

                success, score, detail = verify_output(output, task.get("verification", {}))
                results.append(TaskResult(
                    task_id=task_id, preset=preset, trial=trial,
                    success=success, score=score, latency_s=latency,
                    output_preview=output[:500], verification_detail=detail,
                    session_id=session_id,
                ))

    # Summarize per preset
    summaries: dict[str, PresetSummary] = {}
    for preset in presets:
        preset_results = [r for r in results if r.preset == preset]
        s = PresetSummary(preset=preset, tasks_run=len(preset_results))
        if preset_results:
            s.pass_count = sum(1 for r in preset_results if r.success)
            s.pass_rate = s.pass_count / len(preset_results)
            s.avg_score = sum(r.score for r in preset_results) / len(preset_results)
            s.avg_latency_s = sum(r.latency_s for r in preset_results) / len(preset_results)
            s.total_latency_s = sum(r.latency_s for r in preset_results)
            s.errors = [r.error for r in preset_results if r.error][:5]
        summaries[preset] = s

    report = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "presets": presets,
        "trials": trials,
        "task_count": len(tasks),
        "summaries": {k: asdict(v) for k, v in summaries.items()},
        "results": [asdict(r) for r in results],
    }

    out_path = RESULTS_DIR / f"run_{run_id}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nResults saved to {out_path}")
    return report


def print_comparison_table(report: dict[str, Any]) -> None:
    print("\n" + "=" * 72)
    print("MoA PRESET COMPARISON")
    print("=" * 72)
    print(f"{'Preset':<20} {'Pass Rate':>10} {'Avg Score':>10} {'Avg Latency':>12} {'Tasks':>8}")
    print("-" * 72)
    for preset, summary in report.get("summaries", {}).items():
        print(
            f"{preset:<20} "
            f"{summary['pass_rate']:>9.1%} "
            f"{summary['avg_score']:>10.2f} "
            f"{summary['avg_latency_s']:>10.1f}s "
            f"{summary['tasks_run']:>8}"
        )
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes MoA benchmark runner")
    parser.add_argument("--preset", action="append", dest="presets", help="Preset name (repeatable)")
    parser.add_argument("--trials", type=int, default=1, help="Trials per task")
    parser.add_argument("--filter", dest="task_filter", help="Filter tasks by id or category")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls")
    parser.add_argument("--list-tasks", action="store_true", help="List tasks and exit")
    args = parser.parse_args()

    if args.list_tasks:
        for t in load_tasks():
            print(f"{t['id']:12} [{t['category']}] {t['name']}")
        return 0

    presets = args.presets or PRESETS
    valid = set(load_presets())
    unknown = [p for p in presets if p not in valid]
    if unknown:
        print(f"ERROR: unknown preset(s) {unknown}. Defined in moa-presets.yaml: {sorted(valid)}",
              file=sys.stderr)
        return 2

    issues = check_prerequisites()
    if issues and not args.dry_run:
        print("Prerequisites check:", file=sys.stderr)
        for issue in issues:
            print(f"  ⚠ {issue}", file=sys.stderr)
        print("\nSet OPENROUTER_API_KEY or run: hermes config set OPENROUTER_API_KEY <key>", file=sys.stderr)
        print("Continuing anyway — runs may fail.\n", file=sys.stderr)

    report = run_benchmark(presets, trials=args.trials, task_filter=args.task_filter, dry_run=args.dry_run)
    print_comparison_table(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
