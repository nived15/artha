from __future__ import annotations

import pytest

from artha.backtest import BacktestResult, InMemoryHistory, walk_forward
from artha.engine.features import FeatureVector, build_feature_vector
from artha.engine.ranking import rank
from artha.engine.spec import FormulaSpec

BASE = {
    "market_cap": 800.0,
    "pe_ratio": 20.0,
    "dividend_yield": 1.0,
    "profit_growth_5y": 18.0,
    "sales_growth_5y": 15.0,
    "profit_growth_3y": 20.0,
    "roiic_3y": 30.0,
    "reinvestment_rate": 0.5,
    "roce": 30.0,
    "roe": 28.0,
    "interest_coverage": 12.0,
    "gross_margin": 60.0,
    "promoter_holding": 55.0,
    "promoter_holding_trend_3y": 1.0,
    "promoter_pledge": 0.0,
    "debt_to_equity": 0.4,
    "current_ratio": 2.5,
}


def _fv(ticker: str = "ALPHA", as_of: str = "2020-03-31", **overrides) -> FeatureVector:
    raw = dict(BASE)
    raw.update(overrides)
    return build_feature_vector(ticker=ticker, profile="profile_1_standard", as_of=as_of, raw=raw)


class _RecordingHistory:
    """InMemoryHistory that logs every call, to prove there is no lookahead."""

    def __init__(self, inner: InMemoryHistory) -> None:
        self.inner = inner
        self.universe_calls: list[str] = []
        self.outcome_calls: list[tuple[str, str, float]] = []

    def as_of_dates(self) -> tuple[str, ...]:
        return self.inner.as_of_dates()

    def universe_at(self, as_of: str) -> list[FeatureVector]:
        self.universe_calls.append(as_of)
        return self.inner.universe_at(as_of)

    def realised_return(self, ticker: str, from_date: str, horizon_years: float) -> float | None:
        self.outcome_calls.append((ticker, from_date, horizon_years))
        return self.inner.realised_return(ticker, from_date, horizon_years)


def test_one_fold_per_as_of_date_in_ascending_order():
    history = InMemoryHistory(
        universes={
            "2022-03-31": [_fv("GAMMA", as_of="2022-03-31")],
            "2020-03-31": [_fv("ALPHA", as_of="2020-03-31")],
            "2021-03-31": [_fv("BETA", as_of="2021-03-31")],
        }
    )
    result = walk_forward(history, FormulaSpec(), track="A")
    assert [f.as_of for f in result.folds] == ["2020-03-31", "2021-03-31", "2022-03-31"]


def test_top_n_truncates_the_selection():
    spec = FormulaSpec()
    universe = [
        _fv("ALPHA", profit_growth_5y=25.0),
        _fv("BETA", profit_growth_5y=20.0),
        _fv("GAMMA", profit_growth_5y=15.0),
        _fv("DELTA", profit_growth_5y=10.0),
    ]
    history = InMemoryHistory(universes={"2020-03-31": universe})

    result = walk_forward(history, spec, track="A", top_n=2)
    expected = [c.ticker for c in rank(universe, spec, track="A").ranked[:2]]

    assert result.folds[0].selected == tuple(expected)
    assert result.folds[0].ranked_count == 4
    assert result.total_selected == 2


def test_unknown_outcomes_are_excluded_from_metrics_but_lower_coverage():
    universe = [_fv("ALPHA"), _fv("BETA"), _fv("GAMMA"), _fv("DELTA")]
    history = InMemoryHistory(
        universes={"2020-03-31": universe},
        # BETA and DELTA have no recorded outcome.
        outcomes={("ALPHA", "2020-03-31"): 0.40, ("GAMMA", "2020-03-31"): -0.20},
    )
    result = walk_forward(history, FormulaSpec(), track="A")

    assert result.total_selected == 4
    assert None in result.folds[0].realised
    assert result.coverage == pytest.approx(0.5)
    assert result.hit_rate == pytest.approx(0.5)
    assert result.mean_realised == pytest.approx(0.10)


