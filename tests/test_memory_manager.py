from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from safecode.context import MemoryManager
from safecode.models import (
    ContextPayload,
    FailedTest,
    GuardrailEvent,
    ParsedAction,
    Session,
    SessionStatus,
    SessionStep,
    TaskConfig,
    TestFeedback,
    ToolResult,
)


def make_session(workspace_root: Path) -> Session:
    session = Session(
        session_id="session-memory",
        task_config=TaskConfig(
            id="task-memory",
            title="Memory Task",
            task_type="fix_bug",
            description="Persist trace",
            workspace_template="template",
            test_command="pytest",
        ),
        workspace_root=workspace_root,
        llm_backend="mock",
        blocked_count=1,
        invalid_action_count=2,
        final_status=SessionStatus.SUCCESS,
    )
    session.start_time = datetime(2026, 7, 12, 10, 0, 0)
    session.end_time = datetime(2026, 7, 12, 10, 1, 0)
    return session


def request(step_id: int) -> ContextPayload:
    return ContextPayload(
        system_prompt="system prompt that must not be persisted",
        task_description="task context that must not be persisted",
        step_id=step_id,
        blocked_count=0,
        remaining_steps=10,
        history_summary="full context history must not be persisted",
    )


def add_sample_steps(session: Session) -> None:
    session.steps.append(
        SessionStep(
            step_id=0,
            llm_request=request(0),
            llm_response="RAW LLM RESPONSE THAT MUST NOT BE SAVED",
            parsed_action=ParsedAction("run_tests", {}),
            tool_result=ToolResult("run_tests", True, {"exit_code": 1, "stdout": "full stdout"}),
            test_feedback=TestFeedback(
                exit_code=1,
                passed_count=1,
                failed_count=2,
                skipped_count=0,
                duration_ms=100,
                status="failed",
                failed_tests=[FailedTest("tests/test_calc.py::test_add")],
                progress_summary="2 failed",
            ),
        )
    )
    session.steps.append(
        SessionStep(
            step_id=1,
            llm_request=request(1),
            llm_response="ANOTHER RAW LLM RESPONSE",
            parsed_action=ParsedAction("read_file", {"path": ".env"}),
            guardrail_result=GuardrailEvent(
                reason="sensitive_file_access",
                tool="read_file",
                action_summary="attempted to read .env",
                recoverable=True,
            ),
        )
    )
    session.steps.append(
        SessionStep(
            step_id=2,
            llm_request=request(2),
            llm_response="FINAL RAW RESPONSE",
            parsed_action=ParsedAction("run_tests", {}),
            tool_result=ToolResult("run_tests", True, {"exit_code": 0, "stdout": "all passed"}),
            test_feedback=TestFeedback(
                exit_code=0,
                passed_count=3,
                failed_count=0,
                skipped_count=0,
                duration_ms=80,
                status="passed",
                progress_summary="All tests pass.",
            ),
        )
    )


def read_trace(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_save_trace_creates_safecode_file_and_returns_path(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    add_sample_steps(session)

    trace_path = MemoryManager().save_trace(session, tmp_path)

    assert trace_path == tmp_path / ".safecode" / "session_trace.json"
    assert trace_path.exists()


def test_saved_trace_contains_required_top_level_fields(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    add_sample_steps(session)

    trace = read_trace(MemoryManager().save_trace(session, tmp_path))

    assert trace["session_id"] == "session-memory"
    assert trace["final_status"] == "success"
    assert trace["llm_backend"] == "mock"
    assert trace["start_time"] == "2026-07-12T10:00:00"
    assert trace["end_time"] == "2026-07-12T10:01:00"
    assert trace["total_steps"] == 3
    assert trace["blocked_count"] == 1
    assert trace["invalid_action_count"] == 2


def test_steps_summary_guardrail_events_and_test_summary_are_built(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    add_sample_steps(session)

    trace = read_trace(MemoryManager().save_trace(session, tmp_path))

    assert len(trace["steps_summary"]) == 3
    assert trace["steps_summary"][0] == {
        "step_id": 0,
        "tool": "run_tests",
        "success": True,
        "summary": "tests=failed failed=2 passed=1",
    }
    assert trace["steps_summary"][1] == {
        "step_id": 1,
        "tool": "read_file",
        "success": False,
        "summary": "guardrail=sensitive_file_access",
    }
    assert trace["guardrail_events"] == [
        {
            "step_id": 1,
            "reason": "sensitive_file_access",
            "action_summary": "attempted to read .env",
        }
    ]
    assert trace["test_summary"] == {
        "final_passed": 3,
        "final_failed": 0,
        "final_status": "passed",
    }


def test_load_latest_trace_reads_saved_trace(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    add_sample_steps(session)
    manager = MemoryManager()
    trace_path = manager.save_trace(session, tmp_path)

    loaded = manager.load_latest_trace(tmp_path)

    assert loaded == read_trace(trace_path)


def test_load_latest_trace_returns_none_when_missing(tmp_path: Path) -> None:
    assert MemoryManager().load_latest_trace(tmp_path) is None


def test_trace_does_not_include_full_llm_response_or_context_payload(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    add_sample_steps(session)

    raw = MemoryManager().save_trace(session, tmp_path).read_text(encoding="utf-8")

    assert "RAW LLM RESPONSE" not in raw
    assert "ANOTHER RAW LLM RESPONSE" not in raw
    assert "FINAL RAW RESPONSE" not in raw
    assert "system prompt that must not be persisted" not in raw
    assert "task context that must not be persisted" not in raw
    assert "full context history must not be persisted" not in raw
    assert "llm_request" not in raw
    assert "llm_response" not in raw


def test_empty_session_can_be_saved_with_default_summaries(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    session.final_status = SessionStatus.RUNNING
    session.end_time = None

    trace = read_trace(MemoryManager().save_trace(session, tmp_path / "missing-output-dir"))

    assert trace["total_steps"] == 0
    assert trace["steps_summary"] == []
    assert trace["guardrail_events"] == []
    assert trace["test_summary"] == {
        "final_passed": 0,
        "final_failed": 0,
        "final_status": "unknown",
    }
    assert trace["end_time"] is None
