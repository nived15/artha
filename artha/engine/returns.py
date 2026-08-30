"""Expected-return models for both tracks.

Track A decomposes a five-year CAGR into earnings growth, carry, and a capped
rerating term, less a risk penalty. Track B prices a scenario tree and takes a
probability-weighted expectation. Both then pay tax on the terminal gain and
re-annualise, so `tau_tax` is derived from arithmetic rather than assumed.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from artha.engine.features import FeatureVector
from artha.engine.scoring import ScoreCard, ramp
from artha.engine.spec import FormulaSpec


@dataclass(frozen=True)
class ReturnEstimate:
    track: str
    computable: bool
    horizon_years: float
    gross_cagr: float | None
    net_cagr: float | None
    components: dict[str, float]
    confidence: float
    notes: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()

    @property
    def tau_tax(self) -> float | None:
        if self.gross_cagr is None or self.net_cagr is None:
            return None
        return self.gross_cagr - self.net_cagr


@dataclass(frozen=True)
class Scenario:
    name: str
    probability: float
    total_return: float


@dataclass(frozen=True)
class TrackBEstimate:
    estimate: ReturnEstimate
    scenarios: tuple[Scenario, ...]
    asymmetry_ratio: float | None
    asymmetry_passed: bool


def after_tax_cagr(gross_cagr: float, horizon_years: float, tax_rate: float) -> float:
    """Tax the terminal gain, then re-annualise. Losses get no tax credit."""
    terminal = (1.0 + gross_cagr) ** horizon_years
    if terminal <= 1.0:
        return gross_cagr
    net_terminal = 1.0 + (terminal - 1.0) * (1.0 - tax_rate)
    return net_terminal ** (1.0 / horizon_years) - 1.0


def soft_cap(value: float, cap: float) -> float:
    """Bound growth without creating ties.

    A hard clip maps every high grower onto the same number, which destroys
    ordering exactly where discrimination matters most: Indian smallcap 3-year
    growth is routinely a recovery from a depressed base. This is asymptotic
    and strictly monotone, so 80% still outranks 40% while neither is
    extrapolated as sustainable.
    """
    if cap <= 0:
        return 0.0
    if value <= 0:
        return value
    return cap * (1.0 - math.exp(-value / cap))


def _weighted_available(pairs: tuple[tuple[float | None, float], ...]) -> tuple[float | None, float]:
    """Weighted mean over available inputs, renormalised. Returns (value, coverage)."""
    total = sum(w for _, w in pairs)
    present = [(v, w) for v, w in pairs if v is not None]
    got = sum(w for _, w in present)
    if got == 0 or total == 0:
        return None, 0.0
    value = sum(v * w for v, w in present) / got  # type: ignore[misc]
    return value, got / total


def sustainable_growth(fv: FeatureVector, spec: FormulaSpec) -> tuple[float | None, float, tuple[str, ...]]:
    """Blend the growth legs, renormalising over whatever is available.

    Each leg falls back to its 3-year variant when the 5-year one is absent.
    A fallback is recorded as a note, because a 3-year window carries a
    cycle risk the 5-year one partly averages out.
    """
    notes: list[str] = []

    earnings = fv.get("profit_growth_5y")
    if earnings is None:
        earnings = fv.get("profit_growth_3y")
        if earnings is not None:
            notes.append("earnings growth uses the 3y series; 5y unavailable")

    sales = fv.get("sales_growth_5y")
    if sales is None:
        sales = fv.get("sales_growth_3y")
        if sales is not None:
            notes.append("sales growth uses the 3y series; 5y unavailable")

    roiic = fv.get("roiic_3y")
    reinvestment = fv.get("reinvestment_rate")
    reinvested_growth = roiic * reinvestment if roiic is not None and reinvestment is not None else None

    value, coverage = _weighted_available(
        (
            (earnings, spec.growth.w_eps_5y),
            (sales, spec.growth.w_sales_5y),
            (reinvested_growth, spec.growth.w_roiic),
        )
    )
    if value is None:
        return None, 0.0, tuple(notes)
    return soft_cap(value, spec.growth.cap), coverage, tuple(notes)


def fair_pe(growth: float, quality: float, spec: FormulaSpec) -> float:
    raw = spec.valuation.base_pe * (1.0 + spec.valuation.k_growth * growth) * (
        1.0 + spec.valuation.k_quality * (quality - 0.5)
    )
    return max(spec.valuation.min_fair_pe, min(spec.valuation.max_fair_pe, raw))


def rerating_cagr(entry_pe: float, target_pe: float, horizon_years: float, spec: FormulaSpec) -> float:
    if entry_pe <= 0 or target_pe <= 0:
        return 0.0
    annual = math.log(target_pe / entry_pe) / horizon_years
    cap = spec.valuation.max_annual_rerating
    return max(-cap, min(cap, annual))


def risk_penalty(fv: FeatureVector, scores: ScoreCard, spec: FormulaSpec) -> float:
    leverage = ramp(fv.get("debt_to_equity"), 0.5, 2.5) or 0.0

    g3 = fv.get("profit_growth_3y")
    g5 = fv.get("profit_growth_5y")
    instability = ramp(abs(g3 - g5), 0.05, 0.40) if g3 is not None and g5 is not None else 0.0

    governance = 1.0 - scores.governance.value if scores.governance.confidence > 0 else 0.5
    fragility = 1.0 - (ramp(fv.get("current_ratio"), 0.8, 2.0) or 0.5)

    raw = (
        spec.risk.w_leverage * leverage
        + spec.risk.w_earnings_instability * (instability or 0.0)
        + spec.risk.w_governance * governance
        + spec.risk.w_fragility * fragility
    )
    return min(spec.risk.max_penalty, raw * spec.risk.max_penalty)


def estimate_track_a(fv: FeatureVector, scores: ScoreCard, spec: FormulaSpec) -> ReturnEstimate:
    horizon = spec.horizons.track_a_years
    notes: list[str] = []
    blockers: list[str] = []

    growth, growth_coverage, growth_notes = sustainable_growth(fv, spec)
    notes.extend(growth_notes)
    entry_pe = fv.get("pe_ratio")

    if growth is None:
        blockers.append("no growth input available")
    if entry_pe is None or entry_pe <= 0:
        blockers.append("entry P/E unavailable or non-positive")

    if growth is None or entry_pe is None or entry_pe <= 0:
        return ReturnEstimate(
            "A", False, horizon, None, None, {}, 0.0, tuple(notes), tuple(blockers)
        )

    carry = fv.get("dividend_yield") or 0.0
    target_pe = fair_pe(growth, scores.quality.value, spec)
    rerating = rerating_cagr(entry_pe, target_pe, horizon, spec)
    penalty = risk_penalty(fv, scores, spec)

    gross = growth + carry + rerating - penalty
    net = after_tax_cagr(gross, horizon, spec.tax.ltcg_rate)

    confidence = min(growth_coverage, scores.confidence)
    return ReturnEstimate(
        track="A",
        computable=True,
        horizon_years=horizon,
        gross_cagr=gross,
        net_cagr=net,
        components={
            "growth": growth,
            "carry": carry,
            "rerating": rerating,
            "risk_penalty": -penalty,
            "fair_pe": target_pe,
            "entry_pe": entry_pe,
        },
        confidence=confidence,
        notes=tuple(notes),
    )


class ProbabilityModel(Protocol):
    """Maps a 0-1 setup score onto (bear, base, bull) probabilities."""

    def __call__(self, setup_score: float) -> tuple[float, float, float]: ...


def default_probability_model(setup_score: float) -> tuple[float, float, float]:
    """Interpretable placeholder until calibrated on real outcome data.

    Deliberately simple and monotone: a better setup shifts weight from bear
    to bull. Replace with a fitted, reliability-checked model before sizing
    real capital on it.
    """
    s = max(0.0, min(1.0, setup_score))
    bull = 0.15 + 0.35 * s
    bear = 0.45 - 0.30 * s
    base = 1.0 - bull - bear
    return bear, base, bull


def estimate_track_b(
    fv: FeatureVector,
    scores: ScoreCard,
    spec: FormulaSpec,
    probability_model: ProbabilityModel = default_probability_model,
) -> TrackBEstimate:
    horizon = spec.horizons.track_b_years
    notes: list[str] = []

    entry_pe = fv.get("pe_ratio")
    if entry_pe is None or entry_pe <= 0:
        blocker = "entry P/E unavailable or non-positive"
        empty = ReturnEstimate("B", False, horizon, None, None, {}, 0.0, (), (blocker,))
        return TrackBEstimate(empty, (), None, False)

    b = spec.track_b
    legs = (
        ("bear", b.bear_eps_multiple, b.bear_pe_multiple),
        ("base", b.base_eps_multiple, b.base_pe_multiple),
        ("bull", b.bull_eps_multiple, b.bull_pe_multiple),
    )
    returns = {name: eps_m * pe_m - 1.0 for name, eps_m, pe_m in legs}

    setup = 0.5 * scores.growth.value + 0.3 * scores.value.value + 0.2 * scores.quality.value
    p_bear, p_base, p_bull = probability_model(setup)
    probabilities = {"bear": p_bear, "base": p_base, "bull": p_bull}

    scenarios = tuple(
        Scenario(name, probabilities[name], returns[name]) for name, _, _ in legs
    )

    expected_total = sum(s.probability * s.total_return for s in scenarios)
    gross = (1.0 + expected_total) ** (1.0 / horizon) - 1.0 if expected_total > -1.0 else -1.0
    tax_rate = spec.tax.ltcg_rate if horizon >= spec.tax.long_term_years else spec.tax.stcg_rate
    net = after_tax_cagr(gross, horizon, tax_rate)

    downside = returns["bear"]
    asymmetry = returns["bull"] / abs(downside) if downside < 0 else None
    if asymmetry is None:
        notes.append("bear case is non-negative, asymmetry ratio undefined")
    passed = asymmetry is not None and asymmetry >= b.min_asymmetry_ratio

    estimate = ReturnEstimate(
        track="B",
        computable=True,
        horizon_years=horizon,
        gross_cagr=gross,
        net_cagr=net,
        components={
            "expected_total_return": expected_total,
            "entry_pe": entry_pe,
            "setup_score": setup,
            "p_bear": p_bear,
            "p_base": p_base,
            "p_bull": p_bull,
        },
        confidence=scores.confidence,
        notes=tuple(notes),
    )
    return TrackBEstimate(estimate, scenarios, asymmetry, passed)
