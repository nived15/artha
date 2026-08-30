"""Framework scoring.

The named investor frameworks stop being pass/fail vetoes here and become
continuous 0-1 inputs to the return model. Each composite also reports
`confidence`, the share of its input weight that was actually available, so a
score built from two of six inputs is never mistaken for a complete one.
"""

from __future__ import annotations

from dataclasses import dataclass

from artha.engine.features import LENDING_PROFILES, FeatureVector


@dataclass(frozen=True)
class ScoreComponent:
    name: str
    value: float | None  # 0..1, None when the input is unavailable
    detail: str


@dataclass(frozen=True)
class CompositeScore:
    name: str
    value: float          # 0..1, 0.0 when confidence is 0
    confidence: float     # 0..1, share of input weight that was available
    components: tuple[ScoreComponent, ...]

    @property
    def missing(self) -> tuple[str, ...]:
        return tuple(c.name for c in self.components if c.value is None)


def ramp(value: float | None, low: float, high: float) -> float | None:
    """Map value onto 0..1 across [low, high], clipped. Descending if low > high."""
    if value is None:
        return None
    if low == high:
        return 1.0 if value >= low else 0.0
    scaled = (value - low) / (high - low)
    return max(0.0, min(1.0, scaled))


def _component(fv: FeatureVector, feature: str, low: float, high: float, label: str) -> ScoreComponent:
    raw = fv.get(feature)
    scored = ramp(raw, low, high)
    detail = f"{label}: unavailable" if raw is None else f"{label}={raw:.4g} -> {scored:.2f}"
    return ScoreComponent(feature, scored, detail)


def _composite(name: str, weighted: tuple[tuple[ScoreComponent, float], ...]) -> CompositeScore:
    total_weight = sum(w for _, w in weighted)
    available = [(c, w) for c, w in weighted if c.value is not None]
    got_weight = sum(w for _, w in available)
    if got_weight == 0 or total_weight == 0:
        return CompositeScore(name, 0.0, 0.0, tuple(c for c, _ in weighted))
    value = sum(c.value * w for c, w in available) / got_weight  # type: ignore[misc]
    return CompositeScore(name, value, got_weight / total_weight, tuple(c for c, _ in weighted))


def quality_score(fv: FeatureVector) -> CompositeScore:
    """Agrawal Q, Terry Smith and the Buffett/Munger moat proxies, blended.

    Cash conversion is absent: OCF/PAT is not exportable from Screener, so it
    is assessed from filings at Stage 3 rather than guessed at here.
    """
    return _composite(
        "quality",
        (
            (_component(fv, "roce", 0.10, 0.30, "ROCE"), 0.35),
            (_component(fv, "roe", 0.10, 0.28, "ROE"), 0.30),
            (_component(fv, "interest_coverage", 2.0, 12.0, "interest cover"), 0.20),
            (_component(fv, "gross_margin", 0.20, 0.60, "gross margin"), 0.15),
        ),
    )


def growth_score(fv: FeatureVector) -> CompositeScore:
    """Agrawal G plus reported acceleration, never forward estimates."""
    return _composite(
        "growth",
        (
            (_component(fv, "profit_growth_5y", 0.05, 0.25, "5y PAT CAGR"), 0.40),
            (_component(fv, "sales_growth_3y", 0.05, 0.22, "3y sales CAGR"), 0.25),
            (_component(fv, "profit_growth_3y", 0.05, 0.25, "3y PAT CAGR"), 0.20),
            (_component(fv, "eps_growth_ttm_yoy", 0.0, 0.30, "TTM EPS YoY"), 0.15),
        ),
    )


def value_score(fv: FeatureVector) -> CompositeScore:
    """Greenblatt earnings yield, Graham cheapness, and P/B discipline.

    Greenblatt's EBIT/EV is undefined for lenders, since their enterprise
    value sweeps in deposits and borrowings. plan.md 5.4 substitutes
    PAT/MarketCap there, which is 1/(P/E). The separate P/E leg is then
    dropped rather than double-counting the same number, leaving P/B to
    carry the rest, per 5.3a's "valuation on P/B read against ROE".
    """
    pe = fv.get("pe_ratio")

    if fv.profile in LENDING_PROFILES:
        earnings_yield = 1.0 / pe if pe is not None and pe > 0 else None
        detail = (
            "PAT/MarketCap unavailable"
            if earnings_yield is None
            else f"PAT/MarketCap=1/{pe:.4g}={earnings_yield:.3f} (Artha substitution, not Greenblatt)"
        )
        return _composite(
            "value",
            (
                (ScoreComponent("earnings_yield", ramp(earnings_yield, 0.04, 0.18), detail), 0.55),
                (_component(fv, "price_to_book", 6.0, 1.0, "P/B"), 0.45),
            ),
        )

    ebit = fv.get("ebit")
    ev = fv.get("enterprise_value")
    earnings_yield = ebit / ev if ebit is not None and ev not in (None, 0) else None
    ey_component = ScoreComponent(
        "earnings_yield",
        ramp(earnings_yield, 0.04, 0.18),
        "earnings yield: unavailable" if earnings_yield is None else f"EBIT/EV={earnings_yield:.3f}",
    )
    return _composite(
        "value",
        (
            (ey_component, 0.45),
            (_component(fv, "pe_ratio", 40.0, 8.0, "P/E"), 0.35),
            (_component(fv, "price_to_book", 6.0, 1.0, "P/B"), 0.20),
        ),
    )


def governance_score(fv: FeatureVector) -> CompositeScore:
    """Promoter behaviour as a continuous signal; the hard veto lives in gates."""
    return _composite(
        "governance",
        (
            (_component(fv, "promoter_holding", 0.35, 0.65, "promoter holding"), 0.40),
            (_component(fv, "promoter_holding_trend_3y", -0.05, 0.02, "3y holding trend"), 0.35),
            (_component(fv, "promoter_pledge", 0.20, 0.0, "pledge"), 0.25),
        ),
    )


@dataclass(frozen=True)
class ScoreCard:
    quality: CompositeScore
    growth: CompositeScore
    value: CompositeScore
    governance: CompositeScore

    @property
    def confidence(self) -> float:
        parts = (self.quality, self.growth, self.value, self.governance)
        return sum(p.confidence for p in parts) / len(parts)

    @property
    def missing_features(self) -> tuple[str, ...]:
        seen: list[str] = []
        for part in (self.quality, self.growth, self.value, self.governance):
            for name in part.missing:
                if name not in seen:
                    seen.append(name)
        return tuple(seen)


def score_all(fv: FeatureVector) -> ScoreCard:
    return ScoreCard(
        quality=quality_score(fv),
        growth=growth_score(fv),
        value=value_score(fv),
        governance=governance_score(fv),
    )
