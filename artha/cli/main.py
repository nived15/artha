"""Artha CLI.

plan.md §11 Phase 0 exit criterion: `artha --version` runs. The other
subcommands are stubs for later phases (module layout in
implementation_plan.md §2: `cli/ # artha screen | artha research <ticker>
| artha review | artha order`) — they exist so the intended surface is
documented, but they refuse to run until their phase lands.
"""

from __future__ import annotations

import sys

import click

from artha import __version__
from artha.config import ConfigError, load_config
from artha.db import apply_migrations, connect, current_schema_version
from artha.secrets import SecretNotFoundError, delete_secret, has_secret, set_secret

DEFAULT_CONFIG_PATH = "config/artha.toml"
DEFAULT_DRY_RUN_SETTING = "dry_run_mode"


@click.group()
@click.version_option(version=__version__, prog_name="artha")
def cli() -> None:
    """Artha — a disciplined, documented Indian-equity research and execution pipeline."""


@cli.command()
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def init(config_path: str) -> None:
    """Bootstrap the local SQLite database and apply schema migrations.

    Reads db_path from config; falls back to the AppConfig default if the
    config file does not exist yet, so `artha init` also works before you've
    copied config/artha.example.toml to config/artha.toml.
    """
    try:
        config = load_config(config_path)
        db_path = config.db_path
    except ConfigError as exc:
        click.echo(f"warning: {exc}\n(using default db_path — copy config/artha.example.toml to {config_path} first)", err=True)
        db_path = ".artha/artha.db"

    conn = connect(db_path)
    try:
        applied = apply_migrations(conn)
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (DEFAULT_DRY_RUN_SETTING, "true"),
        )
        conn.commit()
        version = current_schema_version(conn)
    finally:
        conn.close()

    if applied:
        click.echo(f"applied migrations: {applied}")
    click.echo(f"database ready at {db_path} (schema version {version})")


@cli.group()
def config() -> None:
    """Inspect the resolved application config."""


@config.command("show")
@click.option("--config", "config_path", default=DEFAULT_CONFIG_PATH, show_default=True)
def config_show(config_path: str) -> None:
    try:
        app_config = load_config(config_path)
    except ConfigError as exc:
        click.echo(f"config error: {exc}", err=True)
        sys.exit(1)

    click.echo(f"db_path: {app_config.db_path}")
    click.echo(f"ips.statement_path: {app_config.ips.statement_path}")
    click.echo(f"ips.frozen_on: {app_config.ips.frozen_on or '(not frozen)'}")
    click.echo(f"benchmark.index_fund_name: {app_config.benchmark.index_fund_name}")
    click.echo(f"benchmark.factor_fund_name: {app_config.benchmark.factor_fund_name}")
    click.echo(f"benchmark.frozen_on: {app_config.benchmark.frozen_on or '(not frozen)'}")
    click.echo(f"sizing: {app_config.sizing}")
    click.echo(f"budget: {app_config.budget}")


@cli.group()
def secrets() -> None:
    """Manage credentials in the OS keyring (plan.md §7.4). Never stored in the repo."""


@secrets.command("set")
@click.argument("name")
def secrets_set(name: str) -> None:
    value = click.prompt(f"value for '{name}'", hide_input=True)
    set_secret(name, value)
    click.echo(f"stored secret '{name}' in the OS keyring.")


@secrets.command("get")
@click.argument("name")
def secrets_get(name: str) -> None:
    """Report whether a secret is set, without printing its value."""
    if has_secret(name):
        click.echo(f"'{name}' is set.")
    else:
        click.echo(f"'{name}' is not set.", err=True)
        sys.exit(1)


@secrets.command("delete")
@click.argument("name")
def secrets_delete(name: str) -> None:
    try:
        delete_secret(name)
    except SecretNotFoundError as exc:
        click.echo(str(exc), err=True)
        sys.exit(1)
    click.echo(f"deleted secret '{name}'.")


def _not_implemented(phase: str) -> None:
    click.echo(
        f"not implemented yet — this command belongs to {phase}, which has not been built.\n"
        "See implementation_plan.md's build sequence.",
        err=True,
    )
    sys.exit(1)


@cli.command()
def screen() -> None:
    """Run the Track A/B screening pipeline. (Phase 2 — not yet built.)"""
    _not_implemented("Phase 2 (screening + hard blocks)")


@cli.command()
@click.argument("ticker")
def research(ticker: str) -> None:
    """Run deep-dive research and generate a dossier for TICKER. (Phase 3 — not yet built.)"""
    _not_implemented("Phase 3 (deep research + dossiers)")


@cli.command()
def review() -> None:
    """Review pending dossiers and record Gate 1 (thesis approval) decisions. (Phase 3/4 — not yet built.)"""
    _not_implemented("Phase 3/4 (dossier review + paper ledger)")


@cli.command()
def order() -> None:
    """Confirm Gate 2 and place an order on Kite. (Phase 6 — not yet built.)"""
    _not_implemented("Phase 6 (execution)")


if __name__ == "__main__":
    cli()
