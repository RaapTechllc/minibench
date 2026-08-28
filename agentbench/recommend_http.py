"""Localhost-only recommend REST. Not mounted on the CORS * FastAPI app."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from agentbench.board import load_board
from agentbench.openrouter_data import redact_secrets
from agentbench.recommend import recommend_from_query

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3072


def safe_access_log(text: str) -> str:
    """Access-log line with secrets and query strings stripped (GATE-1)."""
    rendered = redact_secrets(text)
    if "?" in rendered:
        rendered = rendered.split("?", 1)[0] + "?[redacted]"
    return rendered


def handle_http(method: str, target: str, board: dict[str, Any] | None = None) -> tuple[int, dict[str, str], str]:
    headers = {"Content-Type": "application/json", "Cache-Control": "no-store"}
    if method != "GET":
        return 405, headers, json.dumps({"error": "GET only"})
    parsed = urlparse(target)
    path = parsed.path.rstrip("/") or "/"
    if path not in ("/recommend", "/health"):
        return 404, headers, json.dumps({"error": "not found"})
    if path == "/health":
        return 200, headers, json.dumps({"status": "ok", "service": "minibench-recommend", "bind": DEFAULT_HOST})
    query = {k: v[0] if v else "" for k, v in parse_qs(parsed.query, keep_blank_values=True).items()}
    board = board if board is not None else load_board()
    result = recommend_from_query(board, query)
    status = 400 if result.get("error") else 200
    if result.get("pick") is None and not result.get("error"):
        status = 404
    return status, headers, json.dumps(result)


class _Handler(BaseHTTPRequestHandler):
    board: dict[str, Any] | None = None

    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
        sys_stderr = __import__("sys").stderr
        sys_stderr.write("recommend_http: " + safe_access_log(fmt % args) + "\n")

    def do_GET(self) -> None:  # noqa: N802
        status, headers, body = handle_http("GET", self.path, self.board)
        payload = body.encode("utf-8")
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def serve(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("recommend HTTP must bind localhost")
    _Handler.board = load_board()
    httpd = ThreadingHTTPServer((host, port), _Handler)
    print(f"minibench recommend listening on http://{host}:{port}/recommend", flush=True)
    httpd.serve_forever()


def main() -> int:
    serve()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
