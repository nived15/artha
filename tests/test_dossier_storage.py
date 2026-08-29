from __future__ import annotations

import dataclasses

import pytest

from artha.db import apply_migrations, connect
from artha.dossier.schema import DossierSection
from artha.dossier.storage import DossierAlreadyExistsError, write_dossier, write_dossier_file


def _conn(tmp_path):
    conn = connect(tmp_path / "artha.db")
    apply_migrations(conn)
    # The dossiers table FK-references snapshots(snapshot_id); the fixture
    # dossier uses snapshot_id="deadbeef", so seed a matching row.
    conn.execute(
        "INSERT INTO snapshots (snapshot_id, source, profile, file_path, captured_at, ingested_at, row_count, column_count) "
        "VALUES ('deadbeef', 'test', 'profile_1_standard', 'test.csv', '2026-01-01', '2026-01-01T00:00:00Z', 1, 1)"
    )
    conn.commit()
    return conn


def test_write_dossier_file_creates_markdown_under_ticker_dir(tmp_path, valid_dossier_track_a):
    path = write_dossier_file(valid_dossier_track_a, run_id="run-001", dossiers_root=tmp_path / "dossiers")
    assert path.is_file()
    assert path.parent.name == "ALPHA"
    assert "# Alpha Ltd (ALPHA)" in path.read_text(encoding="utf-8")


def test_write_dossier_file_refuses_to_overwrite(tmp_path, valid_dossier_track_a):
    write_dossier_file(valid_dossier_track_a, run_id="run-001", dossiers_root=tmp_path / "dossiers")
    with pytest.raises(DossierAlreadyExistsError):
        write_dossier_file(valid_dossier_track_a, run_id="run-001", dossiers_root=tmp_path / "dossiers")


def test_write_dossier_indexes_valid_dossier(tmp_path, valid_dossier_track_a):
    conn = _conn(tmp_path)
    result = write_dossier(conn, valid_dossier_track_a, run_id="run-001", dossiers_root=tmp_path / "dossiers")

    assert result.validation.passed is True
    row = conn.execute("SELECT * FROM dossiers WHERE run_id = ?", ("run-001",)).fetchone()
    assert row["ticker"] == "ALPHA"
    assert row["stage"] == "draft"
    assert row["validation_passed"] == 1


def test_write_dossier_records_rejected_stage_for_invalid_dossier(tmp_path, valid_dossier_track_a):
    conn = _conn(tmp_path)
    invalid = dataclasses.replace(valid_dossier_track_a, disconfirming_evidence=DossierSection("Disconfirming evidence", ""))

    result = write_dossier(conn, invalid, run_id="run-002", dossiers_root=tmp_path / "dossiers")

    assert result.validation.passed is False
    row = conn.execute("SELECT stage, validation_passed FROM dossiers WHERE run_id = ?", ("run-002",)).fetchone()
    assert row["stage"] == "rejected"
    assert row["validation_passed"] == 0
    # The file is still written — the tooling records the attempt, it
    # doesn't make it disappear.
    assert (tmp_path / "dossiers" / "ALPHA" / "run-002.md").is_file()
