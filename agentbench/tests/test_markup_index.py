"""D1 open-weight provider markup / serving-efficiency index."""
from __future__ import annotations

import json
import math
import os
import re
from copy import deepcopy
from pathlib import Path

import pytest

from agentbench.markup_index import (
    DATA_DIR,
    DEFAULT_PROFILE_ID,
    ENDPOINT_LEDGER_PATH,
    OUTPUT_KIND,
    OUTPUT_SCHEMA_PATH,
    PARAM_LEDGER_PATH,
    MarkupIndexError,
    blended_price,
    compute_markup_index,
    format_table,
    load_endpoint_ledger,
    load_param_ledger,
    main,
    validate_against_schema,
)
from agentbench.openrouter_data import ALLOWED_PATHS, DataAPIClient, DataAPIError

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "markup"
SYNTHETIC_PARAMS = FIXTURE_DIR / "synthetic_params.json"
SYNTHETIC_ENDPOINTS = FIXTURE_DIR / "synthetic_endpoints.json"
DOCS_PATH = Path(__file__).resolve().parents[2] / "docs" / "provider-markup-index.md"
FORBIDDEN_COPY = re.compile(r"\b(capability|intelligence|value)\b", re.IGNORECASE)
SOURCE_URL_FIELDS = ("params_source_url", "price_source_url")
AS_OF_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class _RecordingTransport:
    def get_json(self, url: str, headers: dict[str, str]) -> dict:
        return {"data": []}


def _four_sigfigs(number: float) -> float:
    return float(f"{number:.4g}")


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _params_row(**overrides: object) -> dict:
    row = {
        "model_id": "synthetic/open-moe",
        "total_params_b": 100,
        "active_params_b": 37,
        "count_convention": "SYNTHETIC: 100B total / 37B active",
        "params_source_url": "https://example.com/synthetic/params",
        "params_tier": "disclosed",
        "as_of": "2026-10-15",
    }
    row.update(overrides)
    return row


def _endpoint_row(**overrides: object) -> dict:
    row = {
        "model_id": "synthetic/open-moe",
        "provider": "host-a",
        "price_in_per_m": 0.4,
        "price_out_per_m": 2.0,
        "tier": "standard",
        "quantization": "bf16",
        "price_source_url": "https://example.com/synthetic/host-a",
        "fetched_at": "2026-10-15",
    }
    row.update(overrides)
    return row


def _params_ledger(rows: list[dict], **overrides: object) -> dict:
    payload = {
        "ledger_version": "1",
        "live": False,
        "synthetic": True,
        "label": "SYNTHETIC fixture for unit tests. Not listed prices. Do not copy into the real ledger.",
        "as_of": "2026-10-15",
        "rows": rows,
    }
    payload.update(overrides)
    return payload


def _endpoint_ledger(rows: list[dict], **overrides: object) -> dict:
    payload = {
        "ledger_version": "1",
        "live": False,
        "synthetic": True,
        "label": "SYNTHETIC fixture for unit tests. Not listed prices. Do not copy into the real ledger.",
        "as_of": "2026-10-15",
        "rows": rows,
    }
    payload.update(overrides)
    return payload


def _expect_reason(exc: MarkupIndexError, reason: str) -> None:
    assert exc.reason == reason, (exc.reason, str(exc))


def _walk_strings(node: object) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key, item in node.items():
            if key in {"description", "title", "label"} and isinstance(item, str):
                found.append(item)
            found.extend(_walk_strings(item))
    elif isinstance(node, list):
        for item in node:
            found.extend(_walk_strings(item))
    return found


