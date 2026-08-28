"""Stdio MCP server: one tool, `recommend`, over the cached Usage Board."""
from __future__ import annotations

import json
import sys
from typing import Any

from agentbench.board import load_board
from agentbench.recommend import recommend_from_query

TOOLS = [
    {
        "name": "recommend",
        "description": (
            "Recommend an OpenRouter model from the cached Usage Board. "
            "Read-only compare. Does not call OpenRouter."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Classification tag or macro, e.g. code"},
                "budget": {"type": "number", "description": "Max blended USD per 1M tokens"},
                "max_latency_ms": {"type": "integer", "description": "Max cited latency in ms"},
            },
        },
    }
]


def handle_mcp(message: dict[str, Any], board: dict[str, Any] | None = None) -> dict[str, Any]:
    mid = message.get("id")
    method = message.get("method")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "minibench-recommend", "version": "1.0.0"},
            },
        }
    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        if name != "recommend":
            return {
                "jsonrpc": "2.0",
                "id": mid,
                "error": {"code": -32601, "message": f"unknown tool: {name}"},
            }
        board = board if board is not None else load_board()
        result = recommend_from_query(board, args)
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result)}],
                "isError": bool(result.get("error")),
            },
        }
    return {
        "jsonrpc": "2.0",
        "id": mid,
        "error": {"code": -32601, "message": f"unknown method: {method}"},
    }


def main() -> int:
    board = load_board()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        reply = handle_mcp(message, board)
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
