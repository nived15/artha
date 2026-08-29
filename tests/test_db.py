from __future__ import annotations

from artha.db import apply_migrations, connect, current_schema_version


def test_apply_migrations_creates_schema(tmp_path):
    db_path = tmp_path / "sub" / "artha.db"
    conn = connect(db_path)
    try:
        applied = apply_migrations(conn)
        assert applied == [1, 2, 3, 4]
        assert current_schema_version(conn) == 4

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {
            "schema_migrations",
            "settings",
            "journal",
            "snapshots",
            "snapshot_fields",
            "filings",
            "filing_chunks",
            "dossiers",
            "trades",
            "tax_lots",
            "realized_gains",
            "benchmark_nav",
        }.issubset(tables)
    finally:
        conn.close()

    # parent directory should have been created
    assert db_path.parent.is_dir()


def test_apply_migrations_is_idempotent(tmp_path):
    db_path = tmp_path / "artha.db"
    conn = connect(db_path)
    try:
        first = apply_migrations(conn)
        second = apply_migrations(conn)
        assert first == [1, 2, 3, 4]
        assert second == []  # nothing new to apply
    finally:
        conn.close()


def test_settings_table_roundtrip(tmp_path):
    conn = connect(tmp_path / "artha.db")
    try:
        apply_migrations(conn)
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)", ("dry_run_mode", "true")
        )
        conn.commit()
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", ("dry_run_mode",)
        ).fetchone()
        assert row["value"] == "true"
    finally:
        conn.close()
