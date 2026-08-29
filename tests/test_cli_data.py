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

[data]
field_map_path = "screener_field_map.toml"
"""

FIELD_MAP_TOML = """
[profile_1_standard]
market_cap = "Market Capitalization"
price = "Current price"
roce = "Return on capital employed"
roe = "Return on equity"
debt_to_equity = "Debt to equity"
opm = "OPM"
sales_growth_3y = "Sales growth 3Years"
profit_growth_3y = "Profit growth 3Years"
pe_ratio = "Price to Earning"
peg_ratio = "PEG"
ebit = "EBIT"
net_working_capital_ex_cash_ex_debt = "NWC"
net_fixed_assets_ex_goodwill = "Net Block"
enterprise_value = "Enterprise Value"
promoter_holding_pct = "Promoter holding"
promoter_pledge_pct = "Pledged percentage"
promoter_holding_trend_3y = "Change in promoter holding 3Years"
"""

CSV_HEADER = (
    "Name,Market Capitalization,Current price,Return on capital employed,Return on equity,"
    "Debt to equity,OPM,Sales growth 3Years,Profit growth 3Years,Price to Earning,PEG,EBIT,"
    "NWC,Net Block,Enterprise Value,Promoter holding,Pledged percentage,Change in promoter holding 3Years"
)
CSV_ROW = "Alpha Ltd,1000,50,20,18,0.4,12,10,15,10,22,8,9,1200,45.2,0,1.2"


def _setup(tmp_path):
    (tmp_path / "screener_field_map.toml").write_text(FIELD_MAP_TOML, encoding="utf-8")
    config_path = tmp_path / "artha.toml"
    config_path.write_text(CONFIG_TOML, encoding="utf-8")
    csv_path = tmp_path / "export.csv"
    csv_path.write_text(CSV_HEADER + "\r\n" + CSV_ROW + "\r\n", encoding="utf-8")
    return config_path, csv_path


def test_import_screener_passes_and_records_snapshot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path, csv_path = _setup(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["data", "import-screener", str(csv_path), "--source", "screener_profile1", "--config", str(config_path)],
    )
    assert result.exit_code == 0, result.output
    assert "§13.4 validation spike: passed" in result.output
    assert "snapshot_id:" in result.output


def test_import_screener_fails_when_field_unmapped(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path, csv_path = _setup(tmp_path)
    # Remove ebit mapping to simulate an unresolved required field.
    field_map_path = tmp_path / "screener_field_map.toml"
    field_map_path.write_text(FIELD_MAP_TOML.replace('ebit = "EBIT"\n', ""), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["data", "import-screener", str(csv_path), "--source", "screener_profile1", "--config", str(config_path)],
    )
    assert result.exit_code == 1
    assert "FAILED" in result.output


def test_show_snapshot_and_check_staleness_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path, csv_path = _setup(tmp_path)
    runner = CliRunner()

    import_result = runner.invoke(
        cli,
        [
            "data",
            "import-screener",
            str(csv_path),
            "--source",
            "screener_profile1",
            "--captured-on",
            "2020-01-01",
            "--config",
            str(config_path),
        ],
    )
    assert import_result.exit_code == 0, import_result.output
    snapshot_id = [line for line in import_result.output.splitlines() if line.startswith("snapshot_id:")][0].split(": ")[1]

    show_result = runner.invoke(cli, ["data", "show-snapshot", snapshot_id, "--config", str(config_path)])
    assert show_result.exit_code == 0
    assert snapshot_id in show_result.output

    staleness_result = runner.invoke(cli, ["data", "check-staleness", snapshot_id, "--config", str(config_path)])
    assert staleness_result.exit_code == 1
    assert "days old" in staleness_result.output


def test_import_filing_and_show_chunk_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path, _ = _setup(tmp_path)
    filing_path = tmp_path / "filing.txt"
    filing_path.write_text("Quarterly results text.\n\nSecond paragraph.", encoding="utf-8")

    runner = CliRunner()
    import_result = runner.invoke(
        cli,
        ["data", "import-filing", str(filing_path), "--doc-id", "Q1FY25", "--ticker", "ALPHA", "--config", str(config_path)],
    )
    assert import_result.exit_code == 0, import_result.output

    show_result = runner.invoke(cli, ["data", "show-chunk", "Q1FY25", "1", "--config", str(config_path)])
    assert show_result.exit_code == 0
    assert "Quarterly results text." in show_result.output
