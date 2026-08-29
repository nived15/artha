from __future__ import annotations

import pytest

from artha.data.field_map import FieldMapError, load_field_map


def test_load_field_map_reads_named_profile_section(tmp_path):
    toml_path = tmp_path / "field_map.toml"
    toml_path.write_text(
        """
        [profile_1_standard]
        market_cap = "Market Capitalization"
        roce = "ROCE %"

        [profile_2_banking]
        gnpa_pct = "Gross NPA %"
        """,
        encoding="utf-8",
    )

    mapping = load_field_map(toml_path, "profile_1_standard")
    assert mapping == {"market_cap": "Market Capitalization", "roce": "ROCE %"}

    banking_mapping = load_field_map(toml_path, "profile_2_banking")
    assert banking_mapping == {"gnpa_pct": "Gross NPA %"}


def test_load_field_map_missing_file_returns_empty_dict(tmp_path):
    mapping = load_field_map(tmp_path / "nonexistent.toml", "profile_1_standard")
    assert mapping == {}


def test_load_field_map_missing_profile_section_returns_empty_dict(tmp_path):
    toml_path = tmp_path / "field_map.toml"
    toml_path.write_text('[profile_1_standard]\nmarket_cap = "Market Cap"\n', encoding="utf-8")

    mapping = load_field_map(toml_path, "profile_9_unknown")
    assert mapping == {}


def test_load_field_map_invalid_toml_raises(tmp_path):
    toml_path = tmp_path / "field_map.toml"
    toml_path.write_text("not [ valid toml", encoding="utf-8")

    with pytest.raises(FieldMapError):
        load_field_map(toml_path, "profile_1_standard")
