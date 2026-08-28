"""Public Usage Board reads — cached snapshot only. No recommend. No live OpenRouter."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/v1/openrouter", tags=["openrouter-board"])

DEFAULT_FIXTURE = Path(__file__).resolve().parent / "data" / "openrouter_board_fixture.json"
CITE_TEMPLATE = "Source: OpenRouter (openrouter.ai/rankings), as of {as_of}. CC BY 4.0."


def snapshot_path() -> Path:
    """Board path when set and present; otherwise the committed fixture."""
    override = (os.environ.get("OPENROUTER_BOARD_PATH") or "").strip()
    if override:
        path = Path(override)
        if path.exists():
            return path
    return DEFAULT_FIXTURE


def load_snapshot() -> dict[str, Any]:
    path = snapshot_path()
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text())


def _task_share(row: dict[str, Any], task: str) -> float | None:
    shares = row.get("task_shares") or {}
    if task in shares:
        return shares[task]
    matches = [v for k, v in shares.items() if k == task or k.startswith(f"{task}:")]
    return max(matches) if matches else None


def compare_rows(board: dict[str, Any], by: str, task: str | None = None) -> list[dict[str, Any]]:
    rows = list(board.get("rows") or [])
    if by == "cost":
        rows = [r for r in rows if r.get("blended_per_million") is not None]
        rows.sort(key=lambda r: (r["blended_per_million"], r["id"]))
        return rows
    if by == "latency":
        rows = [r for r in rows if r.get("latency_ms") is not None]
        rows.sort(key=lambda r: (r["latency_ms"], r["id"]))
        return rows
    if by == "task":
        if not task:
            raise HTTPException(400, "task is required for best-by-task")
        scored = []
        for row in rows:
            share = _task_share(row, task)
            if share is None:
                continue
            scored.append((share, row))
        scored.sort(key=lambda pair: (-pair[0], pair[1].get("blended_per_million") or 1e9, pair[1]["id"]))
        return [row for _, row in scored]
    raise HTTPException(400, "by must be cost, task, or latency")


def _payload(board: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    meta = dict(board.get("meta") or {})
    as_of = meta.get("as_of") or ""
    meta.setdefault("citation", CITE_TEMPLATE.format(as_of=as_of))
    return {"meta": meta, "rows": rows}


@router.get("/board")
def get_board() -> dict[str, Any]:
    try:
        board = load_snapshot()
    except FileNotFoundError:
        raise HTTPException(
            503,
            "Usage Board snapshot missing; poll with a key or ship the fixture.",
        )
    return _payload(board, list(board.get("rows") or []))


@router.get("/compare/best-by-cost")
def compare_cost() -> dict[str, Any]:
    board = _require_board()
    return _payload(board, compare_rows(board, "cost"))


@router.get("/compare/best-by-task")
def compare_task(task: str = Query(..., min_length=1)) -> dict[str, Any]:
    board = _require_board()
    return _payload(board, compare_rows(board, "task", task))


@router.get("/compare/best-by-latency")
def compare_latency() -> dict[str, Any]:
    board = _require_board()
    return _payload(board, compare_rows(board, "latency"))


def _require_board() -> dict[str, Any]:
    try:
        return load_snapshot()
    except FileNotFoundError:
        raise HTTPException(503, "Usage Board snapshot missing; poll with a key or ship the fixture.")
