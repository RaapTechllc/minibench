from agentbench.config import MoAConfig
from agentbench.moa import MoAModel
from agentbench.tests.fakes import FakeTransport
from agentbench.client import OpenAICompatClient


def _client(transport):
    return OpenAICompatClient(provider="openrouter", transport=transport)


def _cfg(**over):
    base = {
        "name": "t",
        "proposers": [{"model": "p1"}, {"model": "p2"}, {"model": "p3"}],
        "aggregator": {"model": "agg"},
    }
    base.update(over)
    return MoAConfig.from_dict(base)


def test_moa_calls_all_proposers_then_aggregator():
    seen = []

    def responder(payload):
        model = payload["model"]
        seen.append(model)
        return f"resp-{model}", {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001}

    transport = FakeTransport(responder=responder)
    moa = MoAModel(_cfg(), _client(transport))
    result = moa.generate("What is 2+2?")

    # 3 proposers + 1 aggregator = 4 calls; final text is the aggregator's.
    assert result.n_calls == 4
    assert seen[-1] == "agg"
    assert set(seen[:3]) == {"p1", "p2", "p3"}
    assert result.text == "resp-agg"


def test_moa_rolls_up_cost_and_tokens():
    def responder(payload):
        return "x", {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.002}

    moa = MoAModel(_cfg(), _client(FakeTransport(responder=responder)))
    r = moa.generate("q")
    assert r.prompt_tokens == 40  # 4 calls * 10
    assert r.completion_tokens == 20
    assert abs(r.cost_usd - 0.008) < 1e-9  # 4 * 0.002


def test_aggregator_receives_numbered_references():
    def responder(payload):
        return f"resp-{payload['model']}", {}

    transport = FakeTransport(responder=responder)
    MoAModel(_cfg(), _client(transport)).generate("q")

    # The aggregator request (last) must carry all three proposer answers as refs.
    agg_req = transport.requests[-1]
    system = agg_req["messages"][0]["content"]
    assert "1. resp-p1" in system
    assert "2. resp-p2" in system
    assert "3. resp-p3" in system


def test_self_moa_samples_single_model_n_times():
    calls = []

    def responder(payload):
        calls.append(payload["model"])
        return "x", {}

    cfg = _cfg(
        self_moa=True,
        self_moa_samples=4,
        proposers=[{"model": "solo"}],
        aggregator={"model": "solo"},
    )
    MoAModel(cfg, _client(FakeTransport(responder=responder))).generate("q")
    # 4 samples of "solo" + 1 aggregator (also "solo") = 5 calls, one model.
    assert calls.count("solo") == 5


def test_missing_cost_yields_none():
    # If any provider omits cost we can't claim a total (Ollama local case).
    def responder(payload):
        return "x", {"prompt_tokens": 1, "completion_tokens": 1}  # no cost key

    r = MoAModel(_cfg(), _client(FakeTransport(responder=responder))).generate("q")
    assert r.cost_usd is None
    assert r.total_tokens == 8
