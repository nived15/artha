"""Screener.in export ingestion + the §13.4 validation spike.

plan.md §13.4: "Test Screener Premium's export against the full Stage 1/
Stage 2 formula set before building on it." This module implements the
four checks that are mechanically verifiable from a real CSV export:

  (a) Column ceiling  — does the export stay within the 50-column cap?
  (b) Shareholding     — do the shareholding fields resolve via the field map?
  (c) Export reuse     — a human/legal question, out of scope for code.
  (d) Completeness     — per-field non-null percentage across the export's rows.
  (e) Sector fields    — do banking/insurance fields resolve, for those profiles?

(c) is deliberately not automated — reading a vendor's terms of service is
a human act, recorded in docs/phase1_validation_spike.md, not a code check.
"""

from __future__ import annotations

import csv
import io
import sqlite3
from dataclasses import dataclass, field

from artha.data.fields import required_fields_for_profile
from artha.data.snapshot import SnapshotRecord, ingest_bytes


@dataclass(frozen=True)
class FieldCompleteness:
    canonical_name: str
    csv_column: str | None       # None if the field map has no mapping for this field
    non_null_count: int
    total_count: int

    @property
    def completeness_pct(self) -> float:
        return (self.non_null_count / self.total_count * 100.0) if self.total_count else 0.0


@dataclass(frozen=True)
class ValidationReport:
    profile: str
    row_count: int
    column_count: int
    max_columns: int
    column_ceiling_ok: bool
    unmapped_fields: tuple[str, ...]       # required fields absent from the field map
    missing_columns: tuple[str, ...]       # mapped, but the CSV doesn't actually have that column
    field_completeness: tuple[FieldCompleteness, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        """Spike (a)+(b)/(e) pass: within column ceiling and every required
        field resolves to an actual CSV column. Completeness (d) is
        reported but does not gate pass/fail — a low but nonzero
        completeness is a data-quality fact to record, not a hard block.
        """
        return self.column_ceiling_ok and not self.unmapped_fields and not self.missing_columns


def validate_export(
    *,
    csv_text: str,
    profile: str,
    field_map: dict[str, str],
    max_columns: int = 50,
) -> ValidationReport:
    """Run the §13.4 spike checks against exported CSV text (already decoded)."""
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    header = reader.fieldnames or []
    column_count = len(header)
    row_count = len(rows)

    required = required_fields_for_profile(profile)

    unmapped: list[str] = []
    missing_columns: list[str] = []
    completeness: list[FieldCompleteness] = []

    for req in required:
        csv_column = field_map.get(req.canonical_name)
        if csv_column is None:
            unmapped.append(req.canonical_name)
            continue
        if csv_column not in header:
            missing_columns.append(req.canonical_name)
            completeness.append(FieldCompleteness(req.canonical_name, csv_column, 0, row_count))
            continue
        non_null = sum(1 for row in rows if (row.get(csv_column) or "").strip())
        completeness.append(FieldCompleteness(req.canonical_name, csv_column, non_null, row_count))

    return ValidationReport(
        profile=profile,
        row_count=row_count,
        column_count=column_count,
        max_columns=max_columns,
        column_ceiling_ok=column_count <= max_columns,
        unmapped_fields=tuple(unmapped),
        missing_columns=tuple(missing_columns),
        field_completeness=tuple(completeness),
    )


def ingest_and_validate(
    conn: sqlite3.Connection,
    *,
    csv_bytes: bytes,
    source: str,
    profile: str,
    field_map: dict[str, str],
    snapshot_dir: str,
    max_columns: int = 50,
    captured_at: str | None = None,
) -> tuple[SnapshotRecord, ValidationReport]:
    """Ingest a Screener export into the snapshot store and run the spike checks.

    Also persists per-field completeness into snapshot_fields so the
    spike's empirical results (§13.4(d)) are recorded, not just printed.
    """
    record = ingest_bytes(
        conn,
        data=csv_bytes,
        source=source,
        snapshot_dir=snapshot_dir,
        profile=profile,
        captured_at=captured_at,
    )
    report = validate_export(
        csv_text=csv_bytes.decode("utf-8-sig"),
        profile=profile,
        field_map=field_map,
        max_columns=max_columns,
    )

    with conn:
        for fc in report.field_completeness:
            conn.execute(
                """
                INSERT OR REPLACE INTO snapshot_fields
                    (snapshot_id, field_name, non_null_count, total_count, completeness_pct)
                VALUES (?, ?, ?, ?, ?)
                """,
                (record.snapshot_id, fc.canonical_name, fc.non_null_count, fc.total_count, fc.completeness_pct),
            )

    return record, report
