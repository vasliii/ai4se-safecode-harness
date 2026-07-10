import shutil
import tempfile
from pathlib import Path

import pytest

from safecode.core.workspace_manager import WorkspaceManager


def make_template(tmp_path: Path) -> Path:
    template = tmp_path / "template"
    package_dir = template / "src" / "demo"
    tests_dir = template / "tests"
    package_dir.mkdir(parents=True)
    tests_dir.mkdir()
    (template / "README.md").write_text("demo task\n", encoding="utf-8")
    (package_dir / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    (tests_dir / "test_app.py").write_text("def test_add():\n    assert True\n", encoding="utf-8")
    return template


def test_setup_creates_workspace_from_template(tmp_path: Path) -> None:
    template = make_template(tmp_path)
    manager = WorkspaceManager()

    workspace = manager.setup(template)

    try:
        assert workspace.exists()
        assert workspace.is_dir()
        assert workspace != template
        assert workspace.name.startswith("safecode-session-")
        assert workspace.parent == Path(tempfile.gettempdir())
        assert manager.workspace_root == workspace
    finally:
        manager.cleanup()


def test_setup_initializes_workspace_contents(tmp_path: Path) -> None:
    template = make_template(tmp_path)
    manager = WorkspaceManager()

    workspace = manager.setup(template)

    try:
        assert (workspace / "README.md").read_text(encoding="utf-8") == "demo task\n"
        assert (workspace / "src" / "demo" / "app.py").exists()
        assert (workspace / "tests" / "test_app.py").exists()
    finally:
        manager.cleanup()


def test_cleanup_removes_workspace(tmp_path: Path) -> None:
    template = make_template(tmp_path)
    manager = WorkspaceManager()
    workspace = manager.setup(template)

    manager.cleanup()

    assert not workspace.exists()
    assert manager.workspace_root is None


def test_cleanup_missing_workspace_is_noop(tmp_path: Path) -> None:
    template = make_template(tmp_path)
    manager = WorkspaceManager()
    workspace = manager.setup(template)
    shutil.rmtree(workspace)

    manager.cleanup()

    assert manager.workspace_root is None


def test_cleanup_keeps_workspace_when_requested(tmp_path: Path) -> None:
    template = make_template(tmp_path)
    manager = WorkspaceManager()
    workspace = manager.setup(template, keep=True)

    try:
        manager.cleanup()

        assert workspace.exists()
        assert manager.workspace_root == workspace
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_multiple_workspaces_are_isolated(tmp_path: Path) -> None:
    template = make_template(tmp_path)
    first = WorkspaceManager()
    second = WorkspaceManager()
    first_workspace = first.setup(template)
    second_workspace = second.setup(template)

    try:
        (first_workspace / "only_first.txt").write_text("first", encoding="utf-8")

        assert first_workspace != second_workspace
        assert (first_workspace / "only_first.txt").exists()
        assert not (second_workspace / "only_first.txt").exists()
    finally:
        first.cleanup()
        second.cleanup()


def test_setup_missing_template_raises_file_not_found(tmp_path: Path) -> None:
    manager = WorkspaceManager()

    with pytest.raises(FileNotFoundError):
        manager.setup(tmp_path / "missing-template")