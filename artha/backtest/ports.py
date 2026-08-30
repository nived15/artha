"""Data boundary for the walk-forward harness.

The harness never touches storage. It asks a `HistoryPort` for the universe
that existed on a date and, as a separate call, for what happened afterwards.
Splitting those two questions is what keeps lookahead out: selection can only
ever see `universe_at(as_of)`, and an outcome is fetched for that same date.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from artha.engine.features import FeatureVector


class HistoryPort(Protocol):
    """Point-in-time universe plus the outcome that followed it."""

    def as_of_dates(self) -> tuple[str, ...]: ...

    def universe_at(self, as_of: str) -> list[FeatureVector]: ...

    def realised_return(self, ticker: str, from_date: str, horizon_years: float) -> float | None: ...


@dataclass(frozen=True)
class InMemoryHistory:
    """In-process `HistoryPort` for tests and demos.

    `outcomes` holds the total return earned over the harness horizon, keyed by
    the (ticker, as_of) pair that selected it. A missing key means the outcome
    is unknown and is reported as None, never as a flat 0.0: a zero would be
    indistinguishable from a real year that went nowhere.
    """

    universes: dict[str, list[FeatureVector]] = field(default_factory=dict)
    outcomes: dict[tuple[str, str], float] = field(default_factory=dict)

    def as_of_dates(self) -> tuple[str, ...]:
        return tuple(sorted(self.universes))

    def universe_at(self, as_of: str) -> list[FeatureVector]:
        return list(self.universes.get(as_of, ()))

    def realised_return(self, ticker: str, from_date: str, horizon_years: float) -> float | None:
        # The horizon is already baked into the stored total return.
        return self.outcomes.get((ticker, from_date))