def _output_keys(node: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(node, dict):
        keys.update(node)
        for item in node.values():
            keys.update(_output_keys(item))
    elif isinstance(node, list):
        for item in node:
            keys.update(_output_keys(item))
    return keys


# --- A1 / AC-4 ---


def test_a1_loader_rejects_missing_params_source_url(tmp_path: Path) -> None:
    row = _params_row()
    del row["params_source_url"]
    path = _write_json(tmp_path / "params.json", _params_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_param_ledger(path)
    _expect_reason(exc.value, "missing_params_source_url")


def test_a1_loader_rejects_missing_as_of(tmp_path: Path) -> None:
    row = _params_row()
    del row["as_of"]
    path = _write_json(tmp_path / "params.json", _params_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_param_ledger(path)
    _expect_reason(exc.value, "missing_as_of")


def test_a1_check_exits_nonzero_on_missing_citation(tmp_path: Path) -> None:
    row = _params_row()
    del row["params_source_url"]
    params = _write_json(tmp_path / "params.json", _params_ledger([row]))
    endpoints = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([_endpoint_row()]))
    assert main(["--check", "--params", str(params), "--endpoints", str(endpoints)]) != 0


# --- A2 / AC-5 ---


def test_a2_seed_param_counts_match_notes_2_1() -> None:
    ledger = load_param_ledger(PARAM_LEDGER_PATH)
    by_id = {row["model_id"]: row for row in ledger["rows"]}

    deepseek = by_id["deepseek-ai/DeepSeek-V3"]
    assert deepseek["total_params_b"] == 671
    assert deepseek["active_params_b"] == 37

    gpt_oss = by_id["openai/gpt-oss-120b"]
    assert gpt_oss["total_params_b"] == 116.83
    assert gpt_oss["active_params_b"] == 5.13

    grok = by_id["xai/grok-1"]
    assert grok["total_params_b"] == 314

    qwen = by_id["Qwen/Qwen3-30B-A3B"]
    assert qwen["total_params_b"] == 30.5
    assert qwen["active_params_b"] == 3.4


# --- A3 price citation ---


def test_a3_missing_price_source_url_fails(tmp_path: Path) -> None:
    row = _endpoint_row()
    del row["price_source_url"]
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "missing_price_source_url")


def test_a3_missing_fetched_at_fails(tmp_path: Path) -> None:
    row = _endpoint_row()
    del row["fetched_at"]
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "missing_fetched_at")


def test_a3_null_price_without_unlisted_fails(tmp_path: Path) -> None:
    row = _endpoint_row(price_in_per_m=None, price_out_per_m=None)
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "unlisted_price_unmarked")


def test_a3_null_price_marked_unlisted_is_accepted(tmp_path: Path) -> None:
    row = _endpoint_row(price_in_per_m=None, price_out_per_m=None, unlisted=True)
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    loaded = load_endpoint_ledger(path)
    assert loaded["rows"][0]["unlisted"] is True
    assert loaded["rows"][0]["price_in_per_m"] is None


def test_a3_real_ledger_never_defaults_or_interpolates_prices() -> None:
    ledger = load_endpoint_ledger(ENDPOINT_LEDGER_PATH)
    for row in ledger["rows"]:
        if row.get("unlisted"):
            assert row.get("price_in_per_m") is None
            assert row.get("price_out_per_m") is None
            continue
        assert isinstance(row["price_in_per_m"], (int, float))
        assert isinstance(row["price_out_per_m"], (int, float))
        assert row["price_source_url"].startswith("https://")
        assert AS_OF_RE.match(row["fetched_at"])


# --- A4 / AC-6 ---


def test_a4_hand_computed_minibench_1_3_matches_four_sig_figs() -> None:
    params = load_param_ledger(SYNTHETIC_PARAMS)
    endpoints = load_endpoint_ledger(SYNTHETIC_ENDPOINTS)
    index = compute_markup_index(params, endpoints, profile_id="minibench-1:3", as_of="2026-10-15")
    model = index["models"][0]
    row = model["providers"][0]
    expected_blended = (0.4 + 3 * 2.0) / 4
    expected_index = expected_blended / 37
    assert expected_blended == 1.6
    assert _four_sigfigs(row["dollars_per_1m_per_active_b"]) == _four_sigfigs(expected_index)
    assert row["provider"] == "host-a"
    assert row["price_source"].startswith("https://")
    assert row["as_of"]
    assert row["profile_id"] == "minibench-1:3"
    assert row["cache_assumption"] == "none"


