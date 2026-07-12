"""Agent loop skeleton for SafeCode Harness."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from safecode.core.action_parser import ActionParser
from safecode.core.exceptions import InvalidActionError
from safecode.core.stop_controller import StopController
from safecode.guardrail import Guardrail
from safecode.llm import LLMBackend, LLMError
from safecode.models import (
    ContextPayload,
    GuardrailEvent,
    ParsedAction,
    RuntimeConfig,
    Session,
    SessionStatus,
    SessionStep,
    TestFeedback,
    ToolResult,
)


class ContextBuilderLike(Protocol):
    def build(self, session: Session, config: RuntimeConfig) -> ContextPayload:
        """Build context for the next LLM call."""


class GuardrailLike(Protocol):
    def check(self, action: ParsedAction, session: Session) -> GuardrailEvent | None:
        """Return a guardrail event when an action is blocked."""


class ToolDispatcherLike(Protocol):
    def dispatch(self, action: ParsedAction, session: Session) -> ToolResult:
        """Execute or simulate execution of a parsed action."""


class FeedbackSummarizerLike(Protocol):
    def summarize(self, tool_result: ToolResult, session: Session) -> TestFeedback:
        """Summarize a run_tests tool result."""


class _StubContextBuilder:
    def build(self, session: Session, config: RuntimeConfig) -> ContextPayload:
        step_id = len(session.steps)
        return ContextPayload(
            system_prompt="SafeCode Harness agent loop skeleton.",
            task_description=session.task_config.description,
            step_id=step_id,
            blocked_count=session.blocked_count,
            remaining_steps=max(config.max_iterations - step_id, 0),
            last_test_feedback=_last_test_feedback(session),
            last_tool_result=_last_tool_result(session),
            last_guardrail_event=_last_guardrail_event(session),
        )


class _StubToolDispatcher:
    def dispatch(self, action: ParsedAction, session: Session) -> ToolResult:
        return ToolResult(tool=action.tool, success=True, data={})


class _StubFeedbackSummarizer:
    def summarize(self, tool_result: ToolResult, session: Session) -> TestFeedback:
        data = tool_result.data or {}
        exit_code = data.get("exit_code", 1)
        passed = exit_code == 0
        return TestFeedback(
            exit_code=exit_code,
            passed_count=1 if passed else 0,
            failed_count=0 if passed else 1,
            skipped_count=0,
            duration_ms=tool_result.duration_ms,
            status="passed" if passed else "failed",
        )


class AgentLoop:
    """Coordinate the current pipeline components for a SafeCode session."""

    def __init__(
        self,
        *,
        context_builder: ContextBuilderLike | None = None,
        action_parser: ActionParser | None = None,
        guardrail: GuardrailLike | None = None,
        tool_dispatcher: ToolDispatcherLike | None = None,
        feedback_summarizer: FeedbackSummarizerLike | None = None,
        stop_controller: StopController | None = None,
    ) -> None:
        self.context_builder = context_builder or _StubContextBuilder()
        self.action_parser = action_parser or ActionParser()
        self.guardrail = guardrail
        self.tool_dispatcher = tool_dispatcher or _StubToolDispatcher()
        self.feedback_summarizer = feedback_summarizer or _StubFeedbackSummarizer()
        self.stop_controller = stop_controller or StopController()

    def run(self, session: Session, llm_backend: LLMBackend, config: RuntimeConfig) -> Session:
        while True:
            should_stop, status = self.stop_controller.should_stop(session, config)
            if should_stop:
                self._finish(session, status)
                return session

            context = self.context_builder.build(session, config)

            try:
                llm_response = llm_backend.query(context)
            except LLMError as exc:
                self._append_error_step(session, context, "", "llm", str(exc))
                continue

            try:
                action = self.action_parser.parse(llm_response)
            except InvalidActionError as exc:
                session.invalid_action_count += 1
                self._append_error_step(session, context, llm_response, "action_parser", exc.reason)
                continue

            guardrail = self.guardrail or Guardrail(config.shell_allowlist)
            guardrail_event = guardrail.check(action, session)
            if guardrail_event is not None:
                session.blocked_count += 1
                session.steps.append(
                    SessionStep(
                        step_id=len(session.steps),
                        llm_request=context,
                        llm_response=llm_response,
                        parsed_action=action,
                        guardrail_result=guardrail_event,
                    )
                )
                continue

            tool_result = self.tool_dispatcher.dispatch(action, session)
            test_feedback = None
            if action.tool == "run_tests":
                test_feedback = self.feedback_summarizer.summarize(tool_result, session)

            session.steps.append(
                SessionStep(
                    step_id=len(session.steps),
                    llm_request=context,
                    llm_response=llm_response,
                    parsed_action=action,
                    tool_result=tool_result,
                    test_feedback=test_feedback,
                )
            )

    def _append_error_step(
        self,
        session: Session,
        context: ContextPayload,
        llm_response: str,
        tool: str,
        error: str,
    ) -> None:
        session.steps.append(
            SessionStep(
                step_id=len(session.steps),
                llm_request=context,
                llm_response=llm_response,
                tool_result=ToolResult(tool=tool, success=False, error=error),
            )
        )

    def _finish(self, session: Session, status: SessionStatus) -> None:
        session.final_status = status
        if status is not SessionStatus.RUNNING:
            session.end_time = datetime.now()


def _last_test_feedback(session: Session) -> TestFeedback | None:
    for step in reversed(session.steps):
        if step.test_feedback is not None:
            return step.test_feedback
    return None


def _last_tool_result(session: Session) -> ToolResult | None:
    for step in reversed(session.steps):
        if step.tool_result is not None:
            return step.tool_result
    return None


def _last_guardrail_event(session: Session) -> GuardrailEvent | None:
    for step in reversed(session.steps):
        if step.guardrail_result is not None:
            return step.guardrail_result
    return None
