"""Core exceptions for SafeCode Harness."""


class InvalidActionError(Exception):
    """Raised when an LLM response cannot be parsed into a valid action."""

    def __init__(self, reason: str, message: str | None = None) -> None:
        self.reason = reason
        super().__init__(message or reason)