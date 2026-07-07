"""Budget guard: a minibench suite must stay affordable on the priciest model.

The pivot's cost rule (docs/PIVOT-PLAN.md): a full public-suite run — tasks x
trials x (expected tokens in + out) x price — must cost at most BUDGET_USD
against the most expensive standard-tier model in the committed catalog.
This module *shows the math* and exits non-zero when a suite breaks its budget,
so CI catches an expensive suite before anyone pays for it.

Token model (deliberately conservative):
  tokens_in  = prompt_chars / 4 + FIXED_OVERHEAD      (system prompt, wrapping)
  tokens_out = MAX_TOKENS cap of the single-model preset (worst case)

Usage:
    python -m agentbench.cost_check --tasks agentbench/tasks/minibench-core-v1.json \
        --trials 3
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# The budget guard is a worst-case ceiling: every call assumed to emit
# MAX_OUTPUT_TOKENS at the priciest catalog model's completion price. That cap
# is 4096 (reasoning-model headroom, see single_model_config), and reasoning
# runs genuinely cost more, so the ceiling is set to $15 for a full dev-slice
# run — still cheap enough to catch a suite that would cost hundreds, which is
# all the guard is for. Real answer-only runs cost cents.
BUDGET_USD = 15.00
FIXED_OVERHEAD_TOKENS = 60
MAX_OUTPUT_TOKENS = 4096  # matches single_model_config's max_tokens cap

CATALOG = Path(__file__).resolve().parents[1] / "backend" / "app" / "data" / "known_models_seed.json"


def priciest_model(catalog_path: Path = CATALOG) -> dict:
    models = json.loads(catalog_path.read_text(encoding="utf-8"))["models"]
    priced = [m for m in models if m.get("prompt_price") and m.get("completion_price")]
    return max(priced, key=lambda m: m["prompt_price"] + m["completion_price"])


def estimate_cost(tasks: list[dict], trials: int, prompt_price: float, completion_price: float) -> dict:
    calls = len(tasks) * trials
    tokens_in = sum(len(t["prompt"]) / 4 + FIXED_OVERHEAD_TOKENS for t in tasks) * trials
    tokens_out = calls * MAX_OUTPUT_TOKENS
    cost = tokens_in * prompt_price + tokens_out * completion_price
    return {
        "n_tasks": len(tasks),
        "trials": trials,
        "calls": calls,
        "est_tokens_in": round(tokens_in),
        "est_tokens_out": tokens_out,
        "est_cost_usd": round(cost, 4),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check a suite against the cost budget.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--tasks", help="published suite JSON")
    src.add_argument("--generate", help="estimate a generated suite (core|hard); "
                     "uses a throwaway seed — instance sizes, not instances, matter here")
    ap.add_argument("--per-category", type=int, default=5)
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--budget", type=float, default=BUDGET_USD)
    args = ap.parse_args(argv)

    if args.generate:
        from agentbench.minibench_gen import SUITES, generate_tasks

        tasks = generate_tasks(0, args.per_category, suite=args.generate)
        suite = {"suite": SUITES[args.generate]["name"], "tasks": tasks}
    else:
        suite = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    model = priciest_model()
    est = estimate_cost(
        suite["tasks"], args.trials, model["prompt_price"], model["completion_price"]
    )

    print(f"suite:          {suite.get('suite')}")
    print(f"priciest model: {model['model_id']} "
          f"(${model['prompt_price'] * 1e6:.2f}/M in, ${model['completion_price'] * 1e6:.2f}/M out)")
    for k, v in est.items():
        print(f"{k}: {v}")
    print(f"budget: ${args.budget:.2f}")

    if est["est_cost_usd"] > args.budget:
        print(f"FAIL: estimated ${est['est_cost_usd']} exceeds ${args.budget:.2f} budget")
        return 1
    print("OK: suite is within budget")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