# --- A5 baseline / markup range ---


def test_a5_baseline_is_lowest_standard_listed_price_and_output_is_a_range() -> None:
    params = _params_ledger([_params_row()])
    endpoints = _endpoint_ledger(
        [
            _endpoint_row(provider="cheap", price_in_per_m=0.10, price_out_per_m=0.10),
            _endpoint_row(
                provider="dear",
                price_in_per_m=0.40,
                price_out_per_m=0.40,
                price_source_url="https://example.com/synthetic/dear",
            ),
        ]
    )
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    model = index["models"][0]
    assert model["markup_range"] == [1.0, 4.0]
    assert isinstance(model["markup_range"], list)
    assert len(model["markup_range"]) == 2
    assert "markup_point" not in model
    by_provider = {row["provider"]: row for row in model["providers"]}
    assert by_provider["cheap"]["markup"] == 1.0
    assert by_provider["dear"]["markup"] == 4.0
    assert model["baseline_provider"] == "cheap"


# --- A6 / AC-7 ---


def test_a6_estimated_params_tier_refused() -> None:
    params = _params_ledger([_params_row(params_tier="estimated")])
    endpoints = _endpoint_ledger([_endpoint_row()])
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    assert index["models"] == []
    assert index["refusals"]
    assert index["refusals"][0]["reason"] == "params_tier_not_disclosed"


def test_a6_unknown_params_tier_refused() -> None:
    params = _params_ledger([_params_row(params_tier="unknown")])
    endpoints = _endpoint_ledger([_endpoint_row()])
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    assert index["refusals"][0]["reason"] == "params_tier_not_disclosed"


# --- A7 / AC-9 ---


def test_a7_unknown_quantization_is_flagged_not_silent() -> None:
    params = _params_ledger([_params_row()])
    endpoints = _endpoint_ledger([_endpoint_row(quantization="unknown")])
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    flags = index["models"][0]["providers"][0]["flags"]
    assert "quantization_unknown" in flags


# --- A8 / D4 open ---


def test_a8_nonstandard_tiers_kept_but_excluded_from_baseline() -> None:
    params = _params_ledger([_params_row()])
    endpoints = _endpoint_ledger(
        [
            _endpoint_row(provider="standard-host", price_in_per_m=0.20, price_out_per_m=0.20),
            _endpoint_row(
                provider="fast-host",
                tier="priority",
                price_in_per_m=0.05,
                price_out_per_m=0.05,
                price_source_url="https://example.com/synthetic/fast",
            ),
        ]
    )
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    model = index["models"][0]
    assert model["baseline_provider"] == "standard-host"
    assert model["baseline_tier"] == "standard"
    providers = {row["provider"]: row for row in model["providers"]}
    assert "fast-host" in providers
    assert providers["fast-host"]["tier"] == "priority"
    assert "non_standard_tier" in providers["fast-host"]["flags"]
    assert providers["standard-host"]["markup"] == 1.0
    assert providers["fast-host"]["markup"] == 0.25


# --- A9 / AC-10 ---


def test_a9_allowlist_is_still_exactly_the_four_gate1_paths() -> None:
    assert ALLOWED_PATHS == frozenset(
        {
            "/models",
            "/datasets/rankings-daily",
            "/benchmarks",
            "/classifications/task",
        }
    )


def test_a9_endpoints_path_still_raises_data_api_error() -> None:
    client = DataAPIClient(api_key="sk-or-v1-test", transport=_RecordingTransport())
    with pytest.raises(DataAPIError, match="not allowlisted"):
        client.get("/models/deepseek/deepseek-chat/endpoints")


def test_a9_markup_index_adds_no_network_imports() -> None:
    source = Path(__file__).resolve().parents[1] / "markup_index.py"
    text = source.read_text(encoding="utf-8")
    for banned in ("httpx", "urllib.request", "urllib3", "requests", "aiohttp"):
        assert banned not in text


# --- A10 / AC-8 ---


