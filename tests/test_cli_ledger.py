from __future__ import annotations

from click.testing import CliRunner

from artha.cli.main import cli

CONFIG_TOML = """
db_path = ".artha/artha.db"

[ips]
statement_path = "config/ips.md"

[benchmark]
index_fund_name = "UTI Nifty 50 Index Fund"
index_fund_isin = "INF789F01XA1"
factor_fund_name = "Nifty Quality 30 Index Fund"
factor_fund_isin = "INF789F01XA2"
"""


def _write_config(tmp_path) -> None:
    (tmp_path / "artha.toml").write_text(CONFIG_TOML, encoding="utf-8")


def test_ledger_buy_then_positions(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["ledger", "buy", "ALPHA", "--track", "A", "--quantity", "100", "--price", "50", "--trade-date", "2024-01-01", "--config", "artha.toml"],
    )
    assert result.exit_code == 0
    assert "bought 100.0 ALPHA @ 50.0" in result.output

    result = runner.invoke(cli, ["ledger", "positions", "--config", "artha.toml"])
    assert result.exit_code == 0
    assert "ALPHA (track A): qty=100.0" in result.output


def test_ledger_sell_blocked_within_12_months(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path)
    runner = CliRunner()
    runner.invoke(
        cli,
        ["ledger", "buy", "ALPHA", "--track", "A", "--quantity", "100", "--price", "50", "--trade-date", "2025-01-01", "--config", "artha.toml"],
    )
    result = runner.invoke(
        cli,
        ["ledger", "sell", "ALPHA", "--quantity", "50", "--price", "60", "--trade-date", "2025-03-01", "--config", "artha.toml"],
    )
    assert result.exit_code == 1
    assert "held <12 months" in result.output


def test_ledger_sell_with_override_reports_realized_gain(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path)
    runner = CliRunner()
    runner.invoke(
        cli,
        ["ledger", "buy", "ALPHA", "--track", "A", "--quantity", "100", "--price", "50", "--trade-date", "2025-01-01", "--config", "artha.toml"],
    )
    result = runner.invoke(
        cli,
        [
            "ledger", "sell", "ALPHA", "--quantity", "50", "--price", "60", "--trade-date", "2025-03-01",
            "--override-reason", "thesis broken", "--config", "artha.toml",
        ],
    )
    assert result.exit_code == 0
    assert "realized STCG: qty=50.0 gain=500.00" in result.output


def test_ledger_scorecard_without_benchmark_nav(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path)
    runner = CliRunner()
    runner.invoke(
        cli,
        ["ledger", "buy", "ALPHA", "--track", "A", "--quantity", "100", "--price", "50", "--trade-date", "2023-01-01", "--config", "artha.toml"],
    )
    result = runner.invoke(
        cli,
        ["ledger", "scorecard", "--track", "A", "--as-of-date", "2025-01-01", "--price", "ALPHA=80", "--config", "artha.toml"],
    )
    assert result.exit_code == 0
    assert "invested capital: 5000.00" in result.output
    assert "no benchmark NAV history yet" in result.output


def test_ledger_scorecard_with_benchmark_comparison(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path)
    runner = CliRunner()
    runner.invoke(
        cli,
        ["ledger", "buy", "ALPHA", "--track", "A", "--quantity", "100", "--price", "50", "--trade-date", "2023-01-01", "--config", "artha.toml"],
    )
    runner.invoke(cli, ["ledger", "import-benchmark-nav", "--fund-name", "UTI Nifty 50 Index Fund", "--nav-date", "2023-01-01", "--nav", "100", "--config", "artha.toml"])
    runner.invoke(cli, ["ledger", "import-benchmark-nav", "--fund-name", "UTI Nifty 50 Index Fund", "--nav-date", "2025-01-01", "--nav", "110", "--config", "artha.toml"])
    runner.invoke(cli, ["ledger", "import-benchmark-nav", "--fund-name", "Nifty Quality 30 Index Fund", "--nav-date", "2023-01-01", "--nav", "100", "--config", "artha.toml"])
    runner.invoke(cli, ["ledger", "import-benchmark-nav", "--fund-name", "Nifty Quality 30 Index Fund", "--nav-date", "2025-01-01", "--nav", "115", "--config", "artha.toml"])

    result = runner.invoke(
        cli,
        ["ledger", "scorecard", "--track", "A", "--as-of-date", "2025-01-01", "--price", "ALPHA=80", "--config", "artha.toml"],
    )
    assert result.exit_code == 0
    assert "beats frozen benchmark set" in result.output
