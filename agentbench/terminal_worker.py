"""Oracle-free child process for declarative terminal procedures."""
from __future__ import annotations

import json
import os
from typing import Any


RPC_LIMIT = 65_536


def run_terminal_procedure(
    connection: Any,
    commands: tuple[tuple[str, ...], ...],
    claimed_success: bool,
) -> None:
    try:
        for argv in commands:
            connection.send_bytes(
                json.dumps({"kind": "exec", "argv": list(argv)}, separators=(",", ":")).encode()
            )
            response = json.loads(connection.recv_bytes(RPC_LIMIT).decode("utf-8"))
            if not isinstance(response, dict) or response.get("kind") != "exec_result":
                raise RuntimeError("invalid terminal response")
            if response.get("returncode") != 0:
                raise RuntimeError("terminal command failed")
        connection.send_bytes(
            json.dumps(
                {
                    "kind": "result",
                    "result": {
                        "termination_reason": "completed",
                        "claimed_success": claimed_success,
                        "turns": len(commands),
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "cost_usd": 0.0,
                    },
                    "worker_pid": os.getpid(),
                },
                separators=(",", ":"),
            ).encode()
        )
    except BaseException:
        try:
            connection.send_bytes(b'{"kind":"error"}')
        except (OSError, BrokenPipeError):
            pass
    finally:
        connection.close()
