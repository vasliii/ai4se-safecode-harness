"""Build LLM context payloads from session state."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from safecode.models import (
    ContextPayload,
    FailedTest,
    GuardrailEvent,
    RuntimeConfig,
    Session,
    TestFeedback,
    ToolResult,
)


class ContextBuilder:
    """Construct a bounded ContextPayload for the next LLM call."""

    _IGNORED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}
    _SECRET_PATTERNS = [
        re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
        re.compile(r"(?i)(api[_-]?key|token|secret)\s*[=:]\s*[^\s,'\"}]+"),
    ]
    _LONG_TEXT_LIMIT = 1200

    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config

    def build(self, session: Session) -> ContextPayload:
        """Build a ContextPayload from the current session."""
        step_id = len(session.steps)
        context = ContextPayload(
            system_prompt=self._build_system_prompt(),
            task_description=session.task_config.description,
            step_id=step_id,
            blocked_count=session.blocked_count,
            remaining_steps=max(self.config.max_iterations - step_id, 0),
            last_test_feedback=self._sanitize_test_feedback(self._last_test_feedback(session)),
            last_tool_result=self._sanitize_tool_result(self._last_tool_result(session)),
            last_guardrail_event=self._sanitize_guardrail_event(self._last_guardrail_event(session)),
            recent_diffs=[],
            workspace_tree=self._build_workspace_tree(session),
            history_summary=self._summarize_history(session),
        )
        self._apply_budget(context)
        return context

    def _build_system_prompt(self) -> str:
        """Return stable system instructions and safety rules."""
        return (
            "SafeCode Harness safety rules:\n"
            "- You must only output one JSON object.\n"
            "- No Markdown. No code blocks. No explanation text. No chain-of-thought. No multiple JSON objects.\n"
            "- The JSON format must be: {\"tool\": \"<tool_name>\", \"params\": {}, \"thought_summary\": \"brief summary\"}.\n"
            "- tool must be one of: list_files, read_file, search_content, write_file, edit_file, run_tests, run_shell, finish.\n"
            "- Use the available tool schema and do not include prose outside the JSON action.\n"
            "- Treat the workspace root as the only allowed file boundary.\n"
            "- Do not read sensitive files such as .env, .env.*, *.key, *.pem, secrets.json, id_rsa, or .git/config.\n"
            "- Do not execute dangerous shell commands. Use only configured low-risk commands.\n"
            "- Prefer running tests after code changes and use structured feedback to decide the next action.\n"
            "Examples:\n"
            "{\"tool\":\"run_tests\",\"params\":{},\"thought_summary\":\"Run tests first.\"}\n"
            "{\"tool\":\"read_file\",\"params\":{\"path\":\"src/calculator.py\"},\"thought_summary\":\"Inspect the target file.\"}\n"
            "{\"tool\":\"edit_file\",\"params\":{\"path\":\"src/calculator.py\",\"old_text\":\"return a - b\",\"new_text\":\"return a + b\"},\"thought_summary\":\"Fix the add implementation.\"}\n"
            "{\"tool\":\"finish\",\"params\":{\"summary\":\"All tests pass.\"},\"thought_summary\":\"Finish after successful tests.\"}"
        )

    def _summarize_history(self, session: Session) -> str:
        """Create a deterministic summary of prior session steps."""
        if not session.steps:
            return "No previous steps."

        lines: list[str] = []
        for step in session.steps:
            parts = [f"step {step.step_id}"]
            if step.parsed_action is not None:
                parts.append(f"action={step.parsed_action.tool}")
            if step.tool_result is not None:
                parts.append(f"tool={step.tool_result.tool} success={step.tool_result.success}")
            if step.guardrail_result is not None:
                parts.append(f"guardrail={step.guardrail_result.reason}")
            if step.test_feedback is not None:
                parts.append(
                    f"tests={step.test_feedback.status} failed={step.test_feedback.failed_count}"
                )
            lines.append("; ".join(parts))
        return self._redact("\n".join(lines))

    def _build_workspace_tree(self, session: Session) -> str:
        """Return a compact file tree without reading file contents."""
        root = session.workspace_root
        if not root.exists():
            return ""

        paths: list[str] = []
        for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
            relative_parts = path.relative_to(root).parts
            if any(part in self._IGNORED_DIRS for part in relative_parts):
                continue
            relative = path.relative_to(root).as_posix()
            if path.is_dir():
                paths.append(f"{relative}/")
            else:
                paths.append(relative)
        return self._redact("\n".join(paths))

    def _last_test_feedback(self, session: Session) -> TestFeedback | None:
        for step in reversed(session.steps):
            if step.test_feedback is not None:
                return step.test_feedback
        return None

    def _last_tool_result(self, session: Session) -> ToolResult | None:
        for step in reversed(session.steps):
            if step.tool_result is not None:
                return step.tool_result
        return None

    def _last_guardrail_event(self, session: Session) -> GuardrailEvent | None:
        for step in reversed(session.steps):
            if step.guardrail_result is not None:
                return step.guardrail_result
        return None

    def _sanitize_tool_result(self, result: ToolResult | None) -> ToolResult | None:
        if result is None:
            return None
        return ToolResult(
            tool=result.tool,
            success=result.success,
            data=self._sanitize_value(result.data),
            error=self._sanitize_value(result.error),
            duration_ms=result.duration_ms,
        )

    def _sanitize_test_feedback(self, feedback: TestFeedback | None) -> TestFeedback | None:
        if feedback is None:
            return None
        failed_tests = [
            FailedTest(
                name=self._redact(failed.name),
                assertion=self._sanitize_value(failed.assertion),
                traceback=self._sanitize_value(failed.traceback),
                file_path=self._sanitize_value(failed.file_path),
                line_number=failed.line_number,
            )
            for failed in feedback.failed_tests
        ]
        return TestFeedback(
            exit_code=feedback.exit_code,
            passed_count=feedback.passed_count,
            failed_count=feedback.failed_count,
            skipped_count=feedback.skipped_count,
            duration_ms=feedback.duration_ms,
            status=feedback.status,
            failed_tests=failed_tests,
            previous_failed_count=feedback.previous_failed_count,
            fixed_tests=[self._redact(name) for name in feedback.fixed_tests],
            new_failures=[self._redact(name) for name in feedback.new_failures],
            unchanged_failures=[self._redact(name) for name in feedback.unchanged_failures],
            progress_summary=self._redact(feedback.progress_summary),
            hint=self._sanitize_value(feedback.hint),
        )

    def _sanitize_guardrail_event(self, event: GuardrailEvent | None) -> GuardrailEvent | None:
        if event is None:
            return None
        return replace(
            event,
            action_summary=self._redact(event.action_summary),
            suggestion=self._sanitize_value(event.suggestion),
        )

    def _sanitize_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._truncate(self._redact(value), self._LONG_TEXT_LIMIT)
        if isinstance(value, dict):
            return {self._redact(str(key)): self._sanitize_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._sanitize_value(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._sanitize_value(item) for item in value)
        return value

    def _redact(self, text: str | None) -> str | None:
        if text is None:
            return None
        redacted = text
        for pattern in self._SECRET_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted

    def _truncate(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "\n[truncated]"

    def _apply_budget(self, context: ContextPayload) -> None:
        budget = self.config.context_budget_chars
        if budget <= 0:
            return

        if self._payload_size(context) <= budget:
            return

        context.history_summary = self._fit_optional_text(context.history_summary, 600)
        if self._payload_size(context) <= budget:
            return

        context.history_summary = None
        if self._payload_size(context) <= budget:
            return

        context.workspace_tree = self._fit_optional_text(context.workspace_tree, 600)
        if self._payload_size(context) <= budget:
            return

        context.workspace_tree = None

    def _fit_optional_text(self, value: str | None, limit: int) -> str | None:
        if value is None:
            return None
        return self._truncate(value, min(limit, max(self.config.context_budget_chars // 2, 80)))

    def _payload_size(self, context: ContextPayload) -> int:
        return len(str(context.to_dict()))
