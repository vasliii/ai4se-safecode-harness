"""LLM context payload data model."""

from dataclasses import asdict, dataclass, field

from safecode.models.guardrail import GuardrailEvent
from safecode.models.test_feedback import TestFeedback
from safecode.models.tool_result import ToolResult


@dataclass(slots=True)
class ContextPayload:
    """Payload sent to an LLM backend for one agent step."""

    system_prompt: str
    task_description: str
    step_id: int
    blocked_count: int
    remaining_steps: int
    last_test_feedback: TestFeedback | None = None
    last_tool_result: ToolResult | None = None
    last_guardrail_event: GuardrailEvent | None = None
    recent_diffs: list[str] = field(default_factory=list)
    workspace_tree: str | None = None
    history_summary: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
