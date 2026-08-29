"""Load and validate an AppConfig from a TOML file."""

from __future__ import annotations

import tomllib
from pathlib import Path

from artha.config.schema import (
    AppConfig,
    BenchmarkConfig,
    BudgetConfig,
    ConfigError,
    IPSConfig,
    SizingLimits,
)


def load_config(path: str | Path) -> AppConfig:
    """Read a TOML config file and return a validated AppConfig.

    Raises ConfigError if the file is missing, malformed, or fails
    structural validation (see each dataclass's validate()).
    """
    config_path = Path(path)
    if not config_path.is_file():
        raise ConfigError(f"config file not found: {config_path}")

    try:
        raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {config_path}: {exc}") from exc

    try:
        ips_raw = raw["ips"]
        benchmark_raw = raw["benchmark"]
    except KeyError as exc:
        raise ConfigError(f"config missing required section: {exc}") from exc

    ips = IPSConfig(
        statement_path=ips_raw.get("statement_path", ""),
        frozen_on=ips_raw.get("frozen_on"),
    )
    benchmark = BenchmarkConfig(
        index_fund_name=benchmark_raw.get("index_fund_name", ""),
        index_fund_isin=benchmark_raw.get("index_fund_isin", ""),
        factor_fund_name=benchmark_raw.get("factor_fund_name", ""),
        factor_fund_isin=benchmark_raw.get("factor_fund_isin", ""),
        frozen_on=benchmark_raw.get("frozen_on"),
    )
    sizing = SizingLimits(**raw.get("sizing", {}))
    budget = BudgetConfig(**raw.get("budget", {}))
    db_path = raw.get("db_path", ".artha/artha.db")

    config = AppConfig(
        ips=ips,
        benchmark=benchmark,
        sizing=sizing,
        budget=budget,
        db_path=db_path,
    )

    problems = config.validate()
    if problems:
        joined = "\n  - ".join(problems)
        raise ConfigError(f"config validation failed:\n  - {joined}")

    return config
