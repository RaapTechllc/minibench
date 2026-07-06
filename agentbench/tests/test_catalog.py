"""Catalog generator: strategic list joins against a feed, missing ids fail loudly."""
import pytest

from agentbench.catalog import STRATEGIC_MODELS, build_catalog


def _feed_for(ids):
    return [
        {
            "id": i,
            "name": f"Name of {i}",
            "created": 1750000000,
            "context_length": 128000,
            "pricing": {"prompt": "0.000001", "completion": "0.000002"},
        }
        for i in ids
    ]


def test_build_catalog_joins_feed_metadata():
    feed = _feed_for([s["id"] for s in STRATEGIC_MODELS])
    rows = build_catalog(feed)
    assert len(rows) == len(STRATEGIC_MODELS)
    row = rows[0]
    assert row["provider"] == "openrouter"
    assert row["display_name"].startswith("Name of ")
    assert row["prompt_price"] == 1e-6
    assert row["completion_price"] == 2e-6
    assert row["snapshot_date"] == "2025-06-15"
    assert row["family"] and row["license"] in ("open", "closed")


def test_build_catalog_fails_on_missing_id():
    feed = _feed_for([s["id"] for s in STRATEGIC_MODELS][1:])  # drop one
    with pytest.raises(KeyError, match="absent from the OpenRouter feed"):
        build_catalog(feed)


def test_strategic_list_has_no_duplicates_and_required_keys():
    ids = [s["id"] for s in STRATEGIC_MODELS]
    assert len(ids) == len(set(ids))
    assert all(s["license"] in ("open", "closed") for s in STRATEGIC_MODELS)
    assert all(s["family"] for s in STRATEGIC_MODELS)
