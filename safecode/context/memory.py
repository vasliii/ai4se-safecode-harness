"""Persist and load compact session trace summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from safecode.models import Session, SessionStatus, SessionStep, TestFeedback


class MemoryManager:
    """Save and load session_trace.json files for cross-session memory."""

    def save_trace(self, session: Session, output_dir: Path) -> Path:
        """Write a compact session trace under output_dir/.safecode/."""
        trace_dir = output_dir / ".safecode"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = trace_dir / "session_trace.json"
        trace = self._build_trace(session)
        try:
            trace_path.write_text(json.dumps(trace, indent=2, sort_keys=True), encoding="utf-8")
        except (TypeError, OSError) as exc:
            raise RuntimeError(f"Failed to write session trace: {exc}") from exc
        return trace_path

    def load_latest_trace(self, workspace_dir: Path) -> dict[str, Any] | None:
        """Load workspace_dir/.safecode/session_trace.json if it exists."""
        trace_path = workspace_dir / ".safecode" / "session_trace.json"
        if not trace_path.exists():
            return None
        try:
            raw = trace_path.read_text(encoding="utf-8")
            loaded = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Failed to load session trace: {exc}") from exc
        if not isinstance(loaded, dict):
            raise RuntimeError("Session trace must contain a JSON object")
        return loaded

    def _build_trace(self, session: Session) -> dict[str, Any]:
        """Build a JSON-serializable summary without full LLM history."""
        return {
            "session_id": session.session_id,
            "final_status": self._status_value(session.final_status),
            "llm_backend": session.llm_backend,
            "start_time": self._format_time(session.start_time),
            "end_time": self._format_time(session.end_time),
            "total_steps": len(session.steps),
            "blocked_count": session.blocked_count,
            "invalid_action_count": session.invalid_action_count,
            "test_summary": self._build_test_summary(session),
            "steps_summary": [self._summarize_step(step) for step in session.steps],
            "guardrail_events": [
                {
                    "step_id": step.step_id,
                    "reason": step.guardrail_result.reason,
                    "action_summary": step.guardrail_result.action_summary,
                }
                for step in session.steps
                if step.guardrail_result is not None
            ],
        }

    def _build_test_summary(self, session: Session) -> dict[str, Any]:
        feedback = self._last_test_feedback(session)
        if feedback is None:
            return {"final_passed": 0, "final_failed": 0, "final_status": "unknown"}
        return {
            "final_passed": feedback.passed_count,
            "final_failed": feedback.failed_count,
            "final_status": feedback.status,
        }

    def _summarize_step(self, step: SessionStep) -> dict[str, Any]:
        tool = self._step_tool(step)
        success = self._step_success(step)
        return {
            "step_id": step.step_id,
            "tool": tool,
            "success": success,
            "summary": self._step_summary(step),
        }

    def _step_tool(self, step: SessionStep) -> str | None:
        if step.tool_result is not None:
            return step.tool_result.tool
        if step.guardrail_result is not None:
            return step.guardrail_result.tool
        if step.parsed_action is not None:
            return step.parsed_action.tool
        return None

    def _step_success(self, step: SessionStep) -> bool | None:
        if step.tool_result is not None:
            return step.tool_result.success
        if step.guardrail_result is not None:
            return False
        return None

    def _step_summary(self, step: SessionStep) -> str:
        if step.test_feedback is not None:
            feedback = step.test_feedback
            return (
                f"tests={feedback.status} failed={feedback.failed_count} "
                f"passed={feedback.passed_count}"
            )
        if step.guardrail_result is not None:
            return f"guardrail={step.guardrail_result.reason}"
        if step.tool_result is not None:
            if step.tool_result.error:
                return f"tool_error={step.tool_result.error}"
            return "tool_executed"
        if step.parsed_action is not None:
            return f"action={step.parsed_action.tool}"
        return "step_recorded"

    def _last_test_feedback(self, session: Session) -> TestFeedback | None:
        for step in reversed(session.steps):
            if step.test_feedback is not None:
                return step.test_feedback
        return None

    def _status_value(self, status: SessionStatus | str) -> str:
        return status.value if isinstance(status, SessionStatus) else str(status)

    def _format_time(self, value: Any) -> str | None:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)
