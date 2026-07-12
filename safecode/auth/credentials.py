"""Credential management for SafeCode API keys."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import keyring


class CredentialManager:
    """Read and manage API keys without exposing secret values."""

    _SERVICE_NAME = "safecode-harness"
    _USERNAME = "api_key"
    _ENV_NAME = "SAFECODE_API_KEY"

    def get_api_key(self) -> Optional[str]:
        """Return the configured API key from keyring, env, or .env."""
        key = self._get_keyring_key()
        if key:
            return key

        key = os.getenv(self._ENV_NAME)
        if key:
            return key

        return self._get_dotenv_key(Path.cwd() / ".env")

    def set_api_key(self, key: str) -> None:
        """Store an API key in the system keyring."""
        keyring.set_password(self._SERVICE_NAME, self._USERNAME, key)

    def clear_api_key(self) -> None:
        """Remove the keyring API key when present."""
        try:
            keyring.delete_password(self._SERVICE_NAME, self._USERNAME)
        except Exception:
            return

    def status(self) -> str:
        """Return whether an API key is configured without revealing it."""
        return "configured" if self.get_api_key() else "missing"

    def _get_keyring_key(self) -> Optional[str]:
        try:
            return keyring.get_password(self._SERVICE_NAME, self._USERNAME)
        except Exception:
            return None

    def _get_dotenv_key(self, path: Path) -> Optional[str]:
        if not path.exists():
            return None

        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return None

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            name, value = stripped.split("=", 1)
            if name.strip() != self._ENV_NAME:
                continue
            return self._clean_dotenv_value(value)
        return None

    def _clean_dotenv_value(self, value: str) -> Optional[str]:
        cleaned = value.strip()
        if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in {"'", '"'}:
            cleaned = cleaned[1:-1]
        return cleaned or None
