from pathlib import Path

from safecode.context import ContextBuilder
from safecode.models import ContextPayload, RuntimeConfig, Session, SessionStep, TaskConfig, ToolResult


def make_session(workspace_root: Path) -> Session:
    return Session(
        "session-sensitive",
        TaskConfig("task", "Task", "fix_bug", "Fix bug", "template", "pytest"),
        workspace_root,
        "mock",
    )


def test_context_does_not_include_env_file_content_or_api_key_patterns(tmp_path: Path) -> None:
    secret = "sk-1234567890abcdef1234567890abcdef"
    (tmp_path / ".env").write_text(f"SAFECODE_API_KEY={secret}", encoding="utf-8")
    (tmp_path / "app.py").write_text("print('safe')", encoding="utf-8")
    session = make_session(tmp_path)
    session.steps.append(
        SessionStep(
            0,
            ContextPayload("system", "task", 0, 0, 10),
            "{}",
            tool_result=ToolResult("read_file", True, {"content": f"token={secret}"}, error=f"failed {secret}"),
        )
    )

    context = ContextBuilder(RuntimeConfig()).build(session)
    serialized = str(context.to_dict())

    assert secret not in serialized
    assert "SAFECODE_API_KEY" not in serialized
    assert "app.py" in (context.workspace_tree or "")
