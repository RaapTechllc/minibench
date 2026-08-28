"""GET-only OpenRouter Data API client (Mode A / GATE-1).

Allowlisted paths only. The key is read from the process environment (or an
explicit constructor arg used by tests). It is never logged, never returned,
and never accepted as a per-request argument.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlencode

ALLOWED_PATHS = frozenset(
    {
        "/models",
        "/datasets/rankings-daily",
        "/benchmarks",
        "/classifications/task",
    }
)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
APP_REFERER = "https://github.com/RaapTechllc/minibench"
APP_TITLE = "MiniBench"
FIXTURE_PATH = Path(__file__).resolve().parent / "data" / "openrouter_data_fixture.json"

_KEY_RE = re.compile(r"sk-or-v1-[A-Za-z0-9]+")


class GetTransport(Protocol):
    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        ...


def redact_secrets(text: str) -> str:
    """Strip OpenRouter-shaped keys from a string (errors, logs)."""
    return _KEY_RE.sub("[redacted]", text)


class DataAPIError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(redact_secrets(message))


def _normalize_path(path: str) -> str:
    path = (path or "").split("?", 1)[0].strip()
    if not path.startswith("/"):
        path = "/" + path
    return path.rstrip("/") if path != "/" else path


class DataAPIClient:
    """Allowlisted GET client. ``api_key=None`` reads ``OPENROUTER_API_KEY``."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        transport: GetTransport | None = None,
    ) -> None:
        env_key = os.environ.get("OPENROUTER_API_KEY") or None
        raw = api_key if api_key is not None else env_key
        self._api_key = raw.strip() if isinstance(raw, str) and raw.strip() else None
        self.base_url = base_url.rstrip("/")
        self._transport = transport

    def can_live_fetch(self) -> bool:
        """True when a process key is present (cron / live poll)."""
        return bool(self._api_key)

    def _headers(self) -> dict[str, str]:
        headers = {
            "HTTP-Referer": APP_REFERER,
            "X-Title": APP_TITLE,
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        normalized = _normalize_path(path)
        if normalized not in ALLOWED_PATHS:
            raise DataAPIError(f"path not allowlisted for Mode A: {normalized}")
        if self._transport is None and not self._api_key:
            raise DataAPIError("no OPENROUTER_API_KEY; load the committed fixture instead")
        url = f"{self.base_url}{normalized}"
        if params:
            url = f"{url}?{urlencode(params)}"
        transport = self._transport or _HttpxGetTransport()
        try:
            body = transport.get_json(url, self._headers())
        except Exception as exc:  # noqa: BLE001 — redact before it escapes
            raise DataAPIError(f"Data API GET failed: {exc}") from None
        if not isinstance(body, dict):
            raise DataAPIError("Data API returned a non-object body")
        return body


class _HttpxGetTransport:
    """Real GET via the existing agentbench httpx dependency."""

    def get_json(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        import httpx

        resp = httpx.get(url, headers=headers, timeout=60.0)
        resp.raise_for_status()
        return resp.json()


def load_fixture_payloads(path: Path | None = None) -> dict[str, Any]:
    """Load the committed four-feed replay. Always ``live: false``."""
    raw = json.loads((path or FIXTURE_PATH).read_text())
    return {
        "live": False,
        "feeds": {
            "/models": raw["models"],
            "/datasets/rankings-daily": raw["rankings"],
            "/benchmarks": raw["benchmarks"],
            "/classifications/task": raw["classifications"],
        },
        "source": "fixture",
    }


def fetch_payloads(client: DataAPIClient | None = None) -> dict[str, Any]:
    """Live poll when a key exists; otherwise the committed fixture.

    Injected transports are treated as non-live (tests / fakes).
    """
    client = client or DataAPIClient()
    if client._transport is None and not client._api_key:
        return load_fixture_payloads()
    if client._transport is not None and not client._api_key:
        # Fake transport, no key: still fetch through the allowlist, label fixture-like.
        feeds = {path: client.get(path) for path in sorted(ALLOWED_PATHS)}
        return {"live": False, "feeds": feeds, "source": "transport"}
    if client._transport is not None:
        feeds = {path: client.get(path) for path in sorted(ALLOWED_PATHS)}
        return {"live": False, "feeds": feeds, "source": "transport"}
    feeds = {path: client.get(path) for path in sorted(ALLOWED_PATHS)}
    return {"live": True, "feeds": feeds, "source": "openrouter"}
