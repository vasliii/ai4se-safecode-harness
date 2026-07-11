"""Dispatch parsed actions to registered tools."""

from time import perf_counter

from safecode.models import ParsedAction, Session, ToolResult
from safecode.tools.base import Tool


class ToolDispatcher:
    """Route parsed actions to matching tools by name."""

    def __init__(self, tools: list[Tool]) -> None:
        self.registered_tools: dict[str, Tool] = {tool.name: tool for tool in tools}

    def dispatch(self, action: ParsedAction, session: Session) -> ToolResult:
        tool = self.registered_tools.get(action.tool)
        if tool is None:
            return ToolResult(
                tool=action.tool,
                success=False,
                error=f"Unknown tool: {action.tool}",
            )

        started_at = perf_counter()
        try:
            result = tool.execute(action.params, session)
        except Exception as exc:
            duration_ms = self._elapsed_ms(started_at)
            return ToolResult(
                tool=action.tool,
                success=False,
                error=str(exc),
                duration_ms=duration_ms,
            )

        result.duration_ms = self._elapsed_ms(started_at)
        return result

    def _elapsed_ms(self, started_at: float) -> int:
        return int((perf_counter() - started_at) * 1000)