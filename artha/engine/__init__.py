"""Artha ranking engine (rebuild).

Runs alongside artha.screening while that path is retired. Composition order
is fixed: features -> gates -> scores -> expected return -> rank.
"""

from artha.engine.features import FeatureVector, build_feature_vector
from artha.engine.gates import GateReport, GateStatus, run_hard_gates
from artha.engine.ranking import Bucket, RankedCandidate, RankingRun, evaluate, rank
from artha.engine.scoring import ScoreCard, score_all
from artha.engine.spec import FormulaSpec, load_formula_spec

__all__ = [
    "Bucket",
    "FeatureVector",
    "FormulaSpec",
    "GateReport",
    "GateStatus",
    "RankedCandidate",
    "RankingRun",
    "ScoreCard",
    "build_feature_vector",
    "evaluate",
    "load_formula_spec",
    "rank",
    "run_hard_gates",
    "score_all",
]
