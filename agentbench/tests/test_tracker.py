from agentbench.tracker import ModelInfo, diff_models, poll_openrouter
from agentbench.client import OpenAICompatClient
from agentbench.tests.fakes import FakeTransport

CATALOG = [
    {"id": "openai/gpt-x", "name": "GPT-X", "created": 100,
     "context_length": 128000, "pricing": {"prompt": "0.000005", "completion": "0.000015"}},
    {"id": "anthropic/claude-z", "name": "Claude Z", "created": 200,
     "pricing": {"prompt": "0.000003"}},
]


def test_from_openrouter_parses_pricing():
    m = ModelInfo.from_openrouter(CATALOG[0])
    assert m.id == "openai/gpt-x"
    assert m.context_length == 128000
    assert m.prompt_price == 0.000005
    assert m.completion_price == 0.000015


def test_diff_returns_only_new_models():
    current = [ModelInfo.from_openrouter(d) for d in CATALOG]
    new = diff_models({"openai/gpt-x"}, current)
    assert [m.id for m in new] == ["anthropic/claude-z"]


def test_diff_empty_when_all_known():
    current = [ModelInfo.from_openrouter(d) for d in CATALOG]
    assert diff_models({"openai/gpt-x", "anthropic/claude-z"}, current) == []


def test_poll_openrouter_through_client():
    client = OpenAICompatClient(provider="openrouter", transport=FakeTransport(models=CATALOG))
    infos = poll_openrouter(client)
    assert {m.id for m in infos} == {"openai/gpt-x", "anthropic/claude-z"}
