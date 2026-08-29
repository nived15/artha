from __future__ import annotations

import pytest

from artha.dossier.serialization import DossierSchemaError, dossier_from_dict
from artha.dossier.validator import validate_dossier
from tests.conftest import dossier_to_dict


def test_round_trip_track_a(valid_dossier_track_a):
    data = dossier_to_dict(valid_dossier_track_a)
    restored = dossier_from_dict(data)
    assert restored == valid_dossier_track_a
    assert validate_dossier(restored).passed is True


def test_round_trip_track_b(valid_dossier_track_b):
    data = dossier_to_dict(valid_dossier_track_b)
    restored = dossier_from_dict(data)
    assert restored == valid_dossier_track_b


def test_missing_required_key_raises_schema_error(valid_dossier_track_a):
    data = dossier_to_dict(valid_dossier_track_a)
    del data["qglp_scorecard"]
    with pytest.raises(DossierSchemaError):
        dossier_from_dict(data)


def test_missing_optional_track_conditional_section_is_none(valid_dossier_track_a):
    data = dossier_to_dict(valid_dossier_track_a)
    data.pop("davis_double_play", None)
    restored = dossier_from_dict(data)
    assert restored.davis_double_play is None
