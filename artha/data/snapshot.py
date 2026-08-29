"""Content-addressable snapshot store (implementation_plan.md §16 Q6).

The Screener CSV export *is* the immutable artifact (plan.md §13.2a/§13.6):
a dated, hashed, version-controlled export makes any Stage 1a run exactly
reproducible. This module stores the raw bytes under a sha256-derived path
(so re-ingesting the identical export is a no-op) and records provenance
metadata in the `snapshots` table.

The staleness guard (§13.6) is enforced here rather than left to callers:
a number's age is part of its provenance (§5.5), so refusing to build on a
stale snapshot is a hard block, not a warning.
"""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path


class StaleSnapshotError(Exception):
    """Raised when a snapshot is older than the configured staleness threshold."""


@dataclass(frozen=True)
class SnapshotRecord:
    snapshot_id: str
    source: str
    profile: str | None
    file_path: str
    captured_at: str  # ISO date
    ingested_at: str  # ISO datetime
    row_count: int
    column_count: int


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ingest_bytes(
    conn: sqlite3.Connection,
    *,
    data: bytes,
    source: str,
    snapshot_dir: str | Path,
    file_suffix: str = ".csv",
    profile: str | None = None,
    captured_at: str | None = None,
) -> SnapshotRecord:
    """Store raw export bytes content-addressably and record its metadata.

    Idempotent: re-ingesting byte-identical content returns the existing
    record without rewriting the file or the DB row (dedup is the point of
    content-addressing — it also means re-running the exact same export
    never produces a second "snapshot" to confuse provenance).
    """
    snapshot_id = _sha256_bytes(data)
    existing = get_snapshot(conn, snapshot_id)
    if existing is not None:
        return existing

    root = Path(snapshot_dir)
    shard = root / snapshot_id[:2]
    shard.mkdir(parents=True, exist_ok=True)
    file_path = shard / f"{snapshot_id}{file_suffix}"
    if not file_path.exists():
        file_path.write_bytes(data)

    row_count, column_count = _count_csv_rows_columns(data)
    captured_at = captured_at or date.today().isoformat()
    ingested_at = datetime.now(timezone.utc).isoformat()

    with conn:
        conn.execute(
            """
            INSERT INTO snapshots
                (snapshot_id, source, profile, file_path, captured_at, ingested_at, row_count, column_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                source,
                profile,
                str(file_path),
                captured_at,
                ingested_at,
                row_count,
                column_count,
            ),
        )

    return SnapshotRecord(
        snapshot_id=snapshot_id,
        source=source,
        profile=profile,
        file_path=str(file_path),
        captured_at=captured_at,
        ingested_at=ingested_at,
        row_count=row_count,
        column_count=column_count,
    )


def _count_csv_rows_columns(data: bytes) -> tuple[int, int]:
    import csv
    import io

    text = data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return 0, 0
    header = rows[0]
    return max(len(rows) - 1, 0), len(header)


def _row_to_record(row: sqlite3.Row) -> SnapshotRecord:
    return SnapshotRecord(
        snapshot_id=row["snapshot_id"],
        source=row["source"],
        profile=row["profile"],
        file_path=row["file_path"],
        captured_at=row["captured_at"],
        ingested_at=row["ingested_at"],
        row_count=row["row_count"],
        column_count=row["column_count"],
    )


def get_snapshot(conn: sqlite3.Connection, snapshot_id: str) -> SnapshotRecord | None:
    row = conn.execute(
        "SELECT * FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)
    ).fetchone()
    return _row_to_record(row) if row else None


def latest_snapshot(conn: sqlite3.Connection, source: str) -> SnapshotRecord | None:
    row = conn.execute(
        "SELECT * FROM snapshots WHERE source = ? ORDER BY captured_at DESC, ingested_at DESC LIMIT 1",
        (source,),
    ).fetchone()
    return _row_to_record(row) if row else None


def load_rows(record: SnapshotRecord) -> list[dict[str, str]]:
    """Read back the stored, immutable CSV as a list of {column: value} rows."""
    import csv

    with open(record.file_path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def assert_not_stale(record: SnapshotRecord, max_age_days: int, as_of: date | None = None) -> None:
    """Raise StaleSnapshotError if record.captured_at is older than max_age_days.

    plan.md §13.6: "the app must refuse to generate a dossier from a
    snapshot older than a configured threshold."
    """
    as_of = as_of or date.today()
    captured = date.fromisoformat(record.captured_at)
    age_days = (as_of - captured).days
    if age_days > max_age_days:
        raise StaleSnapshotError(
            f"snapshot {record.snapshot_id} captured {record.captured_at} is {age_days} days old "
            f"(threshold: {max_age_days} days) — refusing to build on stale data (plan.md §13.6)"
        )
