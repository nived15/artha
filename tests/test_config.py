from __future__ import annotations

import pytest

from artha.config import ConfigError, load_config


def _write(tmp_path, content: str):
    path = tmp_path / "artha.toml"
    path.write_text(content, encoding="utf-8")
    return path


VALID_TOML = """
db_path = ".artha/test.db"

[ips]
statement_path = "config/ips.md"
frozen_on = "2025-01-15"

[benchmark]
index_fund_name = "UTI Nifty 50 Index Fund"
index_fund_isin = "INF789F01XA1"
factor_fund_name = "Nifty Quality 30 Index Fund"
factor_fund_isin = "INF789F01XA2"
frozen_on = "2025-01-15"

[sizing]
track_a_position_pct = 0.03

[budget]
max_ai_credits_per_dossier = 3.0
"""


def test_load_config_valid(tmp_path):
    path = _write(tmp_path, VALID_TOML)
    config = load_config(path)

    assert config.db_path == ".artha/test.db"
    assert config.ips.frozen_on == "2025-01-15"
    assert config.benchmark.index_fund_name == "UTI Nifty 50 Index Fund"
    assert config.sizing.track_a_position_pct == 0.03
    assert config.budget.max_ai_credits_per_dossier == 3.0
    # unspecified fields fall back to defaults
    assert config.sizing.track_b_position_pct == 0.0125


def test_load_config_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "does-not-exist.toml")


def test_load_config_invalid_toml(tmp_path):
    path = _write(tmp_path, "this is not [valid toml")
    with pytest.raises(ConfigError, match="invalid TOML"):
        load_config(path)


def test_load_config_missing_required_section(tmp_path):
    path = _write(tmp_path, "db_path = \".artha/test.db\"\n")
    with pytest.raises(ConfigError, match="missing required section"):
        load_config(path)


def test_load_config_sizing_out_of_bounds(tmp_path):
    bad = VALID_TOML.replace("track_a_position_pct = 0.03", "track_a_position_pct = 1.5")
    path = _write(tmp_path, bad)
    with pytest.raises(ConfigError, match="track_a_position_pct"):
        load_config(path)


def test_load_config_empty_benchmark_field(tmp_path):
    bad = VALID_TOML.replace('index_fund_name = "UTI Nifty 50 Index Fund"', 'index_fund_name = ""')
    path = _write(tmp_path, bad)
    with pytest.raises(ConfigError, match="benchmark.index_fund_name"):
        load_config(path)
