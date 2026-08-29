"""Secrets: OS keyring wrapper (plan.md §7.4)."""

from artha.secrets.keyring_store import (
    SERVICE_NAME,
    SecretNotFoundError,
    delete_secret,
    get_secret,
    has_secret,
    set_secret,
)

__all__ = [
    "SERVICE_NAME",
    "SecretNotFoundError",
    "delete_secret",
    "get_secret",
    "has_secret",
    "set_secret",
]
