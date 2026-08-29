"""Build CompanyRecord objects from raw Screener CSV rows + a field map.

This is the bridge between Phase 1's snapshot store (raw {csv_column:
string} rows, per artha.data.snapshot.load_rows) and Phase 2's screening
functions (which read canonical field names via CompanyRecord).
"""

from __future__ import annotations

from artha.screening.models import CompanyRecord

_STRIP_CHARS = "%, \t\n\r"


def _parse_value(raw: str | None) -> float | str | None:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    cleaned = text.strip(_STRIP_CHARS).replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return text  # keep as-is (e.g. a sector/industry label)


def build_company_records(
    rows: list[dict[str, str]],
    field_map: dict[str, str],
    *,
    arithmetic_profile: str,
    name_column: str = "Name",
) -> list[CompanyRecord]:
    """Resolve each raw CSV row into a CompanyRecord via field_map.

    Rows missing a ticker/name are skipped. A canonical field absent from
    field_map, or whose mapped column is absent from a row, is simply
    left out of that record's `fields` dict — screening functions treat a
    missing key the same as an explicit None (NEEDS_STAGE_1B), never as
    zero or as a pass.
    """
    records: list[CompanyRecord] = []
    for row in rows:
        ticker = (row.get(name_column) or "").strip()
        if not ticker:
            continue
        fields = {}
        for canonical, csv_column in field_map.items():
            if csv_column in row:
                value = _parse_value(row[csv_column])
                if value is not None:
                    fields[canonical] = value
        records.append(CompanyRecord(ticker=ticker, arithmetic_profile=arithmetic_profile, fields=fields))
    return records
