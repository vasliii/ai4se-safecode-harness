from pathlib import Path

from safecode.models import Session, TaskConfig
from safecode.tools.edit_file import EditFileTool
from safecode.tools.write_file import WriteFileTool


def make_session(workspace_root: Path) -> Session:
    return Session(
        session_id="session-1",
        task_config=TaskConfig(
            id="task",
            title="Task",
            task_type="fix_bug",
            description="Fix a bug",
            workspace_template="template",
            test_command="pytest",
        ),
        workspace_root=workspace_root,
        llm_backend="mock",
    )


def test_write_file_creates_new_file(tmp_path: Path) -> None:
    result = WriteFileTool().execute(
        {"path": "src/app.py", "content": "print('hello')\n"},
        make_session(tmp_path),
    )

    assert result.success is True
    assert result.tool == "write_file"
    assert result.data == {"path": "src/app.py", "bytes_written": len("print('hello')\n".encode("utf-8"))}
    assert (tmp_path / "src" / "app.py").read_text(encoding="utf-8") == "print('hello')\n"


def test_write_file_overwrites_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "src" / "app.py"
    target.parent.mkdir()
    target.write_text("old\n", encoding="utf-8")

    result = WriteFileTool().execute({"path": "src/app.py", "content": "new\n"}, make_session(tmp_path))

    assert result.success is True
    assert target.read_text(encoding="utf-8") == "new\n"
    assert result.data["bytes_written"] == len("new\n".encode("utf-8"))


def test_write_file_creates_parent_directories(tmp_path: Path) -> None:
    result = WriteFileTool().execute(
        {"path": "a/b/c.txt", "content": "nested"},
        make_session(tmp_path),
    )

    assert result.success is True
    assert (tmp_path / "a" / "b" / "c.txt").read_text(encoding="utf-8") == "nested"


def test_write_file_supports_empty_content(tmp_path: Path) -> None:
    result = WriteFileTool().execute({"path": "empty.txt", "content": ""}, make_session(tmp_path))

    assert result.success is True
    assert result.data == {"path": "empty.txt", "bytes_written": 0}
    assert (tmp_path / "empty.txt").read_text(encoding="utf-8") == ""


def test_write_file_relative_path_is_based_on_workspace_root(tmp_path: Path, monkeypatch) -> None:
    outside = tmp_path / "outside"
    workspace = tmp_path / "workspace"
    outside.mkdir()
    workspace.mkdir()
    monkeypatch.chdir(outside)

    result = WriteFileTool().execute({"path": "file.txt", "content": "workspace"}, make_session(workspace))

    assert result.success is True
    assert (workspace / "file.txt").exists()
    assert not (outside / "file.txt").exists()


def test_write_file_missing_params_returns_error(tmp_path: Path) -> None:
    result = WriteFileTool().execute({"path": "file.txt"}, make_session(tmp_path))

    assert result.success is False
    assert "content" in result.error


def test_edit_file_replaces_unique_text(tmp_path: Path) -> None:
    target = tmp_path / "src" / "app.py"
    target.parent.mkdir()
    target.write_text("before\nold value\nafter\n", encoding="utf-8")

    result = EditFileTool().execute(
        {"path": "src/app.py", "old_text": "old value", "new_text": "new value"},
        make_session(tmp_path),
    )

    assert result.success is True
    assert result.tool == "edit_file"
    assert result.data == {"path": "src/app.py", "replaced": True}
    assert target.read_text(encoding="utf-8") == "before\nnew value\nafter\n"


def test_edit_file_old_text_not_found_returns_error(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("content\n", encoding="utf-8")

    result = EditFileTool().execute(
        {"path": "app.py", "old_text": "missing", "new_text": "new"},
        make_session(tmp_path),
    )

    assert result.success is False
    assert "not found" in result.error


def test_edit_file_old_text_multiple_matches_returns_error(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("repeat\nrepeat\n", encoding="utf-8")

    result = EditFileTool().execute(
        {"path": "app.py", "old_text": "repeat", "new_text": "new"},
        make_session(tmp_path),
    )

    assert result.success is False
    assert "multiple" in result.error
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "repeat\nrepeat\n"


def test_edit_file_empty_old_text_returns_error(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("content\n", encoding="utf-8")

    result = EditFileTool().execute(
        {"path": "app.py", "old_text": "", "new_text": "new"},
        make_session(tmp_path),
    )

    assert result.success is False
    assert "old_text" in result.error


def test_edit_file_missing_file_returns_error(tmp_path: Path) -> None:
    result = EditFileTool().execute(
        {"path": "missing.py", "old_text": "old", "new_text": "new"},
        make_session(tmp_path),
    )

    assert result.success is False
    assert "not found" in result.error


def test_edit_file_directory_returns_error(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()

    result = EditFileTool().execute(
        {"path": "src", "old_text": "old", "new_text": "new"},
        make_session(tmp_path),
    )

    assert result.success is False
    assert "directory" in result.error


def test_edit_file_binary_file_returns_error(tmp_path: Path) -> None:
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00\x00")

    result = EditFileTool().execute(
        {"path": "blob.bin", "old_text": "old", "new_text": "new"},
        make_session(tmp_path),
    )

    assert result.success is False
    assert "text" in result.error or "decode" in result.error


def test_edit_file_missing_params_returns_error(tmp_path: Path) -> None:
    result = EditFileTool().execute({"path": "app.py", "old_text": "old"}, make_session(tmp_path))

    assert result.success is False
    assert "new_text" in result.error