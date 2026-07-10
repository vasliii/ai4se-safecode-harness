"""Tool execution result data model."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ToolResult:
    """Result returned by a tool execution."""

    tool: str
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
