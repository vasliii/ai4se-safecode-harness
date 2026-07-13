"""Runtime configuration data model."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class RuntimeConfig:
    """Configuration used while executing a SafeCode session."""

    base_url: str = "https://njusehub.info/v1"
    model: str = "qwen3.7-max"
    temperature: float = 0
    max_iterations: int = 10
    timeout_seconds: int = 300
    test_command: str = "pytest"
    context_budget_chars: int = 8000
    guardrail_threshold: int = 3
    shell_allowlist: list[str] = field(
        default_factory=lambda: [
            "git diff",
            "git status",
            "python -m py_compile",
            "pip install pytest",
            "python -m pip install pytest",
        ]
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
