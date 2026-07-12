"""Merge runtime configuration sources into RuntimeConfig."""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from safecode.models import RuntimeConfig


class ConfigurationManager:
    """Load runtime configuration from defaults, config.yaml, env, and CLI."""

    ENV_MAPPING = {
        "SAFECODE_MODEL": ("model", str),
        "SAFECODE_BASE_URL": ("base_url", str),
        "SAFECODE_TEMPERATURE": ("temperature", float),
        "SAFECODE_MAX_ITERATIONS": ("max_iterations", int),
        "SAFECODE_TIMEOUT_SECONDS": ("timeout_seconds", int),
        "SAFECODE_TEST_COMMAND": ("test_command", str),
        "SAFECODE_CONTEXT_BUDGET_CHARS": ("context_budget_chars", int),
        "SAFECODE_GUARDRAIL_THRESHOLD": ("guardrail_threshold", int),
        "SAFECODE_SHELL_ALLOWLIST": ("shell_allowlist", list),
    }
    NON_SENSITIVE_KEYS = set(RuntimeConfig.__dataclass_fields__.keys())

    def load(self, cli_overrides: dict[str, Any] | None = None) -> RuntimeConfig:
        """Load and merge runtime configuration sources."""
        config = self._merge(
            self._load_defaults(),
            self._load_config_yaml(),
            self._load_env_vars(),
            cli_overrides or {},
        )
        self._validate(config)
        return config

    def _load_defaults(self) -> RuntimeConfig:
        """Return built-in runtime defaults."""
        return RuntimeConfig()

    def _load_config_yaml(self) -> dict[str, Any]:
        """Load non-sensitive config.yaml values from the current directory."""
        path = Path("config.yaml")
        if not path.exists():
            return {}
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid config.yaml: {exc}") from exc
        except OSError as exc:
            raise ValueError(f"Unable to read config.yaml: {exc}") from exc
        if raw is None:
            return {}
        if not isinstance(raw, dict):
            raise ValueError("config.yaml must contain a mapping")
        return {key: value for key, value in raw.items() if key in self.NON_SENSITIVE_KEYS}

    def _load_env_vars(self) -> dict[str, Any]:
        """Load supported SAFECODE_* environment variables."""
        loaded: dict[str, Any] = {}
        for env_name, (field_name, converter) in self.ENV_MAPPING.items():
            if env_name not in os.environ:
                continue
            raw_value = os.environ[env_name]
            loaded[field_name] = self._convert_env_value(env_name, raw_value, converter)
        return loaded

    def _merge(self, *sources: RuntimeConfig | dict[str, Any]) -> RuntimeConfig:
        """Merge sources in increasing priority order."""
        merged: dict[str, Any] = {}
        for source in sources:
            if isinstance(source, RuntimeConfig):
                values = asdict(source)
            else:
                values = dict(source)
            for key, value in values.items():
                if key in self.NON_SENSITIVE_KEYS and value is not None:
                    merged[key] = value
        return RuntimeConfig(**merged)

    def _validate(self, config: RuntimeConfig) -> None:
        """Validate RuntimeConfig field ranges and types."""
        if config.max_iterations <= 0:
            raise ValueError("max_iterations must be > 0")
        if not 0 <= config.temperature <= 2:
            raise ValueError("temperature must be between 0 and 2")
        if config.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        if config.context_budget_chars <= 0:
            raise ValueError("context_budget_chars must be > 0")
        if config.guardrail_threshold < 1:
            raise ValueError("guardrail_threshold must be >= 1")
        if not isinstance(config.shell_allowlist, list) or not all(
            isinstance(item, str) for item in config.shell_allowlist
        ):
            raise ValueError("shell_allowlist must be a list of strings")

    def _convert_env_value(self, env_name: str, raw_value: str, converter: type) -> Any:
        if converter is str:
            return raw_value
        if converter is int:
            try:
                return int(raw_value)
            except ValueError as exc:
                raise ValueError(f"{env_name} must be an integer") from exc
        if converter is float:
            try:
                return float(raw_value)
            except ValueError as exc:
                raise ValueError(f"{env_name} must be a number") from exc
        if converter is list:
            return [item.strip() for item in raw_value.split(",") if item.strip()]
        return raw_value
