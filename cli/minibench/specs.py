"""Curated hardware-spec lookup.

Memory bandwidth — the headline metric for local LLM inference — cannot be read
reliably at runtime on most platforms, so the CLI looks it up from this curated
table instead of guessing. The table mirrors the backend `hardware_specs` seed
data; keep the two in sync. Lookups are keyed by substrings found in the
auto-detected CPU model string (or by an explicit ``--system-type``).
"""
from typing import Optional

# system_type, curated specs, and CPU-string match hints (all lowercase).
HARDWARE_TABLE = [
    {
        "system_type": "Mac Mini M4 Max",
        "memory_bandwidth_gbs": 546.0,
        "memory_type": "Unified",
        "hardware_price_usd": 2999.0,
        "form_factor": "mini_pc",
        "cpu": ["apple m4 max"],
    },
    {
        "system_type": "Mac Mini M4 Pro",
        "memory_bandwidth_gbs": 273.0,
        "memory_type": "Unified",
        "hardware_price_usd": 1399.0,
        "form_factor": "mini_pc",
        "cpu": ["apple m4 pro"],
    },
    {
        "system_type": "Mac Mini M4",
        "memory_bandwidth_gbs": 100.0,
        "memory_type": "Unified",
        "hardware_price_usd": 599.0,
        "form_factor": "mini_pc",
        "cpu": ["apple m4"],
    },
    {
        "system_type": "Minisforum UM790 Pro",
        "memory_bandwidth_gbs": 51.2,
        "memory_type": "DDR5",
        "hardware_price_usd": 550.0,
        "form_factor": "mini_pc",
        "cpu": ["7940hs"],
    },
    {
        "system_type": "Minisforum MS-01",
        "memory_bandwidth_gbs": 76.8,
        "memory_type": "DDR5",
        "hardware_price_usd": 850.0,
        "form_factor": "mini_pc",
        "cpu": ["13900h"],
    },
    {
        "system_type": "Beelink SER8",
        "memory_bandwidth_gbs": 51.2,
        "memory_type": "DDR5",
        "hardware_price_usd": 450.0,
        "form_factor": "mini_pc",
        "cpu": ["8945hs"],
    },
    {
        "system_type": "Intel NUC 14 Pro",
        "memory_bandwidth_gbs": 76.8,
        "memory_type": "DDR5",
        "hardware_price_usd": 600.0,
        "form_factor": "nuc",
        "cpu": ["ultra 7 155h", "155h"],
    },
    {
        "system_type": "NVIDIA Jetson AGX Orin",
        "memory_bandwidth_gbs": 204.0,
        "memory_type": "LPDDR5",
        "hardware_price_usd": 1999.0,
        "form_factor": "sbc",
        "cpu": ["cortex-a78ae", "a78ae"],
    },
    {
        "system_type": "Framework 16",
        "memory_bandwidth_gbs": 51.2,
        "memory_type": "DDR5",
        "hardware_price_usd": 1400.0,
        "form_factor": "laptop",
        "cpu": ["7840hs"],
    },
    {
        "system_type": "Raspberry Pi 5",
        "memory_bandwidth_gbs": 34.0,
        "memory_type": "LPDDR4X",
        "hardware_price_usd": 80.0,
        "form_factor": "sbc",
        "cpu": ["bcm2712", "cortex-a76"],
    },
]

_SPEC_FIELDS = (
    "system_type",
    "memory_bandwidth_gbs",
    "memory_type",
    "hardware_price_usd",
    "form_factor",
)


def _spec(entry: dict) -> dict:
    return {k: entry[k] for k in _SPEC_FIELDS}


def lookup_specs(cpu_model: str, system_type: Optional[str] = None) -> Optional[dict]:
    """Return curated specs for a system, or None if unknown.

    Resolution order:
      1. An explicit ``system_type`` matched against known system names.
      2. The longest CPU-substring match (so "Apple M4 Pro" wins over "Apple M4").
    """
    if system_type:
        st = system_type.strip().lower()
        for entry in HARDWARE_TABLE:
            name = entry["system_type"].lower()
            if name == st or name in st or st in name:
                return _spec(entry)

    cpu = (cpu_model or "").lower()
    best: Optional[dict] = None
    best_len = 0
    for entry in HARDWARE_TABLE:
        for hint in entry["cpu"]:
            if hint in cpu and len(hint) > best_len:
                best = entry
                best_len = len(hint)
    return _spec(best) if best else None
