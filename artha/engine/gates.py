"""Hard gates: deterministic vetoes that no return estimate can override.

Two rules the v1 code blurred:

1. A gate that cannot be evaluated is not a pass. Unknown fails closed.
2. "Definitively bad" and "we do not know" are different outcomes and are
   reported separately, so a zero-eligible run tells you whether the universe
   is genuinely bad or the data is simply missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from artha.engine.features import LENDING_PROFILES, FeatureVector
from artha.engine.spec import FormulaSpec


class GateStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    INSUFFICIENT_DATA = "insufficient_data"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class GateResult:
    name: str
    status: GateStatus
    reason: str
    features_used: tuple[str, ...] = ()

    @property
    def blocks(self) -> bool:
        return self.status in (GateStatus.FAIL, GateStatus.INSUFFICIENT_DATA)


@dataclass(frozen=True)
class GateReport:
    results: tuple[GateResult, ...]

    @property
    def eligible(self) -> bool:
        return not any(r.blocks for r in self.results)

    @property
    def failures(self) -> tuple[GateResult, ...]:
        return tuple(r for r in self.results if r.status is GateStatus.FAIL)

    @property
    def unknowns(self) -> tuple[GateResult, ...]:
        return tuple(r for r in self.results if r.status is GateStatus.INSUFFICIENT_DATA)

    @property
    def missing_features(self) -> tuple[str, ...]:
        seen: list[str] = []
        for result in self.unknowns:
            for name in result.features_used:
                if name not in seen:
                    seen.append(name)
        return tuple(seen)


Gate = Callable[[FeatureVector, FormulaSpec], GateResult]


def _compare(
    *,
    name: str,
    feature: str,
    value: float | None,
    limit: float,
    at_most: bool,
    label: str,
) -> GateResult:
    if value is None:
        return GateResult(name, GateStatus.INSUFFICIENT_DATA, f"{feature} unavailable", (feature,))
    ok = value <= limit if at_most else value >= limit
    comparator = "<=" if at_most else ">="
    return GateResult(
        name,
        GateStatus.PASS if ok else GateStatus.FAIL,
        f"{label}: {value:.4g} {comparator} {limit:.4g} is {ok}",
        (feature,),
    )


def promoter_pledge_gate(fv: FeatureVector, spec: FormulaSpec) -> GateResult:
    return _compare(
        name="promoter_pledge",
        feature="promoter_pledge",
        value=fv.get("promoter_pledge"),
        limit=spec.gates.max_promoter_pledge,
        at_most=True,
        label="pledged promoter holding",
    )


def promoter_holding_gate(fv: FeatureVector, spec: FormulaSpec) -> GateResult:
    return _compare(
        name="promoter_holding",
        feature="promoter_holding",
        value=fv.get("promoter_holding"),
        limit=spec.gates.min_promoter_holding,
        at_most=False,
        label="promoter holding",
    )


def liquidity_gate(fv: FeatureVector, spec: FormulaSpec) -> GateResult:
    return _compare(
        name="liquidity",
        feature="market_cap",
        value=fv.get("market_cap"),
        limit=spec.gates.min_market_cap_cr,
        at_most=False,
        label="market cap (Rs cr)",
    )


def solvency_gate(fv: FeatureVector, spec: FormulaSpec) -> GateResult:
    """Leverage is the business model for lenders, so the ratio is dropped
    rather than failed for those profiles (plan.md 5.3a)."""
    if fv.profile in LENDING_PROFILES:
        return GateResult(
            "solvency",
            GateStatus.NOT_APPLICABLE,
            f"debt to equity is not meaningful for {fv.profile}",
            ("debt_to_equity",),
        )
    return _compare(
        name="solvency",
        feature="debt_to_equity",
        value=fv.get("debt_to_equity"),
        limit=spec.gates.max_debt_to_equity,
        at_most=True,
        label="debt to equity",
    )


# Fail closed on unknown: these are plan.md 5.4 fatal flaws, and every one of
# them is reliably present in a standard export.
HARD_GATES: tuple[Gate, ...] = (
    liquidity_gate,
    promoter_pledge_gate,
    promoter_holding_gate,
    solvency_gate,
)


def run_hard_gates(fv: FeatureVector, spec: FormulaSpec, gates: tuple[Gate, ...] = HARD_GATES) -> GateReport:
    return GateReport(tuple(gate(fv, spec) for gate in gates))
