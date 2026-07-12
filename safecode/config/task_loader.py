"""Load and validate task.yaml files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from safecode.core.action_parser import TOOL_SCHEMAS
from safecode.models import TaskConfig


class ValidationError(Exception):
    """Raised when a task configuration file is invalid."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class TaskConfigLoader:
    """Parse task.yaml files into validated TaskConfig objects."""

    REQUIRED_FIELDS = ["id", "title", "task_type", "workspace_template", "test_command"]
    VALID_TASK_TYPES = {"complete_function", "fix_bug", "add_feature"}

    def load(self, path: Path) -> TaskConfig:
        """Load and validate a task.yaml file."""
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ValidationError([f"Invalid YAML: {exc}"]) from exc
        except OSError as exc:
            raise ValidationError([f"Unable to read task config: {exc}"]) from exc

        if not isinstance(raw, dict):
            raise ValidationError(["Task config YAML must contain a mapping"])

        errors = self._validate(raw)
        if errors:
            raise ValidationError(errors)

        data = dict(raw)
        data.setdefault("description", "")
        return TaskConfig(**data)

    def _validate(self, config: dict[str, Any]) -> list[str]:
        """Return validation errors for a raw task config mapping."""
        errors: list[str] = []

        for field in self.REQUIRED_FIELDS:
            if field not in config or config[field] is None:
                errors.append(f"Missing required field: {field}")

        task_type = config.get("task_type")
        if task_type is not None and task_type not in self.VALID_TASK_TYPES:
            errors.append(f"Invalid task_type: {task_type}")

        allowed_tools = config.get("allowed_tools", [])
        if allowed_tools is not None:
            if not isinstance(allowed_tools, list):
                errors.append("allowed_tools must be a list")
            else:
                for tool in allowed_tools:
                    if tool not in TOOL_SCHEMAS:
                        errors.append(f"Unknown allowed tool: {tool}")

        self._validate_positive_int(config, "max_iterations", errors)
        self._validate_positive_int(config, "timeout_seconds", errors)
        return errors

    def _validate_positive_int(self, config: dict[str, Any], field: str, errors: list[str]) -> None:
        if field not in config or config[field] is None:
            return
        value = config[field]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            errors.append(f"{field} must be a positive integer")
