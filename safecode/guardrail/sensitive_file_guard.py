"""Sensitive file guardrail for protected credential-like paths."""

from __future__ import annotations

import fnmatch
from pathlib import PurePosixPath
from typing import Optional

from safecode.models import GuardrailEvent


SENSITIVE_FILE_PATTERNS = (
    ".env",
    ".env.*",
    "*.key",
    "*.pem",
    "secrets.json",
    "id_rsa",
    "id_rsa.pub",
)
SENSITIVE_PATH_PATTERNS = (
    ".git/config",
)


class SensitiveFileGuard:
    """Block access to files that commonly contain credentials or secrets."""

    def check(self, path: str | None) -> Optional[GuardrailEvent]:
        if path is None:
            return None

        path_value = str(path)
        if self._is_sensitive(path_value):
            return self._blocked(path_value)
        return None

    def _is_sensitive(self, path: str) -> bool:
        normalized = path.replace("\\", "/").strip("/")
        if normalized == "":
            return False

        if normalized in SENSITIVE_PATH_PATTERNS:
            return True

        parts = PurePosixPath(normalized).parts
        if len(parts) >= 2 and parts[-2:] == (".git", "config"):
            return True

        filename = parts[-1] if parts else normalized
        return any(fnmatch.fnmatchcase(filename, pattern) for pattern in SENSITIVE_FILE_PATTERNS)

    def _blocked(self, path: str) -> GuardrailEvent:
        return GuardrailEvent(
            reason="sensitive_file_access",
            tool="sensitive_file_guard",
            action_summary=f"attempted sensitive file access: {path}",
            recoverable=True,
            suggestion="Choose a non-sensitive project file and avoid reading or writing credentials.",
        )
