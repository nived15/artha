from __future__ import annotations

import pytest

from artha.engine.spec import FormulaSpec, FormulaSpecError, load_formula_spec


def test_defaults_are_valid_and_load_without_a_file():
    spec = load_formula_spec(None)
    assert spec.version == "v1"
    assert spec.horizons.track_a_years == 5.0


def test_missing_file_falls_back_to_defaults(tmp_path):
    spec = load_formula_spec(tmp_path / "nonexistent.toml")
    assert spec == FormulaSpec()


def test_fingerprint_is_stable_and_changes_with_coefficients():
    base = FormulaSpec()
    same = FormulaSpec()
    assert base.fingerprint == same.fingerprint

    import dataclasses

    tweaked = dataclasses.replace(base, valuation=dataclasses.replace(base.valuation, base_pe=20.0))
    assert tweaked.fingerprint != base.fingerprint


def test_toml_overrides_are_applied(tmp_path):
    path = tmp_path / "formula.toml"
    path.write_text(
        'version = "v2"\n\n[horizons]\ntrack_a_years = 7.0\n\n[gates]\nmax_promoter_pledge = 0.10\n',
        encoding="utf-8",
    )
    spec = load_formula_spec(path)
    assert spec.version == "v2"
    assert spec.horizons.track_a_years == 7.0
    assert spec.gates.max_promoter_pledge == 0.10
    # Untouched sections keep their defaults.
    assert spec.tax.ltcg_rate == 0.125


def test_unknown_key_is_rejected_rather_than_silently_ignored(tmp_path):
    path = tmp_path / "formula.toml"
    path.write_text("[gates]\nmax_promotor_pledge = 0.10\n", encoding="utf-8")
    with pytest.raises(FormulaSpecError, match="unknown keys"):
        load_formula_spec(path)


def test_growth_weights_must_sum_to_one(tmp_path):
    path = tmp_path / "formula.toml"
    path.write_text("[growth]\nw_eps_5y = 0.9\nw_sales_5y = 0.3\nw_roiic = 0.2\n", encoding="utf-8")
    with pytest.raises(FormulaSpecError, match="growth weights"):
        load_formula_spec(path)


def test_invalid_toml_raises_formula_spec_error(tmp_path):
    path = tmp_path / "formula.toml"
    path.write_text("[gates\n", encoding="utf-8")
    with pytest.raises(FormulaSpecError, match="invalid TOML"):
        load_formula_spec(path)


def test_inverted_fair_pe_band_is_rejected(tmp_path):
    path = tmp_path / "formula.toml"
    path.write_text("[valuation]\nmin_fair_pe = 50.0\nmax_fair_pe = 10.0\n", encoding="utf-8")
    with pytest.raises(FormulaSpecError, match="fair P/E band"):
        load_formula_spec(path)
