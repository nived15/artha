from __future__ import annotations

from artha.screening.loader import build_company_records


def test_build_company_records_parses_numeric_and_keeps_text():
    rows = [
        {"Name": "Alpha Ltd", "ROE %": "18.5%", "Industry": "Auto Ancillaries", "Market Cap": "1,200"},
        {"Name": "Beta Ltd", "ROE %": "", "Industry": "Banks", "Market Cap": "800"},
    ]
    field_map = {"roe": "ROE %", "sector": "Industry", "market_cap": "Market Cap"}

    records = build_company_records(rows, field_map, arithmetic_profile="profile_1_standard")

    assert len(records) == 2
    alpha = next(r for r in records if r.ticker == "Alpha Ltd")
    assert alpha.get_float("roe") == 18.5
    assert alpha.get("sector") == "Auto Ancillaries"
    assert alpha.get_float("market_cap") == 1200.0

    beta = next(r for r in records if r.ticker == "Beta Ltd")
    assert beta.get("roe") is None  # blank value is not stored at all


def test_build_company_records_skips_rows_without_ticker():
    rows = [{"Name": "", "ROE %": "10"}]
    records = build_company_records(rows, {"roe": "ROE %"}, arithmetic_profile="profile_1_standard")
    assert records == []


def test_build_company_records_ignores_unmapped_or_missing_columns():
    rows = [{"Name": "Alpha", "ROE %": "10"}]
    field_map = {"roe": "ROE %", "debt_to_equity": "Debt to equity (missing from row)"}
    records = build_company_records(rows, field_map, arithmetic_profile="profile_1_standard")
    assert records[0].get("debt_to_equity") is None
