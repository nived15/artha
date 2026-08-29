"""Persistent index over `artha screen` runs (Phase 2, implementation_plan.md).

Previously a shortlist/excluded/pending outcome only existed transiently
in the CLI's console output and inside one `screen_run` journal event's
JSON payload — unlike every other phase's output (snapshots, filings,
dossiers), there was no dedicated table to list a past shortlist from
without re-running the whole screen. This module is that missing index.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from artha.screening.pipeline import CandidateResult


@dataclass(frozen=True)
class ScreenResultRow:
    screen_run_id: str
    ticker: str
    track: str
    source: str
    arithmetic_profile: str
    snapshot_id: str
    status: str  # "shortlisted" | "excluded" | "pending"
    cleared_stage1: bool
    exclusion_reasons: tuple[str, ...]
    pending_stage3_items: tuple[str, ...]
    insufficient_data_fields: tuple[str, ...]
    greenblatt_combined_rank: int | None
    greenblatt_percentile: float | None
    rank_order: int
    created_at: str


def _status_for(candidate: CandidateResult) -> str:
    if candidate.excluded:
        return "excluded"
    if candidate.cleared_stage1:
        return "shortlisted"
    return "pending"


def record_screen_run(
    conn: sqlite3.Connection,
    candidates: list[CandidateResult],
    *,
    track: str,
    source: str,
    arithmetic_profile: str,
    snapshot_id: str,
) -> str:
    """Persist one `artha screen` run's full candidate list. Returns the
    new screen_run_id. `candidates` must already be in the pipeline's own
    sorted order (screen_track_a/screen_track_b's return value) — that
    order is preserved as `rank_order` so a later listing reproduces
    exactly what the CLI printed at the time.
    """
    screen_run_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    with conn:
        for rank_order, candidate in enumerate(candidates):
            conn.execute(
                """
                INSERT INTO screen_results
                    (screen_run_id, ticker, track, source, arithmetic_profile, snapshot_id, status,
                     cleared_stage1, exclusion_reasons_json, pending_stage3_items_json,
                     insufficient_data_fields_json, greenblatt_combined_rank, greenblatt_percentile,
                     rank_order, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    screen_run_id,
                    candidate.ticker,
                    track,
                    source,
                    arithmetic_profile,
                    snapshot_id,
                    _status_for(candidate),
                    1 if candidate.cleared_stage1 else 0,
                    json.dumps(list(candidate.exclusion_reasons)),
                    json.dumps(list(candidate.pending_stage3_items)),
                    json.dumps(list(candidate.insufficient_data_fields)),
                    candidate.greenblatt.combined_rank if candidate.greenblatt else None,
                    candidate.greenblatt.percentile if candidate.greenblatt else None,
                    rank_order,
                    created_at,
                ),
            )
    return screen_run_id


def _row_to_result(row: sqlite3.Row) -> ScreenResultRow:
    return ScreenResultRow(
        screen_run_id=row["screen_run_id"],
        ticker=row["ticker"],
        track=row["track"],
        source=row["source"],
        arithmetic_profile=row["arithmetic_profile"],
        snapshot_id=row["snapshot_id"],
        status=row["status"],
        cleared_stage1=bool(row["cleared_stage1"]),
        exclusion_reasons=tuple(json.loads(row["exclusion_reasons_json"])),
        pending_stage3_items=tuple(json.loads(row["pending_stage3_items_json"])),
        insufficient_data_fields=tuple(json.loads(row["insufficient_data_fields_json"])),
        greenblatt_combined_rank=row["greenblatt_combined_rank"],
        greenblatt_percentile=row["greenblatt_percentile"],
        rank_order=row["rank_order"],
        created_at=row["created_at"],
    )


def get_screen_results(
    conn: sqlite3.Connection,
    screen_run_id: str,
    *,
    status: str | None = None,
) -> list[ScreenResultRow]:
    """List a past screen run's candidates, optionally filtered by status
    ('shortlisted' | 'excluded' | 'pending'), in the run's own rank order."""
    query = "SELECT * FROM screen_results WHERE screen_run_id = ?"
    params: list[str] = [screen_run_id]
    if status is not None:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY rank_order ASC"
    rows = conn.execute(query, params).fetchall()
    return [_row_to_result(r) for r in rows]


@dataclass(frozen=True)
class ScreenRunSummary:
    screen_run_id: str
    track: str
    source: str
    arithmetic_profile: str
    snapshot_id: str
    created_at: str
    universe_size: int
    shortlist_size: int
    excluded_size: int
    pending_size: int


def list_screen_runs(conn: sqlite3.Connection, *, track: str | None = None, source: str | None = None) -> list[ScreenRunSummary]:
    """List past screen runs (most recent first), one row per run with
    aggregate counts — the "which runs exist" index, complementing
    get_screen_results's "what was in this run" detail."""
    query = """
        SELECT screen_run_id, track, source, arithmetic_profile, snapshot_id, MIN(created_at) AS created_at,
               COUNT(*) AS universe_size,
               SUM(CASE WHEN status = 'shortlisted' THEN 1 ELSE 0 END) AS shortlist_size,
               SUM(CASE WHEN status = 'excluded' THEN 1 ELSE 0 END) AS excluded_size,
               SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_size
        FROM screen_results
        WHERE 1=1
    """
    params: list[str] = []
    if track is not None:
        query += " AND track = ?"
        params.append(track)
    if source is not None:
        query += " AND source = ?"
        params.append(source)
    query += " GROUP BY screen_run_id ORDER BY created_at DESC"

    rows = conn.execute(query, params).fetchall()
    return [
        ScreenRunSummary(
            screen_run_id=r["screen_run_id"],
            track=r["track"],
            source=r["source"],
            arithmetic_profile=r["arithmetic_profile"],
            snapshot_id=r["snapshot_id"],
            created_at=r["created_at"],
            universe_size=r["universe_size"],
            shortlist_size=r["shortlist_size"],
            excluded_size=r["excluded_size"],
            pending_size=r["pending_size"],
        )
        for r in rows
    ]
