"""Summarize raw pytest output into structured test feedback."""

from __future__ import annotations

import re

from safecode.models import FailedTest, Session, TestFeedback, ToolResult


class TestFeedbackSummarizer:
    """Parse pytest output and compare it with previous test feedback."""

    _TRACEBACK_LIMIT = 1100
    _SUMMARY_LIMIT = 2000

    def summarize(self, tool_result: ToolResult, session: Session) -> TestFeedback:
        """Build structured feedback from a run_tests ToolResult."""
        data = tool_result.data or {}
        stdout = str(data.get("stdout") or "")
        stderr = str(data.get("stderr") or "")
        exit_code = data.get("exit_code")

        if self._is_timeout(tool_result):
            feedback = TestFeedback(
                exit_code=-1 if not isinstance(exit_code, int) else exit_code,
                passed_count=0,
                failed_count=0,
                skipped_count=0,
                duration_ms=tool_result.duration_ms,
                status="timeout",
                progress_summary=self._truncate_text(tool_result.error or "Test run timed out."),
            )
            return self._compare_with_previous(feedback, session)

        feedback = self._parse_pytest_output(stdout, stderr)
        if isinstance(exit_code, int):
            feedback.exit_code = exit_code
            feedback.status = self._status_from_exit_code(exit_code)
            if feedback.status == "passed" and feedback.failed_count > 0:
                feedback.status = "failed"
            if feedback.status == "failed" and feedback.failed_count == 0 and not feedback.failed_tests:
                feedback.status = "error"

        return self._compare_with_previous(feedback, session)

    def _parse_pytest_output(self, stdout: str, stderr: str) -> TestFeedback:
        """Parse pytest stdout/stderr into TestFeedback without history comparison."""
        combined = "\n".join(part for part in [stdout, stderr] if part)
        counts = self._parse_counts(combined)
        duration_ms = self._parse_duration_ms(combined)

        if counts is None:
            return TestFeedback(
                exit_code=2,
                passed_count=0,
                failed_count=0,
                skipped_count=0,
                duration_ms=duration_ms,
                status="error",
                progress_summary=self._truncate_text(combined),
            )

        failed_tests = self._parse_failed_tests(combined)
        failed_count = counts.get("failed", 0)
        status = "failed" if failed_count > 0 else "passed"
        return TestFeedback(
            exit_code=1 if failed_count > 0 else 0,
            passed_count=counts.get("passed", 0),
            failed_count=failed_count,
            skipped_count=counts.get("skipped", 0),
            duration_ms=duration_ms,
            status=status,
            failed_tests=failed_tests,
        )

    def _compare_with_previous(self, current: TestFeedback, session: Session) -> TestFeedback:
        """Fill historical comparison fields from the most recent test feedback."""
        previous = self._last_feedback(session)
        if current.status in {"error", "timeout"}:
            current.previous_failed_count = previous.failed_count if previous else None
            current.fixed_tests = []
            current.new_failures = []
            current.unchanged_failures = []
            current.hint = self._hint(current, previous)
            return current

        current_failed_names = [failed.name for failed in current.failed_tests]
        previous_failed_names = [failed.name for failed in previous.failed_tests] if previous else []

        current.previous_failed_count = previous.failed_count if previous else None
        if previous is None:
            current.fixed_tests = []
            current.new_failures = []
            current.unchanged_failures = []
            if current.failed_count == 0:
                current.progress_summary = "All tests passed on first run."
            else:
                current.progress_summary = f"First run: {current.failed_count} failed."
            current.hint = self._hint(current, previous)
            return current

        current.fixed_tests = [name for name in previous_failed_names if name not in current_failed_names]
        current.new_failures = [name for name in current_failed_names if name not in previous_failed_names]
        current.unchanged_failures = [name for name in current_failed_names if name in previous_failed_names]
        current.progress_summary = (
            f"Previous run: {previous.failed_count} failed. "
            f"Current: {current.failed_count} failed. "
            f"Fixed: {len(current.fixed_tests)} tests."
        )
        current.hint = self._hint(current, previous)
        return current

    def _parse_counts(self, text: str) -> dict[str, int] | None:
        summary_lines = [line for line in text.splitlines() if " passed" in line or " failed" in line or " skipped" in line]
        for line in reversed(summary_lines):
            matches = re.findall(r"(\d+)\s+(passed|failed|skipped)\b", line)
            if matches:
                counts = {"passed": 0, "failed": 0, "skipped": 0}
                for value, label in matches:
                    counts[label] = int(value)
                return counts
        return None

    def _parse_duration_ms(self, text: str) -> int:
        match = re.search(r"\bin\s+([0-9]+(?:\.[0-9]+)?)s\b", text)
        if not match:
            return 0
        return int(float(match.group(1)) * 1000)

    def _parse_failed_tests(self, text: str) -> list[FailedTest]:
        names = re.findall(r"^FAILED\s+([^\s]+)", text, flags=re.MULTILINE)
        if not names:
            return []

        assertion = self._parse_assertion(text)
        file_path, line_number = self._parse_file_location(text)
        traceback = self._truncate_traceback(self._extract_traceback(text))
        failed_tests: list[FailedTest] = []
        for name in names:
            inferred_path = name.split("::", 1)[0] if "::" in name else file_path
            failed_tests.append(
                FailedTest(
                    name=name,
                    assertion=assertion,
                    traceback=traceback,
                    file_path=file_path or inferred_path,
                    line_number=line_number,
                )
            )
        return failed_tests

    def _parse_assertion(self, text: str) -> str | None:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("E") and "AssertionError" in stripped:
                return stripped.removeprefix("E").strip()
            if stripped.startswith("E") and "assert" in stripped:
                return stripped.removeprefix("E").strip()
        match = re.search(r"-\s+(AssertionError: .+|assert .+)$", text, flags=re.MULTILINE)
        return match.group(1).strip() if match else None

    def _parse_file_location(self, text: str) -> tuple[str | None, int | None]:
        match = re.search(r"^([^\s:]+\.py):(\d+):", text, flags=re.MULTILINE)
        if not match:
            return None, None
        return match.group(1), int(match.group(2))

    def _extract_traceback(self, text: str) -> str | None:
        if "FAILURES" not in text:
            return None
        section = text.split("FAILURES", 1)[1]
        section = section.split("short test summary info", 1)[0]
        return section.strip("=\n ") or None

    def _truncate_traceback(self, text: str | None) -> str | None:
        if text is None or len(text) <= self._TRACEBACK_LIMIT:
            return text
        return text[: self._TRACEBACK_LIMIT].rstrip() + "\n[truncated]"

    def _truncate_text(self, text: str) -> str:
        normalized = text.strip()
        if len(normalized) <= self._SUMMARY_LIMIT:
            return normalized
        return normalized[: self._SUMMARY_LIMIT].rstrip() + "\n[truncated]"

    def _last_feedback(self, session: Session) -> TestFeedback | None:
        for step in reversed(session.steps):
            if step.test_feedback is not None:
                return step.test_feedback
        return None

    def _hint(self, current: TestFeedback, previous: TestFeedback | None) -> str:
        if current.status == "passed" or current.failed_count == 0 and current.status == "passed":
            return "All tests pass. Consider calling finish."
        if previous is not None and current.failed_count < previous.failed_count:
            return "Good progress. Continue fixing remaining failures."
        if previous is not None and current.failed_count > previous.failed_count:
            return "Failures increased. Review recent changes."
        return "Same failures persist. Try a different approach."

    def _status_from_exit_code(self, exit_code: int) -> str:
        if exit_code == 0:
            return "passed"
        if exit_code == 1:
            return "failed"
        return "error"

    def _is_timeout(self, tool_result: ToolResult) -> bool:
        text = f"{tool_result.error or ''}"
        return "timeout" in text.lower() or "timed out" in text.lower()