def test_a10_copy_and_field_descriptions_avoid_forbidden_words() -> None:
    blobs: list[str] = []
    assert DOCS_PATH.is_file(), "docs/provider-markup-index.md is required"
    blobs.append(DOCS_PATH.read_text(encoding="utf-8"))
    module_path = Path(__file__).resolve().parents[1] / "markup_index.py"
    blobs.append(module_path.read_text(encoding="utf-8").split("if __name__")[0])
    for schema_path in DATA_DIR.glob("*.schema.json"):
        blobs.extend(_walk_strings(json.loads(schema_path.read_text(encoding="utf-8"))))
    for blob in blobs:
        match = FORBIDDEN_COPY.search(blob)
        assert match is None, f"forbidden word {match.group(0)!r} in copy"


# --- A11 / AC-28 ---


def test_a11_cli_out_validates_against_committed_schema(tmp_path: Path) -> None:
    out = tmp_path / "markup.json"
    code = main(
        [
            "--params",
            str(SYNTHETIC_PARAMS),
            "--endpoints",
            str(SYNTHETIC_ENDPOINTS),
            "--as-of",
            "2026-10-15",
            "--out",
            str(out),
        ]
    )
    assert code == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
    validate_against_schema(payload, schema)
    assert payload["live"] is False
    assert payload["kind"] == OUTPUT_KIND


# --- A12 / D11 ---


def test_a12_stale_badge_after_90_days_and_exclude_after_180() -> None:
    params = _params_ledger([_params_row()])
    endpoints = _endpoint_ledger(
        [
            _endpoint_row(provider="fresh", fetched_at="2026-10-01"),
            _endpoint_row(
                provider="stale",
                fetched_at="2026-06-01",
                price_in_per_m=0.50,
                price_out_per_m=0.50,
                price_source_url="https://example.com/synthetic/stale",
            ),
            _endpoint_row(
                provider="expired",
                fetched_at="2026-03-01",
                price_in_per_m=0.80,
                price_out_per_m=0.80,
                price_source_url="https://example.com/synthetic/expired",
            ),
        ]
    )
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    by_provider = {row["provider"]: row for row in index["models"][0]["providers"]}
    assert "stale" in by_provider["stale"]["flags"]
    assert by_provider["stale"]["in_default_ranking"] is True
    assert "stale_excluded" in by_provider["expired"]["flags"]
    assert by_provider["expired"]["in_default_ranking"] is False
    assert "fresh" not in "".join(by_provider["fresh"]["flags"])


# --- A13 offline / no composite ---


def test_a13_offline_without_openrouter_key_and_no_composite_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert os.environ.get("OPENROUTER_API_KEY") in (None, "")
    params = load_param_ledger(SYNTHETIC_PARAMS)
    endpoints = load_endpoint_ledger(SYNTHETIC_ENDPOINTS)
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    assert index["live"] is False
    keys = _output_keys(index)
    assert "composite" not in keys
    assert "overall" not in keys
    assert "index_score" not in keys


# --- C-2 URL / string hygiene ---


@pytest.mark.parametrize(
    "bad_url,reason",
    [
        ("javascript:alert(1)", "invalid_source_url"),
        ("data:text/html,hi", "invalid_source_url"),
        ("file:///etc/passwd", "invalid_source_url"),
        ("http://example.com/price", "invalid_source_url"),
    ],
)
def test_c2_rejects_non_https_source_urls(tmp_path: Path, bad_url: str, reason: str) -> None:
    row = _endpoint_row(price_source_url=bad_url)
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, reason)


def test_c2_accepts_https_source_url(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([_endpoint_row()]))
    loaded = load_endpoint_ledger(path)
    assert loaded["rows"][0]["price_source_url"].startswith("https://")


def test_c2_rejects_overlong_provider(tmp_path: Path) -> None:
    row = _endpoint_row(provider="p" * 300)
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "field_too_long")


def test_c2_rejects_html_in_provider(tmp_path: Path) -> None:
    row = _endpoint_row(provider="<script>x</script>")
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "html_or_control_chars")


