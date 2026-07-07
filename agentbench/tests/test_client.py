import pytest

from agentbench.client import (
    HttpxTransport,
    InfraError,
    OpenAICompatClient,
    ChatMessage,
    Usage,
)
from agentbench.tests.fakes import FakeTransport


class _FakeResponse:
    def __init__(self, status_code: int, body: dict | None = None, headers: dict | None = None):
        self.status_code = status_code
        self._body = body or {}
        self.headers = headers or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            raise httpx.HTTPStatusError(f"HTTP {self.status_code}", request=None, response=None)


def _transport_with(responses):
    """HttpxTransport whose POST pops scripted responses; sleeps are recorded."""
    calls = {"n": 0}
    sleeps: list[float] = []

    def fake_post(url, headers=None, json=None, timeout=None):
        resp = responses[min(calls["n"], len(responses) - 1)]
        calls["n"] += 1
        if isinstance(resp, Exception):
            raise resp
        return resp

    t = HttpxTransport(post=fake_post, sleep=sleeps.append)
    return t, calls, sleeps


def test_provider_prefix_stripped_before_upstream():
    transport = FakeTransport()
    client = OpenAICompatClient(provider="openrouter", transport=transport)
    client.chat("openrouter/anthropic/claude-sonnet-4", [ChatMessage("user", "hi")])
    # Upstream should not see our routing prefix.
    assert transport.requests[-1]["model"] == "anthropic/claude-sonnet-4"


def test_usage_include_flag_sent():
    transport = FakeTransport()
    client = OpenAICompatClient(provider="openrouter", transport=transport)
    client.chat("m", [ChatMessage("user", "hi")])
    assert transport.requests[-1]["usage"] == {"include": True}


def test_usage_from_response_reads_cost_and_provider():
    body = {"usage": {"prompt_tokens": 3, "completion_tokens": 4, "cost": 0.01}, "provider": "Together"}
    u = Usage.from_response(body)
    assert u.cost_usd == 0.01
    assert u.total_tokens == 7
    assert u.provider == "Together"


def test_latency_measured_from_injected_clock():
    transport = FakeTransport()
    client = OpenAICompatClient(provider="openrouter", transport=transport)
    ticks = iter([1_000_000_000, 1_250_000_000])  # 250ms apart, in ns
    res = client.chat("m", [ChatMessage("user", "hi")], clock=lambda: next(ticks))
    assert res.latency_ms == 250


def test_unknown_provider_rejected():
    with pytest.raises(ValueError):
        OpenAICompatClient(provider="nope")


# ── retry / backoff (infra errors must never score as model failures) ─────────

OK_BODY = {"choices": [{"message": {"content": "42"}}], "usage": {}}


def test_retryable_status_then_success():
    t, calls, sleeps = _transport_with([
        _FakeResponse(429), _FakeResponse(503), _FakeResponse(200, OK_BODY),
    ])
    body = t.post_json("http://x/chat/completions", {}, {})
    assert body == OK_BODY
    assert calls["n"] == 3
    assert len(sleeps) == 2


def test_exhausted_retries_raise_infra_error():
    t, calls, _ = _transport_with([_FakeResponse(503)])
    with pytest.raises(InfraError) as exc:
        t.post_json("http://x/chat/completions", {}, {})
    assert calls["n"] == 5  # MAX_ATTEMPTS
    assert exc.value.status == 503
    assert exc.value.attempts == 5


def test_non_retryable_4xx_raises_immediately():
    import httpx

    t, calls, _ = _transport_with([_FakeResponse(401)])
    with pytest.raises(httpx.HTTPStatusError):
        t.post_json("http://x/chat/completions", {}, {})
    assert calls["n"] == 1  # config bug: no retries


def test_timeout_retried_then_infra_error():
    import httpx

    t, calls, _ = _transport_with([httpx.ConnectTimeout("boom")])
    with pytest.raises(InfraError):
        t.post_json("http://x/chat/completions", {}, {})
    assert calls["n"] == 5


def test_retry_after_header_honored():
    t, _, sleeps = _transport_with([
        _FakeResponse(429, headers={"Retry-After": "7"}), _FakeResponse(200, OK_BODY),
    ])
    t.post_json("http://x/chat/completions", {}, {})
    assert sleeps == [7.0]


def test_negative_retry_after_does_not_crash_sleep():
    # A malformed "Retry-After: -1" must be clamped to >= 0, not passed to
    # time.sleep (which raises on negative delays and would abort the whole run).
    t, _, sleeps = _transport_with([
        _FakeResponse(429, headers={"Retry-After": "-1"}), _FakeResponse(200, OK_BODY),
    ])
    t.post_json("http://x/chat/completions", {}, {})
    assert sleeps == [0.0]


def test_empty_completion_retried_once_then_model_failure():
    empty = {"choices": [{"message": {"content": ""}}]}
    transport = FakeTransport(responder=lambda p: ("", {}))
    client = OpenAICompatClient(provider="openrouter", transport=transport)
    res = client.chat("m", [ChatMessage("user", "hi")])
    # Retried exactly once, then surfaced as an empty (failing) answer.
    assert len(transport.requests) == 2
    assert res.text == ""


def test_top_p_sent_when_set():
    transport = FakeTransport()
    client = OpenAICompatClient(provider="openrouter", transport=transport)
    client.chat("m", [ChatMessage("user", "hi")], top_p=1.0, temperature=0.0)
    assert transport.requests[-1]["top_p"] == 1.0
    assert transport.requests[-1]["temperature"] == 0.0
