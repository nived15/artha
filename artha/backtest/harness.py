"""Walk-forward backtest over the ranking engine.

One fold per as-of date. Each fold ranks only what was visible on that date and
scores the top slice against what followed. Unknown outcomes stay None the whole
way through: they lower `coverage` instead of being folded into the averages as
a zero, so a thin sample reads as thin rather than as a mediocre result. Every
metric over an empty set is None, never 0.0.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from artha.backtest.ports import HistoryPort
from artha.engine.ranking import rank
from artha.engine.returns import ProbabilityModel, default_probability_model
from artha.engine.spec import FormulaSpec


@dataclass(frozen=True)
class FoldResult:
    """One as-of date: what the engine saw, what it picked, what happened."""

    as_of: str
    ranked_count: int
    rejected_count: int
    insufficient_count: int
    selected: tuple[str, ...]
    realised: tuple[float | None, ...]

    @property
    def known_returns(self) -> tuple[float, ...]:
        return tuple(r for r in self.realised if r is not None)


@dataclass(frozen=True)
class BacktestResult:
    track: str
    spec_fingerprint: str
    folds: tuple[FoldResult, ...]

    @property
    def total_selected(self) -> int:
        return sum(len(f.selected) for f in self.folds)

    @property
    def known_returns(self) -> tuple[float, ...]:
        return tuple(r for f in self.folds for r in f.realised if r is not None)

    @property
    def coverage(self) -> float | None:
        """Share of selections whose outcome is actually known."""
        total = self.total_selected
        if total == 0:
            return None
        return len(self.known_returns) / total

    @property
    def hit_rate(self) -> float | None:
        known = self.known_returns
        if not known:
            return None
        return sum(1 for r in known if r > 0.0) / len(known)

    @property
    def mean_realised(self) -> float | None:
        known = self.known_returns
        if not known:
            return None
        return statistics.fmean(known)

    @property
    def median_realised(self) -> float | None:
        known = self.known_returns
        if not known:
            return None
        return statistics.median(known)


def _horizon_for(spec: FormulaSpec, track: str) -> float:
    if track == "A":
        return spec.horizons.track_a_years
    if track == "B":
        return spec.horizons.track_b_years
    raise ValueError(f"unknown track {track!r}, expected 'A' or 'B'")


def walk_forward(
    history: HistoryPort,
    spec: FormulaSpec,
    *,
    track: str,
    top_n: int = 25,
    horizon_years: float | None = None,
    probability_model: ProbabilityModel = default_probability_model,
) -> BacktestResult:
    """Replay the ranking engine date by date and measure what it picked.

    Selection for a fold uses `universe_at(as_of)` alone, and outcomes are only
    ever requested for that same `as_of`, so no fold can borrow information from
    a later one.
    """
    if top_n <= 0:
        raise ValueError(f"top_n must be positive, got {top_n}")
    horizon = _horizon_for(spec, track) if horizon_years is None else horizon_years

    folds: list[FoldResult] = []
    for as_of in sorted(history.as_of_dates()):
        run = rank(
            history.universe_at(as_of),
            spec,
            track=track,
            probability_model=probability_model,
        )
        picks = run.ranked[:top_n]
        folds.append(
            FoldResult(
                as_of=as_of,
                ranked_count=len(run.ranked),
                rejected_count=len(run.rejected),
                insufficient_count=len(run.insufficient),
                selected=tuple(c.ticker for c in picks),
                realised=tuple(
                    history.realised_return(c.ticker, as_of, horizon) for c in picks
                ),
            )
        )

    return BacktestResult(
        track=track,
        spec_fingerprint=spec.fingerprint,
        folds=tuple(folds),
    )
