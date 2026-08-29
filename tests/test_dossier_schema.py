from __future__ import annotations

from artha.dossier.schema import QGLPScorecard


def test_qglp_combined_score():
    scorecard = QGLPScorecard(quality=3, growth=2, longevity=2, price=1, evidence={"Q": "x", "G": "y", "L": "z", "P": "w"})
    assert scorecard.combined_score == 8


def test_qglp_validate_flags_out_of_range():
    scorecard = QGLPScorecard(quality=4, growth=2, longevity=2, price=1, evidence={})
    problems = scorecard.validate()
    assert any("quality" in p for p in problems)


def test_identity_validate_flags_empty_fields():
    from artha.dossier.schema import Identity

    identity = Identity(
        company="",
        ticker="ALPHA",
        sector="Auto",
        arithmetic_profile="profile_1_standard",
        track="A",
        date="2026-01-01",
        pipeline_run_id="run-1",
        snapshot_id="abc",
    )
    problems = identity.validate()
    assert any("company" in p for p in problems)


def test_identity_validate_flags_bad_track():
    from artha.dossier.schema import Identity

    identity = Identity(
        company="Alpha",
        ticker="ALPHA",
        sector="Auto",
        arithmetic_profile="profile_1_standard",
        track="Z",
        date="2026-01-01",
        pipeline_run_id="run-1",
        snapshot_id="abc",
    )
    problems = identity.validate()
    assert any("track" in p for p in problems)
