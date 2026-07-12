from __future__ import annotations

from pathlib import Path

import pytest

from safecode.config import ConfigurationManager
from safecode.models import RuntimeConfig


def test_load_uses_defaults_when_no_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    config = ConfigurationManager().load()

    assert isinstance(config, RuntimeConfig)
    assert config.base_url == "https://njusehub.info/v1"
    assert config.model == "qwen3.7-max"
    assert config.temperature == 0
    assert config.max_iterations == 10
    assert config.timeout_seconds == 300
    assert config.test_command == "pytest"
    assert config.context_budget_chars == 8000
    assert config.guardrail_threshold == 3
    assert config.shell_allowlist == ["git diff", "git status", "python -m py_compile"]


def test_config_yaml_overrides_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text(
        """
base_url: https://example.test/v1
model: local-model
temperature: 0.5
max_iterations: 4
timeout_seconds: 30
test_command: pytest tests/unit
context_budget_chars: 1200
guardrail_threshold: 2
shell_allowlist:
  - git status
""".strip(),
        encoding="utf-8",
    )

    config = ConfigurationManager().load()

    assert config.base_url == "https://example.test/v1"
    assert config.model == "local-model"
    assert config.temperature == 0.5
    assert config.max_iterations == 4
    assert config.timeout_seconds == 30
    assert config.test_command == "pytest tests/unit"
    assert config.context_budget_chars == 1200
    assert config.guardrail_threshold == 2
    assert config.shell_allowlist == ["git status"]


def test_config_yaml_ignores_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text(
        """
model: configured-model
api_key: should-not-load
""".strip(),
        encoding="utf-8",
    )

    config = ConfigurationManager().load()

    assert config.model == "configured-model"
    assert not hasattr(config, "api_key")


def test_environment_overrides_config_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text(
        """
model: yaml-model
max_iterations: 4
temperature: 0.25
shell_allowlist:
  - git status
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("SAFECODE_MODEL", "env-model")
    monkeypatch.setenv("SAFECODE_MAX_ITERATIONS", "8")
    monkeypatch.setenv("SAFECODE_TEMPERATURE", "1.25")
    monkeypatch.setenv("SAFECODE_SHELL_ALLOWLIST", "git diff,python -m py_compile")

    config = ConfigurationManager().load()

    assert config.model == "env-model"
    assert config.max_iterations == 8
    assert config.temperature == 1.25
    assert config.shell_allowlist == ["git diff", "python -m py_compile"]


def test_cli_overrides_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SAFECODE_MODEL", "env-model")
    monkeypatch.setenv("SAFECODE_MAX_ITERATIONS", "8")

    config = ConfigurationManager().load({"model": "cli-model", "max_iterations": 2})

    assert config.model == "cli-model"
    assert config.max_iterations == 2


def test_environment_numeric_type_conversion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SAFECODE_TEMPERATURE", "0.75")
    monkeypatch.setenv("SAFECODE_MAX_ITERATIONS", "6")
    monkeypatch.setenv("SAFECODE_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("SAFECODE_CONTEXT_BUDGET_CHARS", "4096")
    monkeypatch.setenv("SAFECODE_GUARDRAIL_THRESHOLD", "4")
    monkeypatch.setenv("SAFECODE_BASE_URL", "https://env.example/v1")
    monkeypatch.setenv("SAFECODE_TEST_COMMAND", "pytest -q")

    config = ConfigurationManager().load()

    assert config.temperature == 0.75
    assert config.max_iterations == 6
    assert config.timeout_seconds == 45
    assert config.context_budget_chars == 4096
    assert config.guardrail_threshold == 4
    assert config.base_url == "https://env.example/v1"
    assert config.test_command == "pytest -q"


def test_missing_config_yaml_is_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    config = ConfigurationManager().load()

    assert config.model == "qwen3.7-max"


def test_max_iterations_zero_raises_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="max_iterations must be > 0"):
        ConfigurationManager().load({"max_iterations": 0})


def test_temperature_above_range_raises_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="temperature must be between 0 and 2"):
        ConfigurationManager().load({"temperature": 3})


def test_shell_allowlist_invalid_type_raises_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    with pytest.raises(ValueError, match="shell_allowlist must be a list of strings"):
        ConfigurationManager().load({"shell_allowlist": "git status"})


def test_shell_allowlist_list_from_cli_replaces_previous_sources(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SAFECODE_SHELL_ALLOWLIST", "git status")

    config = ConfigurationManager().load({"shell_allowlist": ["python -m py_compile"]})

    assert config.shell_allowlist == ["python -m py_compile"]
