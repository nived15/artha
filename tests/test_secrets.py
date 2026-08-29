from __future__ import annotations

import pytest

import artha.secrets.keyring_store as keyring_store


class _FakeKeyring:
    """In-memory stand-in so tests never touch the real OS credential store."""

    def __init__(self):
        self._store: dict[tuple[str, str], str] = {}

    def set_password(self, service, name, value):
        self._store[(service, name)] = value

    def get_password(self, service, name):
        return self._store.get((service, name))

    def delete_password(self, service, name):
        try:
            del self._store[(service, name)]
        except KeyError:
            import keyring.errors

            raise keyring.errors.PasswordDeleteError("not found")


@pytest.fixture(autouse=True)
def fake_keyring(monkeypatch):
    fake = _FakeKeyring()
    monkeypatch.setattr(keyring_store.keyring, "set_password", fake.set_password)
    monkeypatch.setattr(keyring_store.keyring, "get_password", fake.get_password)
    monkeypatch.setattr(keyring_store.keyring, "delete_password", fake.delete_password)
    return fake


def test_set_and_get_secret():
    keyring_store.set_secret("kite_api_key", "abc123")
    assert keyring_store.get_secret("kite_api_key") == "abc123"


def test_get_missing_secret_raises():
    with pytest.raises(keyring_store.SecretNotFoundError):
        keyring_store.get_secret("does_not_exist")


def test_has_secret():
    assert keyring_store.has_secret("kite_api_key") is False
    keyring_store.set_secret("kite_api_key", "abc123")
    assert keyring_store.has_secret("kite_api_key") is True


def test_delete_secret():
    keyring_store.set_secret("kite_api_key", "abc123")
    keyring_store.delete_secret("kite_api_key")
    assert keyring_store.has_secret("kite_api_key") is False


def test_delete_missing_secret_raises():
    with pytest.raises(keyring_store.SecretNotFoundError):
        keyring_store.delete_secret("does_not_exist")
