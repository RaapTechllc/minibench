"""Open-weight provider markup / serving-efficiency index (curated listed prices)."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

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
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
HTML_RE = re.compile(r"<[^>]*>")

MAX_MODEL_ID = 256
MAX_PROVIDER = 128
MAX_URL = 2048
MAX_TEXT = 2000
MAX_TIER = 64
MAX_QUANT = 64
STANDARD_TIERS = frozenset({"standard"})


class MarkupIndexError(ValueError):
    """Named refusal. ``reason`` is the machine-readable code."""

    def __init__(self, reason: str, message: str = "") -> None:
        self.reason = reason
        text = f"{reason}: {message}" if message else reason
        super().__init__(text)


def _is_finite_amount(amount: object) -> bool:
    return isinstance(amount, (int, float)) and not isinstance(amount, bool) and math.isfinite(amount)


def _parse_day(stamp: str) -> date:
    if not isinstance(stamp, str) or not DATE_RE.match(stamp):
        raise MarkupIndexError("invalid_as_of", f"need YYYY-MM-DD, got {stamp!r}")
    return datetime.strptime(stamp, "%Y-%m-%d").date()


def _has_control_or_html(text: str) -> bool:
    if any(ord(char) < 32 for char in text):
        return True
    if "<" in text or ">" in text or HTML_RE.search(text):
        return True
    return False


def _check_https_url(url: object, *, missing_reason: str) -> str:
    if url is None or url == "":
        raise MarkupIndexError(missing_reason, "source URL is required")
    if not isinstance(url, str):
        raise MarkupIndexError("invalid_source_url", "source URL must be a string")
    lowered = url.strip().lower()
    if (
        lowered.startswith("javascript:")
        or lowered.startswith("data:")
        or lowered.startswith("file:")
        or lowered.startswith("http:")
        or not url.startswith("https://")
    ):
        raise MarkupIndexError("invalid_source_url", "source URL must be https://")
    if len(url) > MAX_URL:
        raise MarkupIndexError("field_too_long", "source URL exceeds cap")
    return url


def _check_name(text: object, *, field: str, cap: int) -> str:
    if not isinstance(text, str) or text == "":
        raise MarkupIndexError("html_or_control_chars", f"{field} must be a non-empty string")
    if len(text) > cap:
        raise MarkupIndexError("field_too_long", f"{field} exceeds cap")
    if _has_control_or_html(text):
        raise MarkupIndexError("html_or_control_chars", f"{field} has HTML or control chars")
    return text


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MarkupIndexError("invalid_json", str(exc)) from exc
    if not isinstance(payload, dict):
        raise MarkupIndexError("invalid_json", "root must be an object")
    if payload.get("live") is True:
        raise MarkupIndexError("live_label", "curated ledgers must set live=false")
    return payload


def _check_param_row(row: object) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise MarkupIndexError("invalid_json", "param row must be an object")
    if "params_source_url" not in row or row.get("params_source_url") in (None, ""):
        raise MarkupIndexError("missing_params_source_url", "params_source_url is required")
    if "as_of" not in row or row.get("as_of") in (None, ""):
        raise MarkupIndexError("missing_as_of", "as_of is required")
    _check_https_url(row["params_source_url"], missing_reason="missing_params_source_url")
    _parse_day(str(row["as_of"]))
    _check_name(row.get("model_id"), field="model_id", cap=MAX_MODEL_ID)
    convention = row.get("count_convention", "")
    if not isinstance(convention, str) or len(convention) > MAX_TEXT:
        raise MarkupIndexError("field_too_long", "count_convention exceeds cap")
    total = row.get("total_params_b")
    if not _is_finite_amount(total) or float(total) <= 0:
        raise MarkupIndexError("active_params_not_positive", "total_params_b must be finite and > 0")
    active = row.get("active_params_b")
    if active is not None and (not _is_finite_amount(active) or float(active) < 0):
        raise MarkupIndexError("active_params_not_positive", "active_params_b must be finite and >= 0 or null")
    tier = row.get("params_tier")
    if tier not in {"disclosed", "estimated", "unknown"}:
        raise MarkupIndexError("params_tier_not_disclosed", f"unsupported params_tier {tier!r}")
    return row


def _check_listed_amount(amount: object, *, allow_null: bool) -> float | None:
    if amount is None:
        if allow_null:
            return None
        raise MarkupIndexError("unlisted_price_unmarked", "null price must be marked unlisted")
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise MarkupIndexError("non_finite_price", "price must be a JSON number")
    if not math.isfinite(float(amount)):
        raise MarkupIndexError("non_finite_price", "price must be finite")
    if float(amount) < 0:
        raise MarkupIndexError("negative_price", "price must be >= 0")
    return float(amount)


def _check_endpoint_row(row: object) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise MarkupIndexError("invalid_json", "endpoint row must be an object")
    if "price_source_url" not in row or row.get("price_source_url") in (None, ""):
        raise MarkupIndexError("missing_price_source_url", "price_source_url is required")
    if "fetched_at" not in row or row.get("fetched_at") in (None, ""):
        raise MarkupIndexError("missing_fetched_at", "fetched_at is required")
    _check_https_url(row["price_source_url"], missing_reason="missing_price_source_url")
    _parse_day(str(row["fetched_at"]))
    _check_name(row.get("model_id"), field="model_id", cap=MAX_MODEL_ID)
    _check_name(row.get("provider"), field="provider", cap=MAX_PROVIDER)
    tier = row.get("tier", "")
    _check_name(tier, field="tier", cap=MAX_TIER)
    quant = row.get("quantization", "")
    _check_name(quant, field="quantization", cap=MAX_QUANT)
    unlisted = bool(row.get("unlisted"))
    _check_listed_amount(row.get("price_in_per_m"), allow_null=unlisted)
    _check_listed_amount(row.get("price_out_per_m"), allow_null=unlisted)
    if unlisted and (row.get("price_in_per_m") is not None or row.get("price_out_per_m") is not None):
        raise MarkupIndexError("unlisted_price_unmarked", "unlisted rows must leave prices null")
    return row


def load_param_ledger(path: Path | None = None) -> dict[str, Any]:
    payload = _read_json(path or PARAM_LEDGER_PATH)
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise MarkupIndexError("invalid_json", "param ledger rows must be an array")
    for row in rows:
        _check_param_row(row)
    return payload


def load_endpoint_ledger(path: Path | None = None) -> dict[str, Any]:
    payload = _read_json(path or ENDPOINT_LEDGER_PATH)
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise MarkupIndexError("invalid_json", "endpoint ledger rows must be an array")
    for row in rows:
        _check_endpoint_row(row)
    return payload


def _type_ok(instance: object, expected: str) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "null":
        return instance is None
    return False


def validate_against_schema(instance: object, schema: dict[str, Any], path: str = "$") -> None:
    if not isinstance(schema, dict):
        raise MarkupIndexError("schema_violation", f"{path}: schema must be an object")
    if "type" in schema:
        expected = schema["type"]
        kinds = expected if isinstance(expected, list) else [expected]
        if not any(_type_ok(instance, kind) for kind in kinds):
            raise MarkupIndexError("schema_violation", f"{path}: type {expected!r} rejected")
    if "const" in schema and instance != schema["const"]:
        raise MarkupIndexError("schema_violation", f"{path}: const mismatch")
    if "enum" in schema and instance not in schema["enum"]:
        raise MarkupIndexError("schema_violation", f"{path}: not in enum")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < int(schema["minLength"]):
            raise MarkupIndexError("schema_violation", f"{path}: shorter than minLength")
        if "maxLength" in schema and len(instance) > int(schema["maxLength"]):
            raise MarkupIndexError("schema_violation", f"{path}: longer than maxLength")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            raise MarkupIndexError("schema_violation", f"{path}: pattern mismatch")
    if _is_finite_amount(instance):
        amount = float(instance)
        if "minimum" in schema and amount < float(schema["minimum"]):
            raise MarkupIndexError("schema_violation", f"{path}: below minimum")
        if "exclusiveMinimum" in schema and amount <= float(schema["exclusiveMinimum"]):
            raise MarkupIndexError("schema_violation", f"{path}: not above exclusiveMinimum")
        if "maximum" in schema and amount > float(schema["maximum"]):
            raise MarkupIndexError("schema_violation", f"{path}: above maximum")
    elif isinstance(instance, (int, float)) and not isinstance(instance, bool) and not math.isfinite(float(instance)):
        raise MarkupIndexError("schema_violation", f"{path}: non-finite number")
    if isinstance(instance, dict) and schema.get("type", "object") in ("object", None) or (
        isinstance(instance, dict) and "properties" in schema
    ):
        if isinstance(instance, dict):
            required = schema.get("required") or []
            for key in required:
                if key not in instance:
                    raise MarkupIndexError("schema_violation", f"{path}: missing {key}")
            props = schema.get("properties") or {}
            additional = schema.get("additionalProperties", True)
            for key, child in instance.items():
                if key in props:
                    validate_against_schema(child, props[key], f"{path}.{key}")
                elif additional is False:
                    raise MarkupIndexError("schema_violation", f"{path}: unexpected {key}")
                elif isinstance(additional, dict):
                    validate_against_schema(child, additional, f"{path}.{key}")
    if isinstance(instance, list) and "items" in schema:
        if "minItems" in schema and len(instance) < int(schema["minItems"]):
            raise MarkupIndexError("schema_violation", f"{path}: fewer than minItems")
        if "maxItems" in schema and len(instance) > int(schema["maxItems"]):
            raise MarkupIndexError("schema_violation", f"{path}: more than maxItems")
        item_schema = schema["items"]
        if isinstance(item_schema, dict):
            for idx, child in enumerate(instance):
                validate_against_schema(child, item_schema, f"{path}[{idx}]")
    if "oneOf" in schema:
        matched = 0
        for option in schema["oneOf"]:
            try:
                validate_against_schema(instance, option, path)
            except MarkupIndexError:
                continue
            matched += 1
        if matched != 1:
            raise MarkupIndexError("schema_violation", f"{path}: oneOf did not match once")


def blended_price(
    price_in_per_m: float,
    price_out_per_m: float,
    profile_id: str = DEFAULT_PROFILE_ID,
    price_cache_per_m: float | None = None,
) -> float:
    if not _is_finite_amount(price_in_per_m) or not _is_finite_amount(price_out_per_m):
        raise MarkupIndexError("non_finite_price", "blend inputs must be finite")
    if float(price_in_per_m) < 0 or float(price_out_per_m) < 0:
        raise MarkupIndexError("negative_price", "blend inputs must be >= 0")
    pin = float(price_in_per_m)
    pout = float(price_out_per_m)
    if profile_id == "minibench-1:3":
        return (pin + 3.0 * pout) / 4.0
    if profile_id == "chat-3:1":
        return (3.0 * pin + pout) / 4.0
    if profile_id == "output-only":
        return pout
    if profile_id == "openrouter-15:1":
        return (15.0 * pin + pout) / 16.0
    if profile_id == "aa-7:2:1":
        cache = pin if price_cache_per_m is None else float(price_cache_per_m)
        if not _is_finite_amount(cache) or cache < 0:
            raise MarkupIndexError("non_finite_price", "cache listed price must be finite and >= 0")
        return (7.0 * cache + 2.0 * pin + pout) / 10.0
    raise MarkupIndexError("unknown_profile", f"unsupported profile_id {profile_id!r}")


def _refusal(model_id: str, reason: str, detail: str = "") -> dict[str, str]:
    payload = {"model_id": model_id, "reason": reason}
    if detail:
        payload["detail"] = detail
    return payload


def compute_markup_index(
    params: dict[str, Any],
    endpoints: dict[str, Any],
    *,
    profile_id: str = DEFAULT_PROFILE_ID,
    as_of: str | None = None,
    cache_assumption: str = "none",
) -> dict[str, Any]:
    as_of_stamp = as_of or date.today().isoformat()
    as_of_day = _parse_day(as_of_stamp)
    models: list[dict[str, Any]] = []
    refusals: list[dict[str, str]] = []
    endpoint_rows = [row for row in (endpoints.get("rows") or []) if isinstance(row, dict)]

    for param in params.get("rows") or []:
        if not isinstance(param, dict):
            continue
        model_id = str(param.get("model_id") or "")
        tier = param.get("params_tier")
        if tier != "disclosed":
            refusals.append(_refusal(model_id, "params_tier_not_disclosed", f"params_tier={tier!r}"))
            continue
        active = param.get("active_params_b")
        if not _is_finite_amount(active) or float(active) <= 0:
            refusals.append(_refusal(model_id, "active_params_not_positive", "active_params_b must be > 0"))
            continue
        active_b = float(active)
        listed: list[dict[str, Any]] = []
        for row in endpoint_rows:
            if row.get("model_id") != model_id:
                continue
            if row.get("unlisted"):
                continue
            pin, pout = row.get("price_in_per_m"), row.get("price_out_per_m")
            if not _is_finite_amount(pin) or not _is_finite_amount(pout):
                continue
            if float(pin) < 0 or float(pout) < 0:
                continue
            listed.append(row)
        if not listed:
            refusals.append(_refusal(model_id, "missing_baseline", "no listed standard-tier price"))
            continue
        provider_rows: list[dict[str, Any]] = []
        baseline_candidates: list[tuple[float, str, str]] = []
        for row in listed:
            fetched = str(row.get("fetched_at") or as_of_stamp)
            try:
                age_days = (as_of_day - _parse_day(fetched)).days
            except MarkupIndexError:
                age_days = 0
            flags: list[str] = []
            service_tier = str(row.get("tier") or "standard")
            if service_tier not in STANDARD_TIERS:
                flags.append("non_standard_tier")
            quant = str(row.get("quantization") or "unknown")
            if quant == "unknown":
                flags.append("quantization_unknown")
            if age_days > STALE_BADGE_DAYS:
                flags.append("stale")
            excluded = age_days > STALE_EXCLUDE_DAYS
            if excluded:
                flags.append("stale_excluded")
            blend = blended_price(
                float(row["price_in_per_m"]),
                float(row["price_out_per_m"]),
                profile_id,
                row.get("price_cache_per_m"),
            )
            in_ranking = not excluded
            if in_ranking and service_tier in STANDARD_TIERS:
                baseline_candidates.append((blend, str(row.get("provider")), service_tier))
            provider_rows.append(
                {
                    "provider": str(row.get("provider")),
                    "tier": service_tier,
                    "quantization": quant,
                    "price_in_per_m": float(row["price_in_per_m"]),
                    "price_out_per_m": float(row["price_out_per_m"]),
                    "blended_per_m": blend,
                    "price_source": str(row.get("price_source_url") or row.get("price_source") or ""),
                    "as_of": fetched,
                    "profile_id": profile_id,
                    "cache_assumption": cache_assumption,
                    "flags": flags,
                    "in_default_ranking": in_ranking,
                    "_blend": blend,
                }
            )
        if not baseline_candidates:
            refusals.append(_refusal(model_id, "missing_baseline", "no listed standard-tier price in ranking window"))
            continue
        baseline_candidates.sort(key=lambda item: (item[0], item[1], item[2]))
        baseline_blend, baseline_provider, baseline_tier = baseline_candidates[0]
        if baseline_blend == 0:
            refusals.append(_refusal(model_id, "zero_divisor", "baseline blended listed price is 0"))
            continue
        finished: list[dict[str, Any]] = []
        ranking_markups: list[float] = []
        for row in provider_rows:
            mix = float(row.pop("_blend"))
            markup = mix / baseline_blend
            per_active = mix / active_b
            row["markup"] = markup
            row["dollars_per_1m_per_active_b"] = per_active
            if row["in_default_ranking"]:
                ranking_markups.append(markup)
            finished.append(row)
        if not ranking_markups:
            refusals.append(_refusal(model_id, "missing_baseline", "no rows remain in default ranking"))
            continue
        finished.sort(key=lambda item: (item["markup"], item["provider"], item["tier"]))
        models.append(
            {
                "model_id": model_id,
                "total_params_b": param.get("total_params_b"),
                "active_params_b": active_b,
                "params_tier": "disclosed",
                "baseline_provider": baseline_provider,
                "baseline_tier": baseline_tier,
                "baseline_blended_per_m": baseline_blend,
                "markup_range": [min(ranking_markups), max(ranking_markups)],
                "providers": finished,
            }
        )

    models.sort(key=lambda item: item["model_id"])
    return {
        "kind": OUTPUT_KIND,
        "label": f"{OUTPUT_KIND}, as of {as_of_stamp}",
        "as_of": as_of_stamp,
        "profile_id": profile_id,
        "cache_assumption": cache_assumption,
        "live": False,
        "models": models,
        "refusals": refusals,
    }


def format_table(index: dict[str, Any]) -> str:
    lines = [
        str(index.get("label") or f"{OUTPUT_KIND}, as of {index.get('as_of')}"),
        (
            f"profile={index.get('profile_id')} "
            f"cache_assumption={index.get('cache_assumption')} "
            f"live={index.get('live')}"
        ),
        "",
        (
            f"{'model':<28} {'provider':<12} {'tier':<10} "
            f"{'blended':>10} {'per_active':>12} {'markup':>8} flags"
        ),
    ]
    for model in index.get("models") or []:
        for row in model.get("providers") or []:
            flags = ",".join(row.get("flags") or []) or "-"
            lines.append(
                f"{model['model_id']:<28} {row['provider']:<12} {row['tier']:<10} "
                f"{row['blended_per_m']:>10.6f} {row['dollars_per_1m_per_active_b']:>12.6f} "
                f"{row['markup']:>8.4f} {flags}"
            )
    if index.get("refusals"):
        lines.append("")
        lines.append("refusals:")
        for row in index["refusals"]:
            lines.append(f"  {row['model_id']}: {row['reason']}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a listed-price comparison of open-weight hosting providers."
    )
    parser.add_argument("--params", type=Path, default=PARAM_LEDGER_PATH, help="Parameter ledger JSON")
    parser.add_argument("--endpoints", type=Path, default=ENDPOINT_LEDGER_PATH, help="Endpoint price ledger JSON")
    parser.add_argument("--out", type=Path, default=None, help="Write JSON to this path")
    parser.add_argument("--check", action="store_true", help="Validate ledgers and exit nonzero on errors")
    parser.add_argument("--profile", default=DEFAULT_PROFILE_ID, help="Workload profile id (default: minibench-1:3)")
    parser.add_argument("--as-of", dest="as_of", default=None, help="Comparison day YYYY-MM-DD")
    args = parser.parse_args(argv)
    try:
        params = load_param_ledger(args.params)
        endpoints = load_endpoint_ledger(args.endpoints)
        if args.check:
            return 0
        index = compute_markup_index(
            params,
            endpoints,
            profile_id=args.profile,
            as_of=args.as_of,
        )
        schema = json.loads(OUTPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
        validate_against_schema(index, schema)
        if args.out is not None:
            args.out.write_text(json.dumps(index, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print(format_table(index), end="")
        return 0
    except MarkupIndexError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
