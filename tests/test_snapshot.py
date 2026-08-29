from __future__ import annotations

from datetime import date

import pytest

from artha.data.snapshot import (
    StaleSnapshotError,
    assert_not_stale,
    get_snapshot,
    ingest_bytes,
    latest_snapshot,
    load_rows,
)
from artha.db import apply_migrations, connect

SAMPLE_CSV = (
    "Name,Market Capitalization,Current price,Promoter holding\r\n"
    "Alpha Ltd,1000,50,45.2\r\n"
    "Beta Ltd,2000,75,60.1\r\n"
).encode("utf-8")


def _fresh_conn(tmp_path):
    conn = connect(tmp_path / "artha.db")
    apply_migrations(conn)
    return conn


def test_ingest_bytes_stores_file_and_row(tmp_path):
    conn = _fresh_conn(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    record = ingest_bytes(
        conn,
        data=SAMPLE_CSV,
        source="screener_profile1",
        snapshot_dir=snapshot_dir,
        profile="profile_1_standard",
        captured_at="2025-06-01",
    )

    assert record.row_count == 2
    assert record.column_count == 4
    assert record.captured_at == "2025-06-01"

    stored = get_snapshot(conn, record.snapshot_id)
    assert stored == record

    rows = load_rows(record)
    assert rows[0]["Name"] == "Alpha Ltd"


def test_ingest_bytes_is_idempotent_by_content(tmp_path):
    conn = _fresh_conn(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    first = ingest_bytes(conn, data=SAMPLE_CSV, source="screener_profile1", snapshot_dir=snapshot_dir)
    second = ingest_bytes(conn, data=SAMPLE_CSV, source="screener_profile1", snapshot_dir=snapshot_dir)

    assert first.snapshot_id == second.snapshot_id
    count = conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
    assert count == 1


def test_latest_snapshot_picks_most_recent_captured_at(tmp_path):
    conn = _fresh_conn(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    ingest_bytes(conn, data=SAMPLE_CSV, source="s", snapshot_dir=snapshot_dir, captured_at="2025-01-01")
    newer_csv = SAMPLE_CSV + b"\r\n"
    newer = ingest_bytes(conn, data=newer_csv, source="s", snapshot_dir=snapshot_dir, captured_at="2025-06-01")

    latest = latest_snapshot(conn, "s")
    assert latest.snapshot_id == newer.snapshot_id


def test_assert_not_stale_raises_past_threshold(tmp_path):
    conn = _fresh_conn(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    record = ingest_bytes(conn, data=SAMPLE_CSV, source="s", snapshot_dir=snapshot_dir, captured_at="2025-01-01")

    assert_not_stale(record, max_age_days=365, as_of=date(2025, 6, 1))  # within threshold, no raise

    with pytest.raises(StaleSnapshotError):
        assert_not_stale(record, max_age_days=100, as_of=date(2025, 6, 1))
