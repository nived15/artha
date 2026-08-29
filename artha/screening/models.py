"""Shared screening data model.

CompanyRecord is a thin, canonical-field wrapper over one snapshot row
(plan.md §13's "one row per company") — the same canonical field names
Phase 1's artha/data/fields.py and screener_field_map use, extended here
with the additional Stage 1a fields the track screens need. A field being
absent (None) is a first-class, reportable state — see the module
docstring — never silently treated as zero or as a pass.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Outcome(str, Enum):
    """The result of one screening criterion or gate."""

    PASS = "pass"
    FAIL = "fail"
    NEEDS_STAGE_1B = "needs_stage_1b"   # multi-year own-history data not in the Stage 1a snapshot
    NEEDS_STAGE_3 = "needs_stage_3"     # qualitative, LLM-verified judgment
    NOT_APPLICABLE = "not_applicable"   # criterion doesn't apply to this arithmetic profile


@dataclass(frozen=True)
class CompanyRecord:
    """One company's resolved Stage 1a fields, for one snapshot.

    `fields` uses the canonical names from artha/data/fields.py plus the
    Phase 2 additions documented in artha/screening/fields.py. Values are
    already numeric/bool/str (parsed from the raw CSV upstream) — this
    class does not parse strings itself.
    """

    ticker: str
    arithmetic_profile: str  # e.g. "profile_1_standard" — plan.md §5.3a
    fields: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str) -> Any | None:
        return self.fields.get(key)

    def get_float(self, key: str) -> float | None:
        value = self.fields.get(key)
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None


@dataclass(frozen=True)
class Criterion:
    """One named check within a screen (e.g. "ROE >= 15%")."""

    name: str
    outcome: Outcome
    detail: str
    fields_used: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScreenResult:
    """The result of one attributed screen (e.g. QGLP quality gate) for one company."""

    screen_name: str
    track: str  # "A" or "B"
    outcome: Outcome  # overall: PASS only if every mandatory criterion passed
    criteria: tuple[Criterion, ...]
    score: float | None = None
    score_max: float | None = None

    @property
    def missing_data_fields(self) -> tuple[str, ...]:
        missing: list[str] = []
        for c in self.criteria:
            if c.outcome in (Outcome.NEEDS_STAGE_1B, Outcome.NEEDS_STAGE_3):
                missing.extend(c.fields_used)
        return tuple(dict.fromkeys(missing))  # de-dup, preserve order


def overall_outcome(criteria: tuple[Criterion, ...], *, mandatory: tuple[str, ...] | None = None) -> Outcome:
    """Combine mandatory criteria into one screen-level outcome.

    Any mandatory criterion that is FAIL, NEEDS_STAGE_1B, or NEEDS_STAGE_3
    makes the whole screen non-passing — matching plan.md §5.4's "any 'no'
    or 'unknown' ends the analysis" for hard blocks. `mandatory=None` means
    every criterion given is mandatory.
    """
    relevant = [c for c in criteria if mandatory is None or c.name in mandatory]
    if not relevant:
        return Outcome.NOT_APPLICABLE
    if all(c.outcome == Outcome.PASS for c in relevant):
        return Outcome.PASS
    # A definitive FAIL is decisive regardless of what else is unknown —
    # more data would not rescue a criterion that already failed.
    if any(c.outcome == Outcome.FAIL for c in relevant):
        return Outcome.FAIL
    if any(c.outcome == Outcome.NEEDS_STAGE_1B for c in relevant):
        return Outcome.NEEDS_STAGE_1B
    if any(c.outcome == Outcome.NEEDS_STAGE_3 for c in relevant):
        return Outcome.NEEDS_STAGE_3
    return Outcome.FAIL
