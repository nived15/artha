"""Bridge from a ranking run into the dossier's quantitative section.

The only supported way to produce a ReturnAssessment. Keeping construction
here means the numbers in a dossier always trace back to an actual engine
run and its formula fingerprint, rather than being typed in by an agent.
"""

from __future__ import annotations

from artha.dossier.schema import ReturnAssessment, ScenarioLine
from artha.engine.gates import GateStatus
from artha.engine.ranking import Bucket, RankedCandidate


class NotRankableError(ValueError):
    """Raised when a candidate has no defensible return estimate to record."""


def return_assessment_from_candidate(
    candidate: RankedCandidate,
    *,
    spec_version: str,
    spec_fingerprint: str,
) -> ReturnAssessment:
    """Build the dossier's quantitative section from a ranked candidate.

    Refuses anything not in the RANKED bucket: a dossier is the case for
    buying something, and there is no case to make for a name the engine
    rejected or could not evaluate.
    """
    if candidate.bucket is not Bucket.RANKED:
        raise NotRankableError(
            f"{candidate.ticker} is in bucket {candidate.bucket.value}, not ranked: "
            f"{'; '.join(candidate.reasons) or 'no reason recorded'}"
        )
    estimate = candidate.estimate
    if estimate.gross_cagr is None or estimate.net_cagr is None:
        raise NotRankableError(f"{candidate.ticker} has no computed return estimate")

    passed = tuple(r.name for r in candidate.gates.results if r.status is GateStatus.PASS)
    failed = tuple(r.name for r in candidate.gates.results if r.status is GateStatus.FAIL)

    return ReturnAssessment(
        track=candidate.track,
        horizon_years=estimate.horizon_years,
        gross_cagr=estimate.gross_cagr,
        net_cagr=estimate.net_cagr,
        confidence=estimate.confidence,
        components=dict(estimate.components),
        spec_version=spec_version,
        spec_fingerprint=spec_fingerprint,
        scenarios=tuple(
            ScenarioLine(s.name, s.probability, s.total_return) for s in candidate.scenarios
        ),
        asymmetry_ratio=candidate.asymmetry_ratio,
        gates_passed=passed,
        gates_failed=failed,
        pending_verification=candidate.pending_verification,
    )
