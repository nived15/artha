"""Append-only journal (plan.md §2.2, §3, §11): a record that cannot be
quietly revised after the fact.

Each row's hash covers the previous row's hash plus its own fields, so any
row that is edited or deleted after the fact breaks the chain — verify()
detects that deterministically. This is deliberately Phase-0-generic: it
does not know about dossiers, orders, or any later-phase concept — those
phases just call append() with their own event_type/entity_type/payload.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

GENESIS_HASH = ""


@dataclass(frozen=True)
class JournalEntry:
    id: int
    ts: str
    event_type: str
    entity_type: str
    entity_id: str
    payload: dict[str, Any]
    prev_hash: str
    row_hash: str


def _compute_hash(prev_hash: str, ts: str, event_type: str, entity_type: str, entity_id: str, payload_json: str) -> str:
    digest_input = "|".join([prev_hash, ts, event_type, entity_type, entity_id, payload_json])
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()


class Journal:
    """Thin wrapper around the `journal` table for a single SQLite connection."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def _last_hash(self) -> str:
        row = self._conn.execute(
            "SELECT row_hash FROM journal ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else GENESIS_HASH

    def append(
        self,
        event_type: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any],
    ) -> JournalEntry:
        """Append one immutable event. Never call UPDATE/DELETE on this table directly."""
        ts = datetime.now(timezone.utc).isoformat()
        payload_json = json.dumps(payload, sort_keys=True, default=str)
        prev_hash = self._last_hash()
        row_hash = _compute_hash(prev_hash, ts, event_type, entity_type, entity_id, payload_json)

        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO journal
                    (ts, event_type, entity_type, entity_id, payload_json, prev_hash, row_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (ts, event_type, entity_type, entity_id, payload_json, prev_hash, row_hash),
            )
        return JournalEntry(
            id=cursor.lastrowid,
            ts=ts,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            prev_hash=prev_hash,
            row_hash=row_hash,
        )

    def all_entries(self) -> list[JournalEntry]:
        rows = self._conn.execute(
            """
            SELECT id, ts, event_type, entity_type, entity_id, payload_json, prev_hash, row_hash
            FROM journal ORDER BY id ASC
            """
        ).fetchall()
        return [
            JournalEntry(
                id=r["id"],
                ts=r["ts"],
                event_type=r["event_type"],
                entity_type=r["entity_type"],
                entity_id=r["entity_id"],
                payload=json.loads(r["payload_json"]),
                prev_hash=r["prev_hash"],
                row_hash=r["row_hash"],
            )
            for r in rows
        ]

    def verify_chain(self) -> tuple[bool, str | None]:
        """Recompute every row's hash and confirm the chain is intact.

        Returns (True, None) if valid, or (False, reason) at the first
        break found — e.g. a row edited/deleted out from under the chain.
        """
        expected_prev = GENESIS_HASH
        for entry in self.all_entries():
            if entry.prev_hash != expected_prev:
                return False, f"journal id={entry.id}: prev_hash mismatch (chain broken)"
            payload_json = json.dumps(entry.payload, sort_keys=True, default=str)
            recomputed = _compute_hash(
                entry.prev_hash, entry.ts, entry.event_type, entry.entity_type, entry.entity_id, payload_json
            )
            if recomputed != entry.row_hash:
                return False, f"journal id={entry.id}: row_hash mismatch (row tampered)"
            expected_prev = entry.row_hash
        return True, None
