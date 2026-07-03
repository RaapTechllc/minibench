from agentbench.client import OpenAICompatClient, ChatMessage, Usage
from agentbench.tests.fakes import FakeTransport


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
    import pytest

    with pytest.raises(ValueError):
        OpenAICompatClient(provider="nope")
