"""Open-weight provider markup / serving-efficiency index (curated listed prices)."""
from __future__ import annotations

from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
PARAM_LEDGER_PATH = DATA_DIR / "param_ledger.json"
ENDPOINT_LEDGER_PATH = DATA_DIR / "endpoint_price_ledger.json"
PARAM_SCHEMA_PATH = DATA_DIR / "param_ledger.schema.json"
ENDPOINT_SCHEMA_PATH = DATA_DIR / "endpoint_price_ledger.schema.json"
OUTPUT_SCHEMA_PATH = DATA_DIR / "markup_index.schema.json"

DEFAULT_PROFILE_ID = "minibench-1:3"
STALE_BADGE_DAYS = 90
STALE_EXCLUDE_DAYS = 180
OUTPUT_KIND = "listed-price comparison"


class MarkupIndexError(ValueError):
    """Named refusal. ``reason`` is the machine-readable code."""

    def __init__(self, reason: str, message: str = "") -> None:
        self.reason = reason
        text = f"{reason}: {message}" if message else reason
        super().__init__(text)


def load_param_ledger(path: Path | None = None) -> dict:
    raise MarkupIndexError("not_implemented", "load_param_ledger")


def load_endpoint_ledger(path: Path | None = None) -> dict:
    raise MarkupIndexError("not_implemented", "load_endpoint_ledger")


def validate_against_schema(instance: object, schema: dict) -> None:
    raise MarkupIndexError("not_implemented", "validate_against_schema")


def blended_price(
    price_in_per_m: float,
    price_out_per_m: float,
    profile_id: str = DEFAULT_PROFILE_ID,
    price_cache_per_m: float | None = None,
) -> float:
    raise MarkupIndexError("not_implemented", "blended_price")


def compute_markup_index(
    params: dict,
    endpoints: dict,
    *,
    profile_id: str = DEFAULT_PROFILE_ID,
    as_of: str | None = None,
    cache_assumption: str = "none",
) -> dict:
    raise MarkupIndexError("not_implemented", "compute_markup_index")


def format_table(index: dict) -> str:
    raise MarkupIndexError("not_implemented", "format_table")


def main(argv: list[str] | None = None) -> int:
    raise MarkupIndexError("not_implemented", "main")


if __name__ == "__main__":
    raise SystemExit(main())
