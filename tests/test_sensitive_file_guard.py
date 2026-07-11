from __future__ import annotations

from safecode.guardrail import SensitiveFileGuard
from safecode.models import GuardrailEvent


SENSITIVE_PATHS = [
    ".env",
    ".env.production",
    ".env.backup",
    "config.key",
    "cert.pem",
    "secrets.json",
    "id_rsa",
    "id_rsa.pub",
    ".git/config",
    "nested/.env",
    "keys/deploy.pem",
]

SAFE_PATHS = [
    "src/main.py",
    "config.json",
    "README.md",
    "tests/test_app.py",
]


def assert_sensitive_blocked(event: GuardrailEvent | None, path: str) -> None:
    assert event is not None
    assert event.blocked is True
    assert event.reason == "sensitive_file_access"
    assert event.tool == "sensitive_file_guard"
    assert event.recoverable is True
    assert path in event.action_summary
    assert event.suggestion


def test_sensitive_paths_are_blocked() -> None:
    guard = SensitiveFileGuard()

    for path in SENSITIVE_PATHS:
        assert_sensitive_blocked(guard.check(path), path)


def test_safe_paths_pass() -> None:
    guard = SensitiveFileGuard()

    for path in SAFE_PATHS:
        assert guard.check(path) is None


def test_none_path_passes() -> None:
    assert SensitiveFileGuard().check(None) is None


def test_sensitive_event_reason_is_specific() -> None:
    event = SensitiveFileGuard().check(".env")

    assert_sensitive_blocked(event, ".env")
    assert event.reason == "sensitive_file_access"
