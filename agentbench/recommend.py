"""Read-only model recommend over a cached Usage Board."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from agentbench.board import _task_share, citation, load_board


def recommend(
    board: dict[str, Any],
    *,
    task: str | None = None,
    budget: float | None = None,
    max_latency_ms: int | None = None,
) -> dict[str, Any]:
    as_of = (board.get("meta") or {}).get("as_of") or ""
    cite = (board.get("meta") or {}).get("citation") or citation(as_of)
    candidates: list[dict[str, Any]] = []
    for row in board.get("rows") or []:
        if task:
            share = _task_share(row, task)
            if share is None:
                continue
        else:
            share = _task_share(row, "") or 0.0
        price = row.get("blended_per_million")
        if budget is not None and (price is None or price > budget):
            continue
        latency = row.get("latency_ms")
        if max_latency_ms is not None:
            if latency is None or latency > max_latency_ms:
                continue
        candidates.append({**row, "_share": share if share is not None else 0.0})

    candidates.sort(
        key=lambda r: (
            -float(r.get("_share") or 0.0),
            float(r.get("blended_per_million") if r.get("blended_per_million") is not None else 1e18),
            float(r.get("latency_ms") if r.get("latency_ms") is not None else 1e18),
            r["id"],
        )
    )
    if not candidates:
        return {
            "pick": None,
            "reason": "no model on the cached board fits task/budget/latency",
            "citation": cite,
            "as_of": as_of,
            "live": bool((board.get("meta") or {}).get("live") or board.get("live")),
            "compared": 0,
        }
    pick = {k: v for k, v in candidates[0].items() if not k.startswith("_")}
    return {
        "pick": pick,
        "reason": "highest task share, then lowest blended price, then lowest latency",
        "citation": cite,
        "as_of": as_of,
        "live": bool((board.get("meta") or {}).get("live") or board.get("live")),
        "compared": len(candidates),
    }


def recommend_from_query(board: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
    """REST/MCP adapter. Rejects any client-supplied key field."""
    lowered = {str(k).lower(): v for k, v in query.items()}
    for banned in ("api_key", "key", "authorization", "token", "openrouter_api_key"):
        if banned in lowered and lowered[banned] not in (None, ""):
            as_of = (board.get("meta") or {}).get("as_of") or ""
            return {
                "pick": None,
                "error": "client-supplied key is not accepted",
                "citation": citation(as_of),
                "as_of": as_of,
                "live": False,
            }
    task = query.get("task")
    task_s = str(task).strip() if task not in (None, "") else None
    budget = _opt_float(query.get("budget"))
    latency = _opt_int(query.get("max_latency_ms"))
    return recommend(board, task=task_s, budget=budget, max_latency_ms=latency)


def _opt_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _opt_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(float(value))


def dogfood(*, task: str = "code", budget: float = 5.0, max_latency_ms: int | None = 5000) -> dict[str, Any]:
    result = recommend(load_board(), task=task, budget=budget, max_latency_ms=max_latency_ms)
    pick = result.get("pick") or {}
    print("MiniBench recommend (cached/fixture board)")
    print(f"live={result['live']} compared={result['compared']}")
    if pick:
        print(f"pick={pick['id']} blended_per_million={pick.get('blended_per_million')} latency_ms={pick.get('latency_ms')}")
        print(f"openrouter={pick.get('openrouter_url')}")
    else:
        print(f"miss: {result.get('reason')}")
    print(result["citation"])
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recommend over the cached OpenRouter Usage Board.")
    parser.add_argument("--task", default="code")
    parser.add_argument("--budget", type=float, default=5.0)
    parser.add_argument("--max-latency-ms", type=int, default=5000)
    parser.add_argument("--dogfood", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = dogfood(task=args.task, budget=args.budget, max_latency_ms=args.max_latency_ms)
    if args.json:
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0 if result.get("pick") else 2


if __name__ == "__main__":
    raise SystemExit(main())
