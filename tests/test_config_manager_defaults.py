from pathlib import Path

import pytest

from safecode.config import ConfigurationManager


def test_default_shell_allowlist_contains_exact_pytest_install_commands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    config = ConfigurationManager().load()

    assert "pip install pytest" in config.shell_allowlist
    assert "python -m pip install pytest" in config.shell_allowlist
