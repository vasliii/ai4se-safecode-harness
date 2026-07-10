"""Pytest feedback data models."""

from dataclasses import asdict, dataclass, field
from typing import ClassVar

__test__ = False


@dataclass(slots=True)
class FailedTest:
    """Details for one failed test case."""

    __test__: ClassVar[bool] = False

    name: str
    assertion: str | None = None
    traceback: str | None = None
    file_path: str | None = None
    line_number: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class TestFeedback:
    """Structured summary of a test run."""

    __test__: ClassVar[bool] = False

    exit_code: int
    passed_count: int
    failed_count: int
    skipped_count: int
    duration_ms: int
    status: str
    failed_tests: list[FailedTest] = field(default_factory=list)
    previous_failed_count: int | None = None
    fixed_tests: list[str] = field(default_factory=list)
    new_failures: list[str] = field(default_factory=list)
    unchanged_failures: list[str] = field(default_factory=list)
    progress_summary: str = ""
    hint: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