def test_c2_rejects_control_chars_in_model_id(tmp_path: Path) -> None:
    row = _params_row(model_id="synthetic/open\x00moe")
    path = _write_json(tmp_path / "params.json", _params_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_param_ledger(path)
    _expect_reason(exc.value, "html_or_control_chars")


# --- C-3 numeric refusals ---


def test_c3_rejects_nan_price(tmp_path: Path) -> None:
    raw = deepcopy(_endpoint_ledger([_endpoint_row()]))
    text = json.dumps(raw).replace("0.4", "NaN", 1)
    path = tmp_path / "endpoints.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "non_finite_price")
    assert math.isnan(json.loads(text)["rows"][0]["price_in_per_m"])


def test_c3_rejects_inf_price(tmp_path: Path) -> None:
    raw = deepcopy(_endpoint_ledger([_endpoint_row()]))
    text = json.dumps(raw).replace("2.0", "Infinity", 1)
    path = tmp_path / "endpoints.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "non_finite_price")


def test_c3_rejects_negative_price(tmp_path: Path) -> None:
    row = _endpoint_row(price_in_per_m=-0.1)
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "negative_price")


def test_c3_zero_or_negative_active_params_named_refusal() -> None:
    params = _params_ledger([_params_row(active_params_b=0)])
    endpoints = _endpoint_ledger([_endpoint_row()])
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    assert index["refusals"][0]["reason"] == "active_params_not_positive"


def test_c3_missing_baseline_named_refusal() -> None:
    params = _params_ledger([_params_row()])
    endpoints = _endpoint_ledger(
        [_endpoint_row(price_in_per_m=None, price_out_per_m=None, unlisted=True)]
    )
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    assert index["models"] == []
    assert index["refusals"][0]["reason"] == "missing_baseline"


def test_c3_zero_divisor_named_refusal() -> None:
    params = _params_ledger([_params_row()])
    endpoints = _endpoint_ledger([_endpoint_row(price_in_per_m=0.0, price_out_per_m=0.0)])
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    assert index["refusals"][0]["reason"] == "zero_divisor"


def test_c3_blended_matches_board_1_3_mix() -> None:
    # board.py: 0.25 * in + 0.75 * out when prices are already per 1M.
    assert blended_price(0.8, 4.0, "minibench-1:3") == 3.2


# --- C-6 label ---


def test_c6_output_is_labeled_listed_price_comparison() -> None:
    params = load_param_ledger(SYNTHETIC_PARAMS)
    endpoints = load_endpoint_ledger(SYNTHETIC_ENDPOINTS)
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    assert index["label"] == "listed-price comparison, as of 2026-10-15"
    assert index["kind"] == "listed-price comparison"
    table = format_table(index)
    assert "listed-price comparison, as of 2026-10-15" in table
    lowered = (index["label"] + table).lower()
    assert "provider cost" not in lowered
    assert "intent" not in lowered


def test_synthetic_fixtures_are_labeled_and_not_the_real_ledger() -> None:
    synthetic = json.loads(SYNTHETIC_PARAMS.read_text(encoding="utf-8"))
    assert synthetic["synthetic"] is True
    assert "SYNTHETIC" in synthetic["label"]
    real = json.loads(PARAM_LEDGER_PATH.read_text(encoding="utf-8"))
    assert real.get("synthetic") is not True
    assert "SYNTHETIC" not in json.dumps(real)


# --- Review #72: B1 dates, B2 cache, C-2 nits, ranking gaps ---


def test_b1_impossible_fetched_at_is_named_refusal(tmp_path: Path) -> None:
    row = _endpoint_row(fetched_at="2026-13-45")
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "invalid_fetched_at")


