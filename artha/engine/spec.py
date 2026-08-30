"""Versioned formula specification.

Every coefficient and threshold the engine uses lives here, not as a literal
buried in a screen. A run records `FormulaSpec.fingerprint`, so a ranking can
always be traced back to the exact numbers that produced it.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import asdict, dataclass, replace
from pathlib import Path


class FormulaSpecError(ValueError):
    """Raised when a formula spec file is malformed or out of range."""


@dataclass(frozen=True)
class Horizons:
    track_a_years: float = 5.0
    track_b_years: float = 3.0


@dataclass(frozen=True)
class GateThresholds:
    max_promoter_pledge: float = 0.20
    min_promoter_holding: float = 0.40
    min_market_cap_cr: float = 200.0
    max_debt_to_equity: float = 2.0


@dataclass(frozen=True)
class GrowthModel:
    w_eps_5y: float = 0.5
    w_sales_5y: float = 0.3
    w_roiic: float = 0.2
    cap: float = 0.30


@dataclass(frozen=True)
class ValuationModel:
    base_pe: float = 15.0
    k_growth: float = 4.0
    k_quality: float = 0.6
    min_fair_pe: float = 6.0
    max_fair_pe: float = 45.0
    max_annual_rerating: float = 0.06


@dataclass(frozen=True)
class RiskModel:
    w_leverage: float = 0.4
    w_earnings_instability: float = 0.3
    w_governance: float = 0.2
    w_fragility: float = 0.1
    max_penalty: float = 0.10


@dataclass(frozen=True)
class TaxModel:
    ltcg_rate: float = 0.125
    stcg_rate: float = 0.20
    long_term_years: float = 1.0


@dataclass(frozen=True)
class TrackBModel:
    min_asymmetry_ratio: float = 3.0
    bear_eps_multiple: float = 0.75
    base_eps_multiple: float = 1.35
    bull_eps_multiple: float = 2.10
    bear_pe_multiple: float = 0.70
    base_pe_multiple: float = 1.00
    bull_pe_multiple: float = 1.40


@dataclass(frozen=True)
class FormulaSpec:
    version: str = "v1"
    horizons: Horizons = Horizons()
    gates: GateThresholds = GateThresholds()
    growth: GrowthModel = GrowthModel()
    valuation: ValuationModel = ValuationModel()
    risk: RiskModel = RiskModel()
    tax: TaxModel = TaxModel()
    track_b: TrackBModel = TrackBModel()

    @property
    def fingerprint(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def validate(self) -> None:
        if self.horizons.track_a_years <= 0 or self.horizons.track_b_years <= 0:
            raise FormulaSpecError("horizons must be positive")
        weights = (self.growth.w_eps_5y, self.growth.w_sales_5y, self.growth.w_roiic)
        if abs(sum(weights) - 1.0) > 1e-9:
            raise FormulaSpecError(f"growth weights must sum to 1.0, got {sum(weights)}")
        if self.valuation.min_fair_pe <= 0 or self.valuation.max_fair_pe <= self.valuation.min_fair_pe:
            raise FormulaSpecError("fair P/E band is inverted or non-positive")
        if not 0 <= self.tax.ltcg_rate < 1 or not 0 <= self.tax.stcg_rate < 1:
            raise FormulaSpecError("tax rates must be in [0, 1)")
        if self.track_b.min_asymmetry_ratio <= 0:
            raise FormulaSpecError("min_asymmetry_ratio must be positive")


_SECTIONS: dict[str, type] = {
    "horizons": Horizons,
    "gates": GateThresholds,
    "growth": GrowthModel,
    "valuation": ValuationModel,
    "risk": RiskModel,
    "tax": TaxModel,
    "track_b": TrackBModel,
}


def load_formula_spec(path: str | Path | None = None) -> FormulaSpec:
    """Load a spec from TOML, falling back to the built-in defaults.

    A missing file is not an error: the defaults are the documented v1 model,
    and running without a local override should still be reproducible.
    """
    spec = FormulaSpec()
    if path is None:
        spec.validate()
        return spec

    spec_path = Path(path)
    if not spec_path.is_file():
        spec.validate()
        return spec

    try:
        raw = tomllib.loads(spec_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise FormulaSpecError(f"invalid TOML in {spec_path}: {exc}") from exc

    overrides: dict[str, object] = {}
    if isinstance(raw.get("version"), str):
        overrides["version"] = raw["version"]

    for section, section_type in _SECTIONS.items():
        table = raw.get(section)
        if not isinstance(table, dict):
            continue
        current = getattr(spec, section)
        known = {f for f in current.__dataclass_fields__}
        unknown = set(table) - known
        if unknown:
            raise FormulaSpecError(f"unknown keys in [{section}]: {sorted(unknown)}")
        overrides[section] = replace(current, **table)

    spec = replace(spec, **overrides)  # type: ignore[arg-type]
    spec.validate()
    return spec
