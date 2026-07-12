from pathlib import Path

from safecode.context import ContextBuilder
from safecode.models import ContextPayload, ParsedAction, RuntimeConfig, Session, SessionStep, TaskConfig, ToolResult


def make_session(workspace_root: Path) -> Session:
    return Session(
        "session-budget",
        TaskConfig("task", "Task", "fix_bug", "This task description must always remain intact.", "template", "pytest"),
        workspace_root,
        "mock",
    )


def test_budget_keeps_system_prompt_and_task_description(tmp_path: Path) -> None:
    for index in range(30):
        (tmp_path / f"file_{index}.py").write_text("print('x')", encoding="utf-8")
    session = make_session(tmp_path)
    for index in range(10):
        session.steps.append(
            SessionStep(
                index,
                ContextPayload("system", "task", index, 0, 10),
                "{}",
                parsed_action=ParsedAction("read_file", {"path": f"file_{index}.py"}),
                tool_result=ToolResult("read_file", True, {"content": "x" * 1000}),
            )
        )

    context = ContextBuilder(RuntimeConfig(max_iterations=20, context_budget_chars=500)).build(session)

    assert "safety rules" in context.system_prompt.lower()
    assert context.task_description == "This task description must always remain intact."
    assert context.history_summary is None or len(context.history_summary) < 500
    assert context.workspace_tree is None or len(context.workspace_tree) < 500


def test_remaining_steps_never_negative(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    for index in range(5):
        session.steps.append(SessionStep(index, ContextPayload("system", "task", index, 0, 2), "{}"))

    context = ContextBuilder(RuntimeConfig(max_iterations=2)).build(session)

    assert context.remaining_steps == 0
