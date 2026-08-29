"""SQLite schema + migrations (plan.md §11 Phase 0).

Phase 0 ships the minimal baseline: schema-version tracking, a persisted
settings table (e.g. dry_run_mode — plan.md §7: "a persisted setting, not
a CLI flag"), and the append-only journal table that artha.journal writes
to. Later phases add their own tables (dossiers, screening runs, ledger
positions, etc.) via additional numbered migrations in this same list.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Each migration is (version, description, sql). Applied in order, once,
# tracked in schema_migrations. Never edit an already-applied migration —
# append a new one instead.
_MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "phase0_baseline",
        """
        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS journal (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            ts            TEXT NOT NULL,        -- ISO 8601 UTC
            event_type    TEXT NOT NULL,
            entity_type   TEXT NOT NULL,
            entity_id     TEXT NOT NULL,
            payload_json  TEXT NOT NULL,
            prev_hash     TEXT NOT NULL,         -- hash of the previous row ('' for the first row)
            row_hash      TEXT NOT NULL UNIQUE   -- sha256(prev_hash || canonical fields)
        );

        CREATE INDEX IF NOT EXISTS idx_journal_entity
            ON journal (entity_type, entity_id);
        """,
    ),
    (
        2,
        "phase1_data_spine",
        """
        -- Content-addressable snapshot store (implementation_plan.md §16 Q6):
        -- snapshot_id is the sha256 of the raw exported file, so identical
        -- exports dedupe automatically and every dossier can cite an exact,
        -- immutable snapshot.
        CREATE TABLE IF NOT EXISTS snapshots (
            snapshot_id    TEXT PRIMARY KEY,   -- sha256 hex of the raw file
            source         TEXT NOT NULL,      -- e.g. 'screener_profile1'
            profile        TEXT,               -- §5.3a arithmetic profile name, if any
            file_path      TEXT NOT NULL,      -- path under data.snapshot_dir
            captured_at    TEXT NOT NULL,      -- ISO date the export was taken (provenance)
            ingested_at    TEXT NOT NULL,      -- ISO datetime this row was written
            row_count      INTEGER NOT NULL,
            column_count   INTEGER NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_snapshots_source
            ON snapshots (source, captured_at);

        -- Per-field completeness stats for a snapshot (§13.4(d) smallcap
        -- completeness check) — one row per canonical field name.
        CREATE TABLE IF NOT EXISTS snapshot_fields (
            snapshot_id       TEXT NOT NULL REFERENCES snapshots (snapshot_id),
            field_name        TEXT NOT NULL,
            non_null_count    INTEGER NOT NULL,
            total_count       INTEGER NOT NULL,
            completeness_pct  REAL NOT NULL,
            PRIMARY KEY (snapshot_id, field_name)
        );

        -- Filing-level provenance (doc_id -> source file, ticker, hash).
        CREATE TABLE IF NOT EXISTS filings (
            doc_id       TEXT PRIMARY KEY,
            source_path  TEXT NOT NULL,
            ticker       TEXT,
            doc_type     TEXT,
            captured_at  TEXT NOT NULL,
            ingested_at  TEXT NOT NULL,
            sha256       TEXT NOT NULL
        );

        -- Citation-preserving chunk store: (doc_id, page, text) so every
        -- dossier claim can cite an exact (doc_id, page) — plan.md §6.
        CREATE TABLE IF NOT EXISTS filing_chunks (
            doc_id       TEXT NOT NULL REFERENCES filings (doc_id),
            page         INTEGER NOT NULL,
            chunk_index  INTEGER NOT NULL,
            text         TEXT NOT NULL,
            sha256       TEXT NOT NULL,
            PRIMARY KEY (doc_id, page, chunk_index)
        );
        """,
    ),
]


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection with sane pragmas, creating parent dirs as needed."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def apply_migrations(conn: sqlite3.Connection) -> list[int]:
    """Apply any migrations not yet recorded in schema_migrations.

    Returns the list of newly-applied version numbers (empty if already
    up to date). Idempotent and safe to call on every startup.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version      INTEGER PRIMARY KEY,
            description  TEXT NOT NULL,
            applied_at   TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    applied = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}

    newly_applied: list[int] = []
    for version, description, sql in _MIGRATIONS:
        if version in applied:
            continue
        with conn:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (version, description),
            )
        newly_applied.append(version)

    return newly_applied


def current_schema_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    return row[0] or 0
