from __future__ import annotations

from artha.data.screener_import import ingest_and_validate, validate_export
from artha.db import apply_migrations, connect

FIELD_MAP = {
    "market_cap": "Market Capitalization",
    "price": "Current price",
    "roce": "Return on capital employed",
    "roe": "Return on equity",
    "debt_to_equity": "Debt to equity",
    "opm": "OPM",
    "sales_growth_3y": "Sales growth 3Years",
    "profit_growth_3y": "Profit growth 3Years",
    "pe_ratio": "Price to Earning",
    "peg_ratio": "PEG",
    "ebit": "EBIT",
    "net_working_capital_ex_cash_ex_debt": "NWC",
    "net_fixed_assets_ex_goodwill": "Net Block",
    "enterprise_value": "Enterprise Value",
    "promoter_holding_pct": "Promoter holding",
    "promoter_pledge_pct": "Pledged percentage",
    "promoter_holding_trend_3y": "Change in promoter holding 3Years",
}

HEADER = ",".join(
    [
        "Name",
        "Market Capitalization",
        "Current price",
        "Return on capital employed",
        "Return on equity",
        "Debt to equity",
        "OPM",
        "Sales growth 3Years",
        "Profit growth 3Years",
        "Price to Earning",
        "PEG",
        "EBIT",
        "NWC",
        "Net Block",
        "Enterprise Value",
        "Promoter holding",
        "Pledged percentage",
        "Change in promoter holding 3Years",
    ]
)


def _row(name: str, promoter_holding: str = "45.2") -> str:
    return ",".join([name, "1000", "50", "20", "18", "0.4", "12", "10", "15", "10", "22", "8", "9", "1200", "1300", promoter_holding, "0", "1.2"])


def _sample_csv(n_rows: int = 3, blank_promoter_rows: int = 0) -> str:
    rows = [_row(f"Company{i}", promoter_holding="" if i < blank_promoter_rows else "45.2") for i in range(n_rows)]
    return "\r\n".join([HEADER, *rows]) + "\r\n"


def test_validate_export_passes_when_all_required_fields_mapped_and_present():
    csv_text = _sample_csv(n_rows=3)
    report = validate_export(csv_text=csv_text, profile="profile_1_standard", field_map=FIELD_MAP, max_columns=50)

    assert report.column_ceiling_ok is True
    assert report.unmapped_fields == ()
    assert report.missing_columns == ()
    assert report.passed is True
    assert report.row_count == 3


def test_validate_export_flags_unmapped_required_field():
    incomplete_map = dict(FIELD_MAP)
    del incomplete_map["ebit"]
    csv_text = _sample_csv(n_rows=2)
    report = validate_export(csv_text=csv_text, profile="profile_1_standard", field_map=incomplete_map, max_columns=50)

    assert "ebit" in report.unmapped_fields
    assert report.passed is False


def test_validate_export_flags_missing_column_in_csv():
    map_with_wrong_column = dict(FIELD_MAP)
    map_with_wrong_column["ebit"] = "Column Not In CSV"
    csv_text = _sample_csv(n_rows=2)
    report = validate_export(csv_text=csv_text, profile="profile_1_standard", field_map=map_with_wrong_column, max_columns=50)

    assert "ebit" in report.missing_columns
    assert report.passed is False


def test_validate_export_column_ceiling_check():
    csv_text = _sample_csv(n_rows=2)
    report = validate_export(csv_text=csv_text, profile="profile_1_standard", field_map=FIELD_MAP, max_columns=5)

    assert report.column_ceiling_ok is False
    assert report.passed is False


def test_validate_export_computes_completeness_percentage():
    csv_text = _sample_csv(n_rows=4, blank_promoter_rows=1)
    report = validate_export(csv_text=csv_text, profile="profile_1_standard", field_map=FIELD_MAP, max_columns=50)

    promoter_field = next(fc for fc in report.field_completeness if fc.canonical_name == "promoter_holding_pct")
    assert promoter_field.non_null_count == 3
    assert promoter_field.total_count == 4
    assert promoter_field.completeness_pct == 75.0


def test_ingest_and_validate_persists_field_completeness(tmp_path):
    conn = connect(tmp_path / "artha.db")
    apply_migrations(conn)

    csv_bytes = _sample_csv(n_rows=3).encode("utf-8")
    record, report = ingest_and_validate(
        conn,
        csv_bytes=csv_bytes,
        source="screener_profile1",
        profile="profile_1_standard",
        field_map=FIELD_MAP,
        snapshot_dir=str(tmp_path / "snapshots"),
    )

    assert report.passed is True
    rows = conn.execute(
        "SELECT field_name, completeness_pct FROM snapshot_fields WHERE snapshot_id = ?",
        (record.snapshot_id,),
    ).fetchall()
    field_names = {row["field_name"] for row in rows}
    assert "ebit" in field_names
    assert "promoter_holding_pct" in field_names
