from minibench.specs import lookup_specs


def test_apple_m4_variants_use_longest_match():
    assert lookup_specs("Apple M4 Max")["system_type"] == "Mac Mini M4 Max"
    assert lookup_specs("Apple M4 Pro")["system_type"] == "Mac Mini M4 Pro"
    assert lookup_specs("Apple M4")["system_type"] == "Mac Mini M4"


def test_apple_variants_have_distinct_bandwidth():
    assert lookup_specs("Apple M4 Max")["memory_bandwidth_gbs"] == 546.0
    assert lookup_specs("Apple M4 Pro")["memory_bandwidth_gbs"] == 273.0
    assert lookup_specs("Apple M4")["memory_bandwidth_gbs"] == 100.0


def test_bandwidth_lookup_by_cpu_substring():
    assert lookup_specs("AMD Ryzen 9 7940HS")["memory_bandwidth_gbs"] == 51.2
    assert lookup_specs("Intel Core i9-13900H")["memory_bandwidth_gbs"] == 76.8
    assert lookup_specs("Broadcom BCM2712 (Cortex-A76)")["memory_bandwidth_gbs"] == 34.0
    assert lookup_specs("Intel Core Ultra 7 155H")["system_type"] == "Intel NUC 14 Pro"


def test_unknown_cpu_returns_none():
    assert lookup_specs("Totally Unknown CPU 9000") is None
    assert lookup_specs("") is None


def test_explicit_system_type_takes_precedence():
    spec = lookup_specs("irrelevant cpu string", system_type="Raspberry Pi 5")
    assert spec["memory_bandwidth_gbs"] == 34.0
    assert spec["form_factor"] == "sbc"


def test_spec_has_expected_fields():
    spec = lookup_specs("Apple M4 Pro")
    assert set(spec) == {
        "system_type",
        "memory_bandwidth_gbs",
        "memory_type",
        "hardware_price_usd",
        "form_factor",
    }
