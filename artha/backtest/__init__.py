"""Walk-forward backtesting for the ranking engine.

History arrives through a port, so the same harness runs against an in-memory
fixture or a real point-in-time store without the metrics changing.
"""

from artha.backtest.harness import BacktestResult, FoldResult, walk_forward
from artha.backtest.ports import HistoryPort, InMemoryHistory

__all__ = [
    "BacktestResult",
    "FoldResult",
    "HistoryPort",
    "InMemoryHistory",
    "walk_forward",
]
