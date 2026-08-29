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
