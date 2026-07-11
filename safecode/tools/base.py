"""Base class for SafeCode tools."""

from abc import ABC, abstractmethod

from safecode.models import Session, ToolResult


class Tool(ABC):
    """Abstract interface implemented by all executable tools."""

    name: str

    @abstractmethod
    def execute(self, params: dict, session: Session) -> ToolResult:
        """Execute the tool with parsed action parameters."""
        raise NotImplementedError

    @abstractmethod
    def validate_params(self, params: dict) -> None:
        """Validate tool parameters, raising ValueError when invalid."""
        raise NotImplementedError