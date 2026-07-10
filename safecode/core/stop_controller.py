"""Stop-condition evaluation for SafeCode sessions."""

from datetime import datetime

from safecode.models import RuntimeConfig, Session, SessionStatus, SessionStep


class StopController:
    """Evaluate whether an agent session should stop."""

    def should_stop(self, session: Session, config: RuntimeConfig) -> tuple[bool, SessionStatus]:
        if self._last_run_tests_passed(session):
            return True, SessionStatus.SUCCESS

        if len(session.steps) >= config.max_iterations:
            return True, SessionStatus.MAX_ITERATIONS_REACHED

        if session.blocked_count >= config.guardrail_threshold:
            return True, SessionStatus.TERMINATED_BY_GUARDRAIL

        if (datetime.now() - session.start_time).total_seconds() >= config.timeout_seconds:
            return True, SessionStatus.TIMEOUT

        last_step = self._last_step(session)
        if self._is_finish_step(last_step):
            if self._has_passing_test_feedback(session):
                return True, SessionStatus.SUCCESS
            return True, SessionStatus.FINISHED_WITHOUT_PASSING_TESTS

        if session.invalid_action_count >= 3:
            return True, SessionStatus.INVALID_ACTION_LIMIT_REACHED

        return False, SessionStatus.RUNNING

    def _last_run_tests_passed(self, session: Session) -> bool:
        last_step = self._last_step(session)
        if last_step is None or last_step.parsed_action is None:
            return False
        if last_step.parsed_action.tool != "run_tests" or last_step.test_feedback is None:
            return False
        return last_step.test_feedback.exit_code == 0 and last_step.test_feedback.status == "passed"

    def _has_passing_test_feedback(self, session: Session) -> bool:
        return any(
            step.test_feedback is not None
            and step.test_feedback.exit_code == 0
            and step.test_feedback.status == "passed"
            for step in session.steps
        )

    def _is_finish_step(self, step: SessionStep | None) -> bool:
        return step is not None and step.parsed_action is not None and step.parsed_action.tool == "finish"

    def _last_step(self, session: Session) -> SessionStep | None:
        if not session.steps:
            return None
        return session.steps[-1]