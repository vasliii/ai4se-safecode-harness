from pathlib import Path

from safecode.context import ContextBuilder
from safecode.models import RuntimeConfig, Session, TaskConfig


def make_session(workspace_root: Path, *, blocked_count: int = 0) -> Session:
    return Session(
        session_id="session-context",
        task_config=TaskConfig(
            id="task-context",
            title="Context Task",
            task_type="fix_bug",
            description="Fix the failing calculator tests.",
            workspace_template="template",
            test_command="pytest",
        ),
        workspace_root=workspace_root,
        llm_backend="mock",
        blocked_count=blocked_count,
    )


def test_empty_session_builds_context_payload(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('ok')", encoding="utf-8")

    context = ContextBuilder(RuntimeConfig(max_iterations=10)).build(make_session(tmp_path))

    assert context.task_description == "Fix the failing calculator tests."
    assert context.step_id == 0
    assert context.blocked_count == 0
    assert context.remaining_steps == 10
    assert context.last_test_feedback is None
    assert context.last_tool_result is None
    assert context.last_guardrail_event is None
    assert context.recent_diffs == []
    assert context.workspace_tree is not None
    assert "src/main.py" in context.workspace_tree
    assert context.history_summary == "No previous steps."


def test_system_prompt_contains_safety_and_json_action_requirements(tmp_path: Path) -> None:
    context = ContextBuilder(RuntimeConfig()).build(make_session(tmp_path))
    prompt = context.system_prompt.lower()

    assert "safety rules" in prompt
    assert "json action" in prompt
    assert "workspace" in prompt
    assert "sensitive" in prompt
    assert ".env" in prompt
    assert "dangerous shell" in prompt
