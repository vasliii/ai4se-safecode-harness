"""Tests for API key credential lookup and status."""

from __future__ import annotations

from pathlib import Path

import pytest

from safecode.auth.credentials import CredentialManager


class FakeKeyring:
    def __init__(self, value: str | None = None, *, fail_get: bool = False) -> None:
        self.value = value
        self.fail_get = fail_get
        self.set_calls: list[tuple[str, str, str]] = []
        self.delete_calls: list[tuple[str, str]] = []

    def get_password(self, service: str, username: str) -> str | None:
        if self.fail_get:
            raise RuntimeError("keyring unavailable")
        assert service == "safecode-harness"
        assert username == "api_key"
        return self.value

    def set_password(self, service: str, username: str, key: str) -> None:
        self.set_calls.append((service, username, key))
        self.value = key

    def delete_password(self, service: str, username: str) -> None:
        self.delete_calls.append((service, username))
        self.value = None


def test_get_api_key_returns_keyring_value(monkeypatch, tmp_path):
    fake_keyring = FakeKeyring("keyring-value")
    monkeypatch.setattr("safecode.auth.credentials.keyring", fake_keyring)
    monkeypatch.chdir(tmp_path)

    assert CredentialManager().get_api_key() == "keyring-value"


def test_get_api_key_falls_back_to_environment(monkeypatch, tmp_path):
    fake_keyring = FakeKeyring(None)
    monkeypatch.setattr("safecode.auth.credentials.keyring", fake_keyring)
    monkeypatch.setenv("SAFECODE_API_KEY", "env-value")
    monkeypatch.chdir(tmp_path)

    assert CredentialManager().get_api_key() == "env-value"


def test_get_api_key_falls_back_to_dotenv(monkeypatch, tmp_path):
    fake_keyring = FakeKeyring(None)
    monkeypatch.setattr("safecode.auth.credentials.keyring", fake_keyring)
    monkeypatch.delenv("SAFECODE_API_KEY", raising=False)
    (tmp_path / ".env").write_text("OTHER=value\nSAFECODE_API_KEY=dotenv-value\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert CredentialManager().get_api_key() == "dotenv-value"


def test_get_api_key_returns_none_when_all_sources_missing(monkeypatch, tmp_path):
    fake_keyring = FakeKeyring(None)
    monkeypatch.setattr("safecode.auth.credentials.keyring", fake_keyring)
    monkeypatch.delenv("SAFECODE_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    assert CredentialManager().get_api_key() is None


def test_keyring_has_priority_over_environment(monkeypatch, tmp_path):
    fake_keyring = FakeKeyring("keyring-value")
    monkeypatch.setattr("safecode.auth.credentials.keyring", fake_keyring)
    monkeypatch.setenv("SAFECODE_API_KEY", "env-value")
    monkeypatch.chdir(tmp_path)

    assert CredentialManager().get_api_key() == "keyring-value"


def test_set_api_key_stores_value_in_keyring(monkeypatch, tmp_path):
    fake_keyring = FakeKeyring(None)
    monkeypatch.setattr("safecode.auth.credentials.keyring", fake_keyring)
    monkeypatch.chdir(tmp_path)

    CredentialManager().set_api_key("new-value")

    assert fake_keyring.set_calls == [("safecode-harness", "api_key", "new-value")]


def test_clear_api_key_removes_keyring_value_and_allows_environment_fallback(monkeypatch, tmp_path):
    fake_keyring = FakeKeyring("keyring-value")
    monkeypatch.setattr("safecode.auth.credentials.keyring", fake_keyring)
    monkeypatch.setenv("SAFECODE_API_KEY", "env-value")
    monkeypatch.chdir(tmp_path)

    manager = CredentialManager()
    manager.clear_api_key()

    assert fake_keyring.delete_calls == [("safecode-harness", "api_key")]
    assert manager.get_api_key() == "env-value"


def test_status_reports_configured_or_missing_without_leaking_key(monkeypatch, tmp_path):
    fake_keyring = FakeKeyring("super-secret-test-key")
    monkeypatch.setattr("safecode.auth.credentials.keyring", fake_keyring)
    monkeypatch.chdir(tmp_path)

    configured = CredentialManager().status()

    assert configured == "configured"
    assert "super-secret-test-key" not in configured

    fake_keyring.value = None
    monkeypatch.delenv("SAFECODE_API_KEY", raising=False)
    assert CredentialManager().status() == "missing"


def test_keyring_get_error_still_falls_back_to_environment(monkeypatch, tmp_path):
    fake_keyring = FakeKeyring(fail_get=True)
    monkeypatch.setattr("safecode.auth.credentials.keyring", fake_keyring)
    monkeypatch.setenv("SAFECODE_API_KEY", "env-value")
    monkeypatch.chdir(tmp_path)

    assert CredentialManager().get_api_key() == "env-value"


def test_dotenv_parser_handles_quotes_and_ignores_comments(monkeypatch, tmp_path):
    fake_keyring = FakeKeyring(None)
    monkeypatch.setattr("safecode.auth.credentials.keyring", fake_keyring)
    monkeypatch.delenv("SAFECODE_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "# SAFECODE_API_KEY=ignored\nSAFECODE_API_KEY='quoted-dotenv-value'\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert CredentialManager().get_api_key() == "quoted-dotenv-value"
