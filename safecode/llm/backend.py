"""Abstract LLM backend contract."""

from abc import ABC, abstractmethod

from safecode.models import ContextPayload


class LLMError(Exception):
    """Raised when an LLM backend call fails."""


class LLMTimeoutError(LLMError):
    """Raised when an LLM backend call times out."""


class LLMBackend(ABC):
    """Base interface shared by all LLM backends."""

    @abstractmethod
    def query(self, context: ContextPayload) -> str:
        """Return the raw LLM response for the supplied context."""
        raise NotImplementedError