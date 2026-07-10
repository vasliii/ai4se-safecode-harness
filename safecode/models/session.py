"""Session data models."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from safecode.models.action import ParsedAction
from safecode.models.context import ContextPayload
from safecode.models.guardrail import GuardrailEvent
from safecode.models.task_config import TaskConfig
from safecode.models.test_feedback import TestFeedback
from safecode.models.tool_result import ToolResult


class SessionStatus(str, Enum):
    """Possible terminal and active session states."""

    RUNNING = "running"
    SUCCESS = "success"
    MAX_ITERATIONS_REACHED = "max_iterations_reached"
    TERMINATED_BY_GUARDRAIL = "terminated_by_guardrail"
    TIMEOUT = "timeout"
    FINISHED_WITHOUT_PASSING_TESTS = "finished_without_passing_tests"
    INVALID_ACTION_LIMIT_REACHED = "invalid_action_limit_reached"


@dataclass(frozen=True, slots=True)
class SessionStep:
    """Append-only record for one agent loop step."""

    step_id: int
    llm_request: ContextPayload
    llm_response: str
    parsed_action: ParsedAction | None = None
    guardrail_result: GuardrailEvent | None = None
    tool_result: ToolResult | None = None
    test_feedback: TestFeedback | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Session:
    """State for one SafeCode task execution session."""

    session_id: str
    task_config: TaskConfig
    workspace_root: Path
    llm_backend: str
    steps: list[SessionStep] = field(default_factory=list)
    blocked_count: int = 0
    invalid_action_count: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None
    final_status: SessionStatus = SessionStatus.RUNNING

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["workspace_root"] = str(self.workspace_root)
        data["final_status"] = self.final_status.value
        return data
