from __future__ import annotations

from click.testing import CliRunner

from artha import __version__
from artha.cli.main import cli


def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_init_creates_database(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["init", "--config", "nonexistent.toml"])
    assert result.exit_code == 0
    assert (tmp_path / ".artha" / "artha.db").is_file()
    assert "schema version 2" in result.output


def test_config_show_reports_error_for_missing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "show", "--config", "missing.toml"])
    assert result.exit_code == 1
    assert "config error" in result.output


def test_config_show_valid(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "artha.toml"
    config_path.write_text(
        """
db_path = ".artha/artha.db"

[ips]
statement_path = "config/ips.md"

[benchmark]
index_fund_name = "UTI Nifty 50 Index Fund"
index_fund_isin = "INF789F01XA1"
factor_fund_name = "Nifty Quality 30 Index Fund"
factor_fund_isin = "INF789F01XA2"
""",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "show", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "UTI Nifty 50 Index Fund" in result.output
    assert "(not frozen)" in result.output


def test_stub_commands_fail_clearly():
    runner = CliRunner()
    for args in (["research", "RELIANCE"], ["review"], ["order"]):
        result = runner.invoke(cli, args)
        assert result.exit_code == 1
        assert "not implemented yet" in result.output
