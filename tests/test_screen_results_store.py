from __future__ import annotations

import pytest

from artha.db import apply_migrations, connect
from artha.screening.hard_blocks import GreenblattRankResult
from artha.screening.models import CompanyRecord, Criterion, Outcome, ScreenResult
from artha.screening.pipeline import CandidateResult
from artha.screening.results_store import get_screen_results, list_screen_runs, record_screen_run


def _seed_snapshot(conn, snapshot_id="snap-1"):
    conn.execute(
        "INSERT INTO snapshots (snapshot_id, source, profile, file_path, captured_at, ingested_at, row_count, column_count) "
        "VALUES (?, 'screener_profile1', 'profile_1_standard', 'test.csv', '2026-01-01', '2026-01-01T00:00:00Z', 2, 5)",
        (snapshot_id,),
    )
    conn.commit()


def _empty_result(name: str) -> ScreenResult:
    return ScreenResult(name, "A", Outcome.PASS, ())


def _candidate(ticker: str, *, cleared: bool, excluded: bool, reasons=(), pending=(), missing=(), rank=None) -> CandidateResult:
    greenblatt = GreenblattRankResult(ticker=ticker, roc_rank=1, earnings_yield_rank=2, combined_rank=3, percentile=rank, passed=rank is not None and rank <= 10) if rank is not None else None
    return CandidateResult(
        ticker=ticker,
        track="A",
        cleared_stage1=cleared,
        stage1_screens={},
        fatal_flaw_result=_empty_result("Fatal-Flaw Checklist"),
        promoter_integrity_result=_empty_result("Promoter Integrity Red Flags"),
        greenblatt=greenblatt,
        excluded=excluded,
        exclusion_reasons=reasons,
        pending_stage3_items=pending,
        insufficient_data_fields=missing,
    )


@pytest.fixture
def conn(tmp_path):
    c = connect(tmp_path / "artha.db")
    apply_migrations(c)
    _seed_snapshot(c)
    yield c
    c.close()


def test_record_and_list_screen_run(conn):
    candidates = [
        _candidate("Alpha", cleared=True, excluded=False, rank=5.0),
        _candidate("Beta", cleared=False, excluded=True, reasons=("promoter_pledging: fail",)),
        _candidate("Gamma", cleared=False, excluded=False, missing=("ocf_to_pat",)),
    ]
    run_id = record_screen_run(conn, candidates, track="A", source="screener_profile1", arithmetic_profile="profile_1_standard", snapshot_id="snap-1")

    runs = list_screen_runs(conn)
    assert len(runs) == 1
    summary = runs[0]
    assert summary.screen_run_id == run_id
    assert summary.universe_size == 3
    assert summary.shortlist_size == 1
    assert summary.excluded_size == 1
    assert summary.pending_size == 1


def test_get_screen_results_filters_by_status(conn):
    candidates = [
        _candidate("Alpha", cleared=True, excluded=False, rank=5.0),
        _candidate("Beta", cleared=False, excluded=True, reasons=("promoter_pledging: fail",)),
        _candidate("Gamma", cleared=False, excluded=False, missing=("ocf_to_pat",)),
    ]
    run_id = record_screen_run(conn, candidates, track="A", source="screener_profile1", arithmetic_profile="profile_1_standard", snapshot_id="snap-1")

    shortlisted = get_screen_results(conn, run_id, status="shortlisted")
    assert [r.ticker for r in shortlisted] == ["Alpha"]
    assert shortlisted[0].greenblatt_percentile == 5.0

    excluded = get_screen_results(conn, run_id, status="excluded")
    assert [r.ticker for r in excluded] == ["Beta"]
    assert excluded[0].exclusion_reasons == ("promoter_pledging: fail",)

    pending = get_screen_results(conn, run_id, status="pending")
    assert [r.ticker for r in pending] == ["Gamma"]
    assert pending[0].insufficient_data_fields == ("ocf_to_pat",)


def test_get_screen_results_without_status_returns_all_in_rank_order(conn):
    candidates = [
        _candidate("Alpha", cleared=True, excluded=False, rank=5.0),
        _candidate("Beta", cleared=False, excluded=True, reasons=("x",)),
    ]
    run_id = record_screen_run(conn, candidates, track="A", source="screener_profile1", arithmetic_profile="profile_1_standard", snapshot_id="snap-1")
    all_rows = get_screen_results(conn, run_id)
    assert [r.ticker for r in all_rows] == ["Alpha", "Beta"]


def test_list_screen_runs_filters_by_track_and_source(conn):
    _seed_snapshot(conn, "snap-2")
    candidates_a = [_candidate("Alpha", cleared=True, excluded=False, rank=5.0)]
    run_a = record_screen_run(conn, candidates_a, track="A", source="screener_profile1", arithmetic_profile="profile_1_standard", snapshot_id="snap-1")

    candidates_b = [_candidate("Beta", cleared=True, excluded=False)]
    # Reuse the store with track B by passing track="B" explicitly.
    run_b = record_screen_run(conn, candidates_b, track="B", source="screener_profile2", arithmetic_profile="profile_1_standard", snapshot_id="snap-2")

    assert [r.screen_run_id for r in list_screen_runs(conn, track="A")] == [run_a]
    assert [r.screen_run_id for r in list_screen_runs(conn, source="screener_profile2")] == [run_b]
    assert len(list_screen_runs(conn)) == 2


def test_list_screen_runs_most_recent_first(conn):
    first = record_screen_run(conn, [_candidate("Alpha", cleared=True, excluded=False)], track="A", source="s1", arithmetic_profile="profile_1_standard", snapshot_id="snap-1")
    second = record_screen_run(conn, [_candidate("Beta", cleared=True, excluded=False)], track="A", source="s1", arithmetic_profile="profile_1_standard", snapshot_id="snap-1")
    runs = list_screen_runs(conn)
    assert runs[0].screen_run_id == second
    assert runs[1].screen_run_id == first
