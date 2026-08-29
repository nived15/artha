"""Secrets: OS keyring wrapper (plan.md §7.4: "Credentials in the OS
keyring. Never in the repo, never in env files committed to git.")

Phase 0 ships the wrapper only; Phase 6 (execution) is the first consumer,
storing the Kite API key/secret/access token under this namespace.
"""

from __future__ import annotations

import keyring
import keyring.errors

SERVICE_NAME = "artha"


class SecretNotFoundError(KeyError):
    """Raised when get_secret() finds nothing stored under that name."""


def set_secret(name: str, value: str) -> None:
    """Store a credential in the OS keyring under the artha namespace."""
    keyring.set_password(SERVICE_NAME, name, value)


def get_secret(name: str) -> str:
    """Retrieve a credential. Raises SecretNotFoundError if unset."""
    try:
        value = keyring.get_password(SERVICE_NAME, name)
    except keyring.errors.KeyringError as exc:
        raise SecretNotFoundError(f"keyring backend error reading '{name}': {exc}") from exc
    if value is None:
        raise SecretNotFoundError(f"no secret stored under '{name}'")
    return value


def delete_secret(name: str) -> None:
    """Remove a stored credential. No-op (raises SecretNotFoundError) if unset."""
    try:
        keyring.delete_password(SERVICE_NAME, name)
    except keyring.errors.PasswordDeleteError as exc:
        raise SecretNotFoundError(f"no secret stored under '{name}'") from exc


def has_secret(name: str) -> bool:
    try:
        get_secret(name)
        return True
    except SecretNotFoundError:
        return False
