from pathlib import Path

from safecode.context import ContextBuilder
from safecode.models import ContextPayload, RuntimeConfig, Session, SessionStep, TaskConfig


def make_session(workspace_root: Path, blocked_count: int = 2) -> Session:
    return Session(
        "session-fields",
        TaskConfig("task", "Task", "fix_bug", "Fix bug", "template", "pytest"),
        workspace_root,
        "mock",
        blocked_count=blocked_count,
    )


def test_workspace_tree_lists_files_and_ignores_cache_directories(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('ok')", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("secret", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "main.pyc").write_bytes(b"cache")
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".venv").mkdir()

    tree = ContextBuilder(RuntimeConfig()).build(make_session(tmp_path)).workspace_tree

    assert tree is not None
    assert "src/main.py" in tree
    assert ".git" not in tree
    assert "__pycache__" not in tree
    assert ".pytest_cache" not in tree
    assert ".venv" not in tree


def test_step_blocked_and_remaining_fields_are_populated(tmp_path: Path) -> None:
    session = make_session(tmp_path, blocked_count=2)
    for index in range(3):
        session.steps.append(SessionStep(index, ContextPayload("system", "task", index, 0, 10), "{}"))

    context = ContextBuilder(RuntimeConfig(max_iterations=5)).build(session)

    assert context.step_id == 3
    assert context.blocked_count == 2
    assert context.remaining_steps == 2
