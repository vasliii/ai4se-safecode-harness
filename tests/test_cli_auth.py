"""CLI tests for safecode auth commands."""

from __future__ import annotations

from typer.testing import CliRunner

from safecode.cli import app
import safecode.cli.auth as auth_module


class FakeCredentialManager:
    status_value = "missing"
    set_calls: list[str] = []
    clear_calls = 0
    set_error: Exception | None = None

    def set_api_key(self, key: str) -> None:
        type(self).set_calls.append(key)
        if type(self).set_error is not None:
            raise type(self).set_error

    def status(self) -> str:
        return type(self).status_value

    def clear_api_key(self) -> None:
        type(self).clear_calls += 1


def reset_fake_credentials() -> None:
    FakeCredentialManager.status_value = "missing"
    FakeCredentialManager.set_calls = []
    FakeCredentialManager.clear_calls = 0
    FakeCredentialManager.set_error = None


def invoke(args: list[str]):
    return CliRunner().invoke(app, args)


def test_safecode_help_exits_successfully():
    result = invoke(["--help"])

    assert result.exit_code == 0
    assert "SafeCode Harness" in result.output


def test_auth_help_exits_successfully():
    result = invoke(["auth", "--help"])

    assert result.exit_code == 0
    assert "set" in result.output
    assert "status" in result.output
    assert "clear" in result.output


def test_auth_set_calls_credential_manager(monkeypatch):
    reset_fake_credentials()
    monkeypatch.setattr(auth_module, "CredentialManager", FakeCredentialManager)
    monkeypatch.setattr(auth_module.getpass, "getpass", lambda prompt: "test-key-value")

    result = invoke(["auth", "set"])

    assert result.exit_code == 0
    assert FakeCredentialManager.set_calls == ["test-key-value"]
    assert "API Key saved successfully" in result.output
    assert "test-key-value" not in result.output


def test_auth_set_empty_input_reports_error(monkeypatch):
    reset_fake_credentials()
    monkeypatch.setattr(auth_module, "CredentialManager", FakeCredentialManager)
    monkeypatch.setattr(auth_module.getpass, "getpass", lambda prompt: "   ")

    result = invoke(["auth", "set"])

    assert result.exit_code != 0
    assert FakeCredentialManager.set_calls == []
    assert "Key cannot be empty" in result.output


def test_auth_status_configured(monkeypatch):
    reset_fake_credentials()
    FakeCredentialManager.status_value = "configured"
    monkeypatch.setattr(auth_module, "CredentialManager", FakeCredentialManager)

    result = invoke(["auth", "status"])

    assert result.exit_code == 0
    assert "API Key: configured" in result.output


def test_auth_status_missing(monkeypatch):
    reset_fake_credentials()
    FakeCredentialManager.status_value = "missing"
    monkeypatch.setattr(auth_module, "CredentialManager", FakeCredentialManager)

    result = invoke(["auth", "status"])

    assert result.exit_code == 0
    assert "API Key: missing" in result.output


def test_auth_status_does_not_leak_key(monkeypatch):
    reset_fake_credentials()
    FakeCredentialManager.status_value = "configured"
    monkeypatch.setattr(auth_module, "CredentialManager", FakeCredentialManager)

    result = invoke(["auth", "status"])

    assert "super-secret-api-key" not in result.output
    assert "configured" in result.output


def test_auth_clear_calls_credential_manager(monkeypatch):
    reset_fake_credentials()
    monkeypatch.setattr(auth_module, "CredentialManager", FakeCredentialManager)

    result = invoke(["auth", "clear"])

    assert result.exit_code == 0
    assert FakeCredentialManager.clear_calls == 1
    assert "API Key cleared" in result.output


def test_auth_set_keyring_write_failure_prints_actionable_error(monkeypatch):
    reset_fake_credentials()
    FakeCredentialManager.set_error = RuntimeError("keyring backend unavailable")
    monkeypatch.setattr(auth_module, "CredentialManager", FakeCredentialManager)
    monkeypatch.setattr(auth_module.getpass, "getpass", lambda prompt: "test-key-value")

    result = invoke(["auth", "set"])

    assert result.exit_code != 0
    assert "Failed to save API Key" in result.output
    assert "SAFECODE_API_KEY" in result.output
    assert "test-key-value" not in result.output
