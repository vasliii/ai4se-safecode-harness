"""Guardrail event data model."""

from dataclasses import asdict, dataclass
from typing import ClassVar


@dataclass(slots=True)
class GuardrailEvent:
    """A deterministic guardrail block event."""

    ALLOWED_REASONS: ClassVar[set[str]] = {
        "dangerous_shell_command",
        "path_outside_workspace",
        "sensitive_file_access",
    }

    reason: str
    tool: str
    action_summary: str
    recoverable: bool
    suggestion: str | None = None
    blocked: bool = True

    def __post_init__(self) -> None:
        if self.reason not in self.ALLOWED_REASONS:
            raise ValueError(f"Unsupported guardrail reason: {self.reason}")
        if self.blocked is not True:
            raise ValueError("GuardrailEvent.blocked must be True")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
