"""Parsed LLM action data model."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ParsedAction:
    """A structured action parsed from an LLM response."""

    tool: str
    params: dict[str, Any] = field(default_factory=dict)
    thought_summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