def test_metrics_are_none_when_no_outcome_is_known():
    history = InMemoryHistory(universes={"2020-03-31": [_fv("ALPHA")]})
    result = walk_forward(history, FormulaSpec(), track="A")

    assert result.total_selected == 1
    assert result.coverage == pytest.approx(0.0)
    assert result.hit_rate is None
    assert result.mean_realised is None
    assert result.median_realised is None


def test_metrics_are_none_when_nothing_was_ever_selected():
    empty = BacktestResult(track="A", spec_fingerprint="x", folds=())
    assert empty.total_selected == 0
    assert empty.coverage is None
    assert empty.hit_rate is None
    assert empty.mean_realised is None
    assert empty.median_realised is None


def test_hand_computed_hit_rate_and_mean_over_a_small_fixture():
    # A flat outcome is not a hit: the test pins the strict > 0 boundary.
    outcomes = {
        ("ALPHA", "2020-03-31"): 0.25,
        ("BETA", "2020-03-31"): -0.10,
        ("GAMMA", "2020-03-31"): 0.45,
        ("DELTA", "2020-03-31"): 0.00,
    }
    history = InMemoryHistory(
        universes={"2020-03-31": [_fv("ALPHA"), _fv("BETA"), _fv("GAMMA"), _fv("DELTA")]},
        outcomes=outcomes,
    )
    result = walk_forward(history, FormulaSpec(), track="A")

    assert result.coverage == pytest.approx(1.0)
    assert result.hit_rate == pytest.approx(0.5)          # 2 of 4 above zero
    assert result.mean_realised == pytest.approx(0.15)    # 0.60 / 4
    assert result.median_realised == pytest.approx(0.125)  # (0.00 + 0.25) / 2


def test_gate_rejected_tickers_are_never_selected():
    history = InMemoryHistory(
        universes={
            "2020-03-31": [
                _fv("GOOD"),
                _fv("PLEDGED", promoter_pledge=40.0),
                _fv("UNKNOWN", promoter_holding=None),
            ]
        },
        outcomes={("PLEDGED", "2020-03-31"): 5.0},
    )
    fold = walk_forward(history, FormulaSpec(), track="A").folds[0]

    assert fold.selected == ("GOOD",)
    assert fold.rejected_count == 1
    assert fold.insufficient_count == 1


def test_outcomes_are_only_requested_for_the_selecting_date():
    inner = InMemoryHistory(
        universes={
            "2020-03-31": [_fv("ALPHA", as_of="2020-03-31")],
            "2021-03-31": [_fv("ALPHA", as_of="2021-03-31")],
        },
        outcomes={("ALPHA", "2020-03-31"): 0.30, ("ALPHA", "2021-03-31"): -0.05},
    )
    history = _RecordingHistory(inner)
    result = walk_forward(history, FormulaSpec(), track="A")

    assert history.universe_calls == ["2020-03-31", "2021-03-31"]
    assert [(t, d) for t, d, _ in history.outcome_calls] == [
        ("ALPHA", "2020-03-31"),
        ("ALPHA", "2021-03-31"),
    ]
    assert [f.realised for f in result.folds] == [(0.30,), (-0.05,)]


def test_horizon_defaults_to_the_track_horizon_and_can_be_overridden():
    spec = FormulaSpec()
    history = _RecordingHistory(InMemoryHistory(universes={"2020-03-31": [_fv("ALPHA")]}))

    walk_forward(history, spec, track="A")
    assert history.outcome_calls[-1][2] == spec.horizons.track_a_years

    walk_forward(history, spec, track="B")
    assert history.outcome_calls[-1][2] == spec.horizons.track_b_years

    walk_forward(history, spec, track="A", horizon_years=2.0)
    assert history.outcome_calls[-1][2] == 2.0


def test_result_records_the_spec_fingerprint_and_track():
    spec = FormulaSpec()
    history = InMemoryHistory(universes={"2020-03-31": [_fv("ALPHA")]})
    result = walk_forward(history, spec, track="A")

    assert result.spec_fingerprint == spec.fingerprint
    assert result.track == "A"


def test_an_unknown_track_is_rejected_rather_than_silently_treated_as_b():
    history = InMemoryHistory(universes={"2020-03-31": [_fv("ALPHA")]})
    with pytest.raises(ValueError):
        walk_forward(history, FormulaSpec(), track="C")