def test_b1_impossible_as_of_is_named_refusal(tmp_path: Path) -> None:
    row = _params_row(as_of="2026-02-30")
    path = _write_json(tmp_path / "params.json", _params_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_param_ledger(path)
    _expect_reason(exc.value, "invalid_as_of")


def test_b1_cli_impossible_dates_exit_nonzero(tmp_path: Path) -> None:
    params = _write_json(tmp_path / "params.json", _params_ledger([_params_row(as_of="2026-02-30")]))
    endpoints = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([_endpoint_row()]))
    assert main(["--check", "--params", str(params), "--endpoints", str(endpoints)]) != 0
    params_ok = _write_json(tmp_path / "params-ok.json", _params_ledger([_params_row()]))
    endpoints_bad = _write_json(
        tmp_path / "endpoints-bad.json",
        _endpoint_ledger([_endpoint_row(fetched_at="2026-13-45")]),
    )
    assert main(["--check", "--params", str(params_ok), "--endpoints", str(endpoints_bad)]) != 0


def test_b2_cache_string_refused_under_aa_profile(tmp_path: Path) -> None:
    params = _write_json(tmp_path / "params.json", _params_ledger([_params_row()]))
    endpoints = _write_json(
        tmp_path / "endpoints.json",
        _endpoint_ledger([_endpoint_row(price_cache_per_m="abc")]),
    )
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(endpoints)
    _expect_reason(exc.value, "non_finite_price")
    assert (
        main(
            [
                "--profile",
                "aa-7:2:1",
                "--params",
                str(params),
                "--endpoints",
                str(endpoints),
                "--as-of",
                "2026-10-15",
            ]
        )
        != 0
    )


def test_b2_cache_boolean_refused_under_aa_profile(tmp_path: Path) -> None:
    params = _write_json(tmp_path / "params.json", _params_ledger([_params_row()]))
    endpoints = _write_json(
        tmp_path / "endpoints.json",
        _endpoint_ledger([_endpoint_row(price_cache_per_m=True)]),
    )
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(endpoints)
    _expect_reason(exc.value, "non_finite_price")
    assert (
        main(
            [
                "--profile",
                "aa-7:2:1",
                "--params",
                str(params),
                "--endpoints",
                str(endpoints),
                "--as-of",
                "2026-10-15",
            ]
        )
        != 0
    )


def test_b2_aa_profile_cli_uses_listed_cache(tmp_path: Path) -> None:
    params = _write_json(tmp_path / "params.json", _params_ledger([_params_row()]))
    endpoints = _write_json(
        tmp_path / "endpoints.json",
        _endpoint_ledger(
            [_endpoint_row(price_in_per_m=0.8, price_out_per_m=4.0, price_cache_per_m=0.2)]
        ),
    )
    out = tmp_path / "markup.json"
    assert (
        main(
            [
                "--profile",
                "aa-7:2:1",
                "--params",
                str(params),
                "--endpoints",
                str(endpoints),
                "--as-of",
                "2026-10-15",
                "--out",
                str(out),
            ]
        )
        == 0
    )
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["profile_id"] == "aa-7:2:1"
    assert payload["models"][0]["providers"][0]["blended_per_m"] == (7 * 0.2 + 2 * 0.8 + 4.0) / 10


@pytest.mark.parametrize(
    "profile_id,cache,expected",
    [
        ("minibench-1:3", None, 3.2),
        ("chat-3:1", None, (3.0 * 0.8 + 4.0) / 4.0),
        ("output-only", None, 4.0),
        ("openrouter-15:1", None, (15.0 * 0.8 + 4.0) / 16.0),
        ("aa-7:2:1", None, (7.0 * 0.8 + 2.0 * 0.8 + 4.0) / 10.0),
        ("aa-7:2:1", 0.2, (7.0 * 0.2 + 2.0 * 0.8 + 4.0) / 10.0),
    ],
)
def test_non_default_blend_profiles(profile_id: str, cache: float | None, expected: float) -> None:
    assert blended_price(0.8, 4.0, profile_id, cache) == expected
    params = _params_ledger([_params_row()])
    row = _endpoint_row(price_in_per_m=0.8, price_out_per_m=4.0)
    if cache is not None:
        row["price_cache_per_m"] = cache
    index = compute_markup_index(
        params, _endpoint_ledger([row]), profile_id=profile_id, as_of="2026-10-15"
    )
    assert index["models"][0]["providers"][0]["blended_per_m"] == expected
    assert index["profile_id"] == profile_id


