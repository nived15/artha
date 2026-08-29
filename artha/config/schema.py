"""Typed config schema for Artha.

Mirrors implementation_plan.md's `config/` module: IPS, benchmark, sizing
limits, and per-run budget caps. These are structural containers only —
freezing the actual IPS and benchmark is a deliberate human act (plan.md
§11 Phase 0 exit criterion), not something this loader can do for you.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class ConfigError(ValueError):
    """Raised when a config file is structurally invalid."""


@dataclass(frozen=True)
class IPSConfig:
    """Investment Policy Statement reference.

    The IPS itself is a written document (see config/ips.template.md) —
    this just records where it lives and whether it has been frozen.
    """

    statement_path: str
    frozen_on: str | None = None  # ISO date, e.g. "2025-01-15"; None until frozen

    def validate(self) -> list[str]:
        problems: list[str] = []
        if not self.statement_path.strip():
            problems.append("ips.statement_path must not be empty")
        return problems


@dataclass(frozen=True)
class BenchmarkConfig:
    """The frozen benchmark (plan.md §9): a named Nifty 50 TR index fund
    plus one named factor fund, fixed weights, recorded by name."""

    index_fund_name: str
    index_fund_isin: str
    factor_fund_name: str
    factor_fund_isin: str
    frozen_on: str | None = None  # ISO date; None until frozen

    def validate(self) -> list[str]:
        problems: list[str] = []
        for field_name in ("index_fund_name", "index_fund_isin", "factor_fund_name", "factor_fund_isin"):
            if not getattr(self, field_name).strip():
                problems.append(f"benchmark.{field_name} must not be empty")
        return problems


@dataclass(frozen=True)
class SizingLimits:
    """Cross-cutting sizing rules from plan.md §4 (per-position and sleeve-wide)."""

    track_a_position_pct: float = 0.025      # 2-3% of investable assets
    track_b_position_pct: float = 0.0125     # 1-1.5%, tighter/higher variance
    max_single_name_pct: float = 0.25
    max_sector_pct: float = 0.30
    max_smallcap_pct: float = 0.35
    track_b_sleeve_cap_pct: float = 0.40     # Track B capped at ~40% of active sleeve
    active_sleeve_start_pct: float = 0.05    # active sleeve starts at 5% of wealth

    def validate(self) -> list[str]:
        problems: list[str] = []
        pct_fields = (
            "track_a_position_pct",
            "track_b_position_pct",
            "max_single_name_pct",
            "max_sector_pct",
            "max_smallcap_pct",
            "track_b_sleeve_cap_pct",
            "active_sleeve_start_pct",
        )
        for name in pct_fields:
            value = getattr(self, name)
            if not (0.0 < value <= 1.0):
                problems.append(f"sizing.{name} must be in (0, 1], got {value}")
        return problems


@dataclass(frozen=True)
class BudgetConfig:
    """Per-run budget caps for the Stage 3/4 Agent Factory (§16 Q5).

    Honest caveat carried from implementation_plan.md §16 Q5: maxAiCredits
    is a soft, post-paid ceiling per the factory docs, not a hard pre-check.
    """

    max_ai_credits_per_dossier: float = 5.0
    max_concurrent_subagents: int = 5
    max_total_subagents: int = 20
    timeout_seconds: float = 3600.0

    def validate(self) -> list[str]:
        problems: list[str] = []
        if self.max_ai_credits_per_dossier <= 0:
            problems.append("budget.max_ai_credits_per_dossier must be > 0")
        if self.max_concurrent_subagents <= 0:
            problems.append("budget.max_concurrent_subagents must be > 0")
        if self.max_total_subagents <= 0:
            problems.append("budget.max_total_subagents must be > 0")
        if self.max_total_subagents < self.max_concurrent_subagents:
            problems.append(
                "budget.max_total_subagents must be >= budget.max_concurrent_subagents"
            )
        if self.timeout_seconds <= 0:
            problems.append("budget.timeout_seconds must be > 0")
        return problems


@dataclass(frozen=True)
class DataConfig:
    """Data-spine settings (plan.md §13.4/§13.6, implementation_plan.md Phase 1).

    Screener.in Premium's CSV export is human-triggered (§13.6) and capped
    at 50 columns per query (§13.4a). A snapshot's *age* is part of its
    provenance (§5.5) — the staleness guard refuses to build a dossier from
    a snapshot older than snapshot_max_age_days.
    """

    snapshot_dir: str = ".artha/snapshots"
    snapshot_max_age_days: int = 100  # ~1 quarter + buffer; §13.6 cadence is 2-4x/year
    max_export_columns: int = 50      # §13.4a's binding column ceiling
    field_map_path: str = "config/screener_field_map.toml"

    def validate(self) -> list[str]:
        problems: list[str] = []
        if not self.snapshot_dir.strip():
            problems.append("data.snapshot_dir must not be empty")
        if self.snapshot_max_age_days <= 0:
            problems.append("data.snapshot_max_age_days must be > 0")
        if self.max_export_columns <= 0:
            problems.append("data.max_export_columns must be > 0")
        if not self.field_map_path.strip():
            problems.append("data.field_map_path must not be empty")
        return problems


@dataclass(frozen=True)
class AppConfig:
    """The fully resolved, validated application config."""

    ips: IPSConfig
    benchmark: BenchmarkConfig
    sizing: SizingLimits = field(default_factory=SizingLimits)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    data: DataConfig = field(default_factory=DataConfig)
    db_path: str = ".artha/artha.db"

    def validate(self) -> list[str]:
        problems: list[str] = []
        problems += self.ips.validate()
        problems += self.benchmark.validate()
        problems += self.sizing.validate()
        problems += self.budget.validate()
        problems += self.data.validate()
        if not self.db_path.strip():
            problems.append("db_path must not be empty")
        return problems
