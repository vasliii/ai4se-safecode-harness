"""Task configuration data model."""

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class TaskConfig:
    """Declarative configuration for one coding task."""

    id: str
    title: str
    task_type: str
    description: str
    workspace_template: str
    test_command: str
    max_iterations: int | None = None
    timeout_seconds: int | None = None
    allowed_files: list[str] = field(default_factory=list)
    read_only_files: list[str] = field(default_factory=list)
    protected_files: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    forbidden_actions: list[str] = field(default_factory=list)
    hints: str | None = None
    success_criteria: list[str] = field(default_factory=list)
    expected_final_files: list[str] = field(default_factory=list)
    mock_scenario: str | None = None
    demo_visible: bool = False
    demo_order: int | None = None
    expected_trace_events: list[str] = field(default_factory=list)

    @classmethod
    def from_yaml(cls, path: Path) -> "TaskConfig":
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("Task config YAML must contain a mapping")

        required_fields = [
            "id",
            "title",
            "task_type",
            "workspace_template",
            "test_command",
        ]
        missing = [field_name for field_name in required_fields if field_name not in raw]
        if missing:
            raise ValueError(f"Missing required task config fields: {', '.join(missing)}")

        raw.setdefault("description", "")
        return cls(**raw)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