@pytest.mark.parametrize(
    "provider",
    [
        "host\x7f",
        "host\u0085",
        "host\u202e",
    ],
)
def test_c2_rejects_del_c1_and_bidi_in_provider(tmp_path: Path, provider: str) -> None:
    row = _endpoint_row(provider=provider)
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "html_or_control_chars")


def test_c2_rejects_control_or_html_in_source_url(tmp_path: Path) -> None:
    row = _endpoint_row(price_source_url="https://x.com/\n<script>")
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "html_or_control_chars")


def test_c2_rejects_bare_https_without_host(tmp_path: Path) -> None:
    row = _endpoint_row(price_source_url="https://")
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "invalid_source_url")


def test_c2_rejects_non_https_param_source_url(tmp_path: Path) -> None:
    row = _params_row(params_source_url="http://example.com/params")
    path = _write_json(tmp_path / "params.json", _params_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_param_ledger(path)
    _expect_reason(exc.value, "invalid_source_url")


def test_c2_rejects_overlong_source_url(tmp_path: Path) -> None:
    row = _endpoint_row(price_source_url="https://example.com/" + ("a" * 2048))
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "field_too_long")


def test_unlisted_string_false_is_refused(tmp_path: Path) -> None:
    row = _endpoint_row(unlisted="false")
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "invalid_unlisted")


def test_unlisted_row_must_leave_prices_null(tmp_path: Path) -> None:
    row = _endpoint_row(unlisted=True, price_in_per_m=0.4, price_out_per_m=2.0)
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "unlisted_price_unmarked")


def test_live_true_ledger_is_refused(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "params.json", _params_ledger([_params_row()], live=True))
    with pytest.raises(MarkupIndexError) as exc:
        load_param_ledger(path)
    _expect_reason(exc.value, "live_label")


def test_future_fetched_at_is_refused(tmp_path: Path) -> None:
    row = _endpoint_row(fetched_at="2099-01-01")
    path = _write_json(tmp_path / "endpoints.json", _endpoint_ledger([row]))
    with pytest.raises(MarkupIndexError) as exc:
        load_endpoint_ledger(path)
    _expect_reason(exc.value, "invalid_fetched_at")


def test_compute_impossible_fetched_at_cannot_be_baseline() -> None:
    params = _params_ledger([_params_row()])
    endpoints = _endpoint_ledger(
        [
            _endpoint_row(
                provider="bogus-cheap",
                fetched_at="2026-13-45",
                price_in_per_m=0.01,
                price_out_per_m=0.01,
                price_source_url="https://example.com/synthetic/bogus",
            ),
            _endpoint_row(
                provider="valid",
                fetched_at="2026-10-15",
                price_in_per_m=0.40,
                price_out_per_m=0.40,
                price_source_url="https://example.com/synthetic/valid",
            ),
        ]
    )
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    model = index["models"][0]
    assert model["baseline_provider"] == "valid"
    assert all(row["provider"] != "bogus-cheap" for row in model["providers"])


def test_stale_row_never_becomes_baseline() -> None:
    params = _params_ledger([_params_row()])
    endpoints = _endpoint_ledger(
        [
            _endpoint_row(
                provider="stale-cheap",
                fetched_at="2026-07-16",
                price_in_per_m=0.10,
                price_out_per_m=0.10,
                price_source_url="https://example.com/synthetic/stale-cheap",
            ),
            _endpoint_row(
                provider="fresh-dear",
                fetched_at="2026-10-15",
                price_in_per_m=0.40,
                price_out_per_m=0.40,
                price_source_url="https://example.com/synthetic/fresh-dear",
            ),
        ]
    )
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    model = index["models"][0]
    assert model["baseline_provider"] == "fresh-dear"
    by_provider = {row["provider"]: row for row in model["providers"]}
    assert "stale" in by_provider["stale-cheap"]["flags"]
    assert by_provider["stale-cheap"]["in_default_ranking"] is True
    assert by_provider["fresh-dear"]["markup"] == 1.0
    assert by_provider["stale-cheap"]["markup"] == 0.25


