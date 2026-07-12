"""Tests for deterministic MockLLM behavior."""

from __future__ import annotations

import json

from safecode.core.action_parser import ActionParser
from safecode.llm import LLMBackend, MockLLM, Rule
from safecode.models import ContextPayload, TestFeedback


def make_context(step_id: int = 0, failed_count: int | None = None) -> ContextPayload:
    feedback = None
    if failed_count is not None:
        feedback = TestFeedback(
            exit_code=1 if failed_count else 0,
            passed_count=1,
            failed_count=failed_count,
            skipped_count=0,
            duration_ms=10,
            status="failed" if failed_count else "passed",
        )
    return ContextPayload(
        system_prompt="system",
        task_description="task",
        step_id=step_id,
        blocked_count=0,
        remaining_steps=5,
        last_test_feedback=feedback,
    )


def parse_action(response: str):
    return ActionParser().parse(response)


def test_mock_llm_is_llm_backend():
    assert isinstance(MockLLM(actions=[]), LLMBackend)


def test_scripted_mode_returns_actions_in_order_then_finish():
    llm = MockLLM(
        actions=[
            {"tool": "list_files", "params": {"path": "."}},
            {"tool": "read_file", "params": {"path": "src/app.py"}},
            {"tool": "run_tests", "params": {}},
        ]
    )

    first = parse_action(llm.query(make_context()))
    second = parse_action(llm.query(make_context()))
    third = parse_action(llm.query(make_context()))
    fourth = parse_action(llm.query(make_context()))

    assert first.tool == "list_files"
    assert second.tool == "read_file"
    assert third.tool == "run_tests"
    assert fourth.tool == "finish"
    assert fourth.params["summary"]


def test_scripted_empty_actions_returns_finish():
    action = parse_action(MockLLM(actions=[]).query(make_context()))

    assert action.tool == "finish"
    assert "summary" in action.params


def test_rule_based_step_id_match_returns_rule_action():
    llm = MockLLM(
        rules=[
            Rule(
                predicate=lambda ctx: ctx.step_id == 0,
                action={"tool": "list_files", "params": {"path": "."}},
            )
        ]
    )

    action = parse_action(llm.query(make_context(step_id=0)))

    assert action.tool == "list_files"
    assert action.params == {"path": "."}


def test_rule_based_step_id_mismatch_returns_finish():
    llm = MockLLM(
        rules=[
            Rule(
                predicate=lambda ctx: ctx.step_id == 0,
                action={"tool": "list_files", "params": {"path": "."}},
            )
        ]
    )

    action = parse_action(llm.query(make_context(step_id=1)))

    assert action.tool == "finish"


def test_rule_based_can_use_last_test_feedback():
    llm = MockLLM(
        rules=[
            Rule(
                predicate=lambda ctx: ctx.last_test_feedback is not None
                and ctx.last_test_feedback.failed_count > 0,
                action={
                    "tool": "edit_file",
                    "params": {
                        "path": "src/app.py",
                        "old_text": "return False",
                        "new_text": "return True",
                    },
                },
            )
        ]
    )

    action = parse_action(llm.query(make_context(failed_count=1)))

    assert action.tool == "edit_file"
    assert action.params["path"] == "src/app.py"


def test_rule_based_no_match_returns_finish():
    llm = MockLLM(
        rules=[
            Rule(
                predicate=lambda ctx: False,
                action={"tool": "run_tests", "params": {}},
            )
        ]
    )

    action = parse_action(llm.query(make_context()))

    assert action.tool == "finish"


def test_rule_based_predicate_exception_is_skipped():
    def broken_predicate(context):
        raise RuntimeError("predicate failed")

    llm = MockLLM(
        rules=[
            Rule(predicate=broken_predicate, action={"tool": "run_shell", "params": {"command": "bad"}}),
            Rule(predicate=lambda ctx: True, action={"tool": "run_tests", "params": {}}),
        ]
    )

    action = parse_action(llm.query(make_context()))

    assert action.tool == "run_tests"


def test_rule_based_is_deterministic_for_same_context():
    llm = MockLLM(
        rules=[
            Rule(
                predicate=lambda ctx: ctx.step_id == 0,
                action={"tool": "read_file", "params": {"path": "README.md"}},
            )
        ]
    )
    context = make_context(step_id=0)

    assert llm.query(context) == llm.query(context)


def test_responses_are_valid_json_and_parseable():
    response = MockLLM(actions=[{"tool": "finish", "params": {"summary": "done"}}]).query(
        make_context()
    )

    assert json.loads(response) == {"tool": "finish", "params": {"summary": "done"}}
    assert parse_action(response).tool == "finish"
