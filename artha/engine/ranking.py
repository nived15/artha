"""Ranking pipeline.

Order of operations is the whole design: gates first and unconditionally, then
scores, then expected return. A return estimate can never rescue a gate
failure, and a candidate blocked only by missing data is reported apart from
one that was genuinely rejected.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from artha.engine.features import FeatureVector
from artha.engine.gates import GateReport, run_hard_gates
from artha.engine.returns import (
    ProbabilityModel,
    ReturnEstimate,
    Scenario,
    default_probability_model,
    estimate_track_a,
    estimate_track_b,
)
from artha.engine.scoring import ScoreCard, score_all
from artha.engine.spec import FormulaSpec


class Bucket(str, Enum):
    RANKED = "ranked"                # eligible and scored
    REJECTED = "rejected"            # a hard gate said no
    INSUFFICIENT_DATA = "insufficient_data"  # cannot be judged yet


@dataclass(frozen=True)
class RankedCandidate:
    ticker: str
    track: str
    bucket: Bucket
    gates: GateReport
    scores: ScoreCard
    estimate: ReturnEstimate
    scenarios: tuple[Scenario, ...] = ()
    asymmetry_ratio: float | None = None
    reasons: tuple[str, ...] = ()
    # Stage 1b items that must be resolved before this name is buyable. Nothing
    # populates this from a single snapshot row today; multi-year history
    # checks will.
    pending_verification: tuple[str, ...] = ()

    @property
    def net_cagr(self) -> float | None:
        return self.estimate.net_cagr


def _bucket_for(gates: GateReport, estimate: ReturnEstimate) -> tuple[Bucket, tuple[str, ...]]:
    if gates.failures:
        return Bucket.REJECTED, tuple(f"{r.name}: {r.reason}" for r in gates.failures)
    if gates.unknowns:
        return Bucket.INSUFFICIENT_DATA, tuple(f"{r.name}: {r.reason}" for r in gates.unknowns)
    if not estimate.computable:
        return Bucket.INSUFFICIENT_DATA, estimate.blockers
    return Bucket.RANKED, ()


def evaluate(
    fv: FeatureVector,
    spec: FormulaSpec,
    *,
    track: str,
    probability_model: ProbabilityModel = default_probability_model,
) -> RankedCandidate:
    gates = run_hard_gates(fv, spec)
    scores = score_all(fv)

    scenarios: tuple[Scenario, ...] = ()
    asymmetry: float | None = None
    extra_reasons: tuple[str, ...] = ()

    if track == "A":
        estimate = estimate_track_a(fv, scores, spec)
    else:
        track_b = estimate_track_b(fv, scores, spec, probability_model)
        estimate = track_b.estimate
        scenarios = track_b.scenarios
        asymmetry = track_b.asymmetry_ratio
        if estimate.computable and not track_b.asymmetry_passed:
            ratio = f"{asymmetry:.2f}" if asymmetry is not None else "undefined"
            extra_reasons = (
                f"asymmetry: ratio {ratio} below required {spec.track_b.min_asymmetry_ratio:.2f}",
            )

    bucket, reasons = _bucket_for(gates, estimate)
    if bucket is Bucket.RANKED and extra_reasons:
        bucket, reasons = Bucket.REJECTED, extra_reasons

    return RankedCandidate(
        ticker=fv.ticker,
        track=track,
        bucket=bucket,
        gates=gates,
        scores=scores,
        estimate=estimate,
        scenarios=scenarios,
        asymmetry_ratio=asymmetry,
        reasons=reasons,
    )


@dataclass(frozen=True)
class RankingRun:
    track: str
    spec_version: str
    spec_fingerprint: str
    candidates: tuple[RankedCandidate, ...]

    @property
    def ranked(self) -> tuple[RankedCandidate, ...]:
        return tuple(c for c in self.candidates if c.bucket is Bucket.RANKED)

    @property
    def rejected(self) -> tuple[RankedCandidate, ...]:
        return tuple(c for c in self.candidates if c.bucket is Bucket.REJECTED)

    @property
    def insufficient(self) -> tuple[RankedCandidate, ...]:
        return tuple(c for c in self.candidates if c.bucket is Bucket.INSUFFICIENT_DATA)


def rank(
    universe: list[FeatureVector],
    spec: FormulaSpec,
    *,
    track: str,
    probability_model: ProbabilityModel = default_probability_model,
) -> RankingRun:
    """Rank a universe best-first by confidence-weighted net CAGR.

    Ranking multiplies expected return by confidence so a high estimate built
    on two available inputs does not outrank a solid one built on eight.
    """
    evaluated = [evaluate(fv, spec, track=track, probability_model=probability_model) for fv in universe]

    def sort_key(c: RankedCandidate) -> tuple[int, float, str]:
        if c.bucket is not Bucket.RANKED or c.net_cagr is None:
            return (1, 0.0, c.ticker)
        return (0, -(c.net_cagr * c.estimate.confidence), c.ticker)

    return RankingRun(
        track=track,
        spec_version=spec.version,
        spec_fingerprint=spec.fingerprint,
        candidates=tuple(sorted(evaluated, key=sort_key)),
    )