def test_only_stale_standard_row_is_missing_baseline() -> None:
    params = _params_ledger([_params_row()])
    endpoints = _endpoint_ledger(
        [
            _endpoint_row(
                provider="stale-only",
                fetched_at="2026-07-16",
                price_in_per_m=0.10,
                price_out_per_m=0.10,
            )
        ]
    )
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    assert index["models"] == []
    assert index["refusals"][0]["reason"] == "missing_baseline"


def test_excluded_row_never_counts_toward_range() -> None:
    params = _params_ledger([_params_row()])
    endpoints = _endpoint_ledger(
        [
            _endpoint_row(
                provider="excluded-cheap",
                fetched_at="2026-04-17",
                price_in_per_m=0.05,
                price_out_per_m=0.05,
                price_source_url="https://example.com/synthetic/excluded",
            ),
            _endpoint_row(
                provider="fresh-mid",
                fetched_at="2026-10-15",
                price_in_per_m=0.40,
                price_out_per_m=0.40,
                price_source_url="https://example.com/synthetic/fresh-mid",
            ),
            _endpoint_row(
                provider="fresh-dear",
                fetched_at="2026-10-15",
                price_in_per_m=0.80,
                price_out_per_m=0.80,
                price_source_url="https://example.com/synthetic/fresh-dear",
            ),
        ]
    )
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    model = index["models"][0]
    by_provider = {row["provider"]: row for row in model["providers"]}
    assert "stale_excluded" in by_provider["excluded-cheap"]["flags"]
    assert by_provider["excluded-cheap"]["in_default_ranking"] is False
    assert model["baseline_provider"] == "fresh-mid"
    assert model["markup_range"] == [1.0, 2.0]
    assert by_provider["excluded-cheap"]["markup"] not in model["markup_range"]


def test_stale_cutoff_edges() -> None:
    params = _params_ledger([_params_row()])
    endpoints = _endpoint_ledger(
        [
            _endpoint_row(
                provider="fresh-baseline",
                fetched_at="2026-10-15",
                price_in_per_m=0.20,
                price_out_per_m=0.20,
                price_source_url="https://example.com/synthetic/fresh-baseline",
            ),
            _endpoint_row(
                provider="age-90",
                fetched_at="2026-07-17",
                price_in_per_m=0.30,
                price_out_per_m=0.30,
                price_source_url="https://example.com/synthetic/age-90",
            ),
            _endpoint_row(
                provider="age-91",
                fetched_at="2026-07-16",
                price_in_per_m=0.40,
                price_out_per_m=0.40,
                price_source_url="https://example.com/synthetic/age-91",
            ),
            _endpoint_row(
                provider="age-180",
                fetched_at="2026-04-18",
                price_in_per_m=0.50,
                price_out_per_m=0.50,
                price_source_url="https://example.com/synthetic/age-180",
            ),
            _endpoint_row(
                provider="age-181",
                fetched_at="2026-04-17",
                price_in_per_m=0.60,
                price_out_per_m=0.60,
                price_source_url="https://example.com/synthetic/age-181",
            ),
        ]
    )
    index = compute_markup_index(params, endpoints, as_of="2026-10-15")
    by_provider = {row["provider"]: row for row in index["models"][0]["providers"]}
    assert "stale" not in by_provider["age-90"]["flags"]
    assert by_provider["age-90"]["in_default_ranking"] is True
    assert "stale" in by_provider["age-91"]["flags"]
    assert "stale_excluded" not in by_provider["age-91"]["flags"]
    assert by_provider["age-91"]["in_default_ranking"] is True
    assert "stale" in by_provider["age-180"]["flags"]
    assert "stale_excluded" not in by_provider["age-180"]["flags"]
    assert by_provider["age-180"]["in_default_ranking"] is True
    assert "stale_excluded" in by_provider["age-181"]["flags"]
    assert by_provider["age-181"]["in_default_ranking"] is False
    assert index["models"][0]["baseline_provider"] == "fresh-baseline"
    assert by_provider["age-181"]["markup"] not in index["models"][0]["markup_range"]
