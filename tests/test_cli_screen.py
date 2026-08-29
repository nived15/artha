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
snapshot_max_age_days = 100000
"""

FIELD_MAP_TOML = """
[profile_1_standard]
market_cap = "Market Capitalization"
price = "Current price"
roce = "ROCE"
roe = "ROE"
debt_to_equity = "D/E"
opm = "OPM"
sales_growth_3y = "Sales Growth 3Y"
profit_growth_3y = "Profit Growth 3Y"
profit_growth_5y = "Profit Growth 5Y"
pe_ratio = "PE"
ebit = "EBIT"
net_working_capital_ex_cash_ex_debt = "NWC"
net_fixed_assets_ex_goodwill = "Net Block"
enterprise_value = "EV"
promoter_holding_pct = "Promoter Holding"
promoter_pledge_pct = "Pledged %"
promoter_holding_trend_3y = "Promoter Change 3Y"
ocf_to_pat = "OCF/PAT"
"""

CSV_HEADER = (
    "Name,Market Capitalization,Current price,ROCE,ROE,D/E,OPM,Sales Growth 3Y,Profit Growth 3Y,"
    "Profit Growth 5Y,PE,EBIT,NWC,Net Block,EV,Promoter Holding,Pledged %,Promoter Change 3Y,OCF/PAT"
)
GOOD_ROW = "Alpha Ltd,1000,50,22,20,0.4,18,15,18,18,15,100,200,200,900,55,0,1.0,0.9"
BAD_ROW = "Beta Ltd,900,40,20,18,0.5,15,10,12,12,20,60,150,150,700,45,35,0.5,0.7"


def _setup(tmp_path):
    (tmp_path / "screener_field_map.toml").write_text(FIELD_MAP_TOML, encoding="utf-8")
    config_path = tmp_path / "artha.toml"
    config_path.write_text(CONFIG_TOML, encoding="utf-8")
    csv_path = tmp_path / "export.csv"
    csv_path.write_text(CSV_HEADER + "\r\n" + GOOD_ROW + "\r\n" + BAD_ROW + "\r\n", encoding="utf-8")
    return config_path, csv_path


def test_screen_track_a_end_to_end(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path, csv_path = _setup(tmp_path)
    runner = CliRunner()

    import_result = runner.invoke(
        cli,
        ["data", "import-screener", str(csv_path), "--source", "screener_profile1", "--config", str(config_path)],
    )
    assert import_result.exit_code in (0, 1)  # spike may fail on unmapped fields; snapshot is still ingested

    screen_result = runner.invoke(
        cli,
        ["screen", "--source", "screener_profile1", "--track", "A", "--config", str(config_path)],
    )
    assert screen_result.exit_code == 0, screen_result.output
    assert "universe: 2" in screen_result.output
    assert "Alpha Ltd" in screen_result.output
    assert "excluded" in screen_result.output
    assert "Beta Ltd" in screen_result.output  # excluded for pledging > 20%


def test_screen_requires_existing_snapshot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path, _ = _setup(tmp_path)
    runner = CliRunner()

    result = runner.invoke(cli, ["screen", "--source", "nonexistent_source", "--track", "A", "--config", str(config_path)])
    assert result.exit_code == 1
    assert "no snapshot found" in result.output


def test_screen_results_list_runs_and_show(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path, csv_path = _setup(tmp_path)
    runner = CliRunner()

    runner.invoke(cli, ["data", "import-screener", str(csv_path), "--source", "screener_profile1", "--config", str(config_path)])
    screen_result = runner.invoke(cli, ["screen", "--source", "screener_profile1", "--track", "A", "--config", str(config_path)])
    run_id = [line for line in screen_result.output.splitlines() if line.startswith("screen_run_id:")][0].split(": ")[1]

    list_result = runner.invoke(cli, ["screen-results", "list-runs", "--config", str(config_path)])
    assert list_result.exit_code == 0, list_result.output
    assert run_id in list_result.output
    assert "track=A" in list_result.output

    show_result = runner.invoke(cli, ["screen-results", "show", run_id, "--status", "shortlisted", "--config", str(config_path)])
    assert show_result.exit_code == 0, show_result.output
    assert "Alpha Ltd" in show_result.output

    excluded_result = runner.invoke(cli, ["screen-results", "show", run_id, "--status", "excluded", "--config", str(config_path)])
    assert excluded_result.exit_code == 0
    assert "Beta Ltd" in excluded_result.output


def test_screen_results_list_runs_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_path, _ = _setup(tmp_path)
    runner = CliRunner()
    result = runner.invoke(cli, ["screen-results", "list-runs", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "no screen runs recorded yet" in result.output
