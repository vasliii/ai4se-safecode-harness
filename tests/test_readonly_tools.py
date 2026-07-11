from pathlib import Path

from safecode.models import Session, TaskConfig
from safecode.tools.list_files import ListFilesTool
from safecode.tools.read_file import ReadFileTool
from safecode.tools.search_content import SearchContentTool


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


def test_list_files_empty_directory(tmp_path: Path) -> None:
    result = ListFilesTool().execute({"path": "."}, make_session(tmp_path))

    assert result.success is True
    assert result.tool == "list_files"
    assert result.data == {"tree": "", "files": []}


def test_list_files_lists_files_and_nested_directories(tmp_path: Path) -> None:
    (tmp_path / "src" / "pkg").mkdir(parents=True)
    (tmp_path / "src" / "pkg" / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")

    result = ListFilesTool().execute({"path": "."}, make_session(tmp_path))

    assert result.success is True
    assert result.data["files"] == ["README.md", "src/pkg/app.py"]
    assert "README.md" in result.data["tree"]
    assert "src/pkg/app.py" in result.data["tree"]


def test_list_files_can_disable_recursion(tmp_path: Path) -> None:
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "child.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "root.py").write_text("x = 2\n", encoding="utf-8")

    result = ListFilesTool().execute({"path": ".", "recursive": False}, make_session(tmp_path))

    assert result.success is True
    assert result.data["files"] == ["root.py"]


def test_list_files_ignores_internal_directories(tmp_path: Path) -> None:
    for ignored in [".git", ".venv", "__pycache__", ".pytest_cache"]:
        (tmp_path / ignored).mkdir()
        (tmp_path / ignored / "hidden.py").write_text("hidden\n", encoding="utf-8")
    (tmp_path / "visible.py").write_text("visible\n", encoding="utf-8")

    result = ListFilesTool().execute({"path": "."}, make_session(tmp_path))

    assert result.success is True
    assert result.data["files"] == ["visible.py"]
    assert "hidden.py" not in result.data["tree"]


def test_list_files_missing_path_returns_error(tmp_path: Path) -> None:
    result = ListFilesTool().execute({"path": "missing"}, make_session(tmp_path))

    assert result.success is False
    assert result.tool == "list_files"
    assert "not found" in result.error


def test_read_file_reads_text_file(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("one\ntwo\nthree\n", encoding="utf-8")

    result = ReadFileTool().execute({"path": "notes.txt"}, make_session(tmp_path))

    assert result.success is True
    assert result.data == {"content": "one\ntwo\nthree\n", "path": "notes.txt", "lines": 3}


def test_read_file_supports_line_range(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("one\ntwo\nthree\nfour\n", encoding="utf-8")

    result = ReadFileTool().execute(
        {"path": "notes.txt", "start_line": 2, "end_line": 3},
        make_session(tmp_path),
    )

    assert result.success is True
    assert result.data == {"content": "two\nthree\n", "path": "notes.txt", "lines": 2}


def test_read_file_missing_file_returns_error(tmp_path: Path) -> None:
    result = ReadFileTool().execute({"path": "missing.txt"}, make_session(tmp_path))

    assert result.success is False
    assert "not found" in result.error


def test_read_file_directory_returns_error(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()

    result = ReadFileTool().execute({"path": "src"}, make_session(tmp_path))

    assert result.success is False
    assert "directory" in result.error


def test_read_file_binary_file_returns_error(tmp_path: Path) -> None:
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00\x00")

    result = ReadFileTool().execute({"path": "blob.bin"}, make_session(tmp_path))

    assert result.success is False
    assert "text" in result.error or "decode" in result.error


def test_search_content_finds_matches(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("alpha\nbeta target\ngamma target\n", encoding="utf-8")

    result = SearchContentTool().execute({"pattern": "target"}, make_session(tmp_path))

    assert result.success is True
    assert result.data["count"] == 2
    assert result.data["matches"] == [
        {"file": "app.py", "line": 2, "content": "beta target"},
        {"file": "app.py", "line": 3, "content": "gamma target"},
    ]


def test_search_content_no_matches_returns_empty_list(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("alpha\n", encoding="utf-8")

    result = SearchContentTool().execute({"pattern": "target"}, make_session(tmp_path))

    assert result.success is True
    assert result.data == {"matches": [], "count": 0}


def test_search_content_supports_regex(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("value_123\nvalue_abc\n", encoding="utf-8")

    result = SearchContentTool().execute({"pattern": r"value_\d+"}, make_session(tmp_path))

    assert result.success is True
    assert result.data["matches"] == [{"file": "app.py", "line": 1, "content": "value_123"}]


def test_search_content_limits_to_subdirectory(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "docs").mkdir()
    (tmp_path / "src" / "app.py").write_text("target\n", encoding="utf-8")
    (tmp_path / "docs" / "guide.md").write_text("target\n", encoding="utf-8")

    result = SearchContentTool().execute({"pattern": "target", "path": "src"}, make_session(tmp_path))

    assert result.success is True
    assert result.data["matches"] == [{"file": "src/app.py", "line": 1, "content": "target"}]


def test_search_content_limits_to_file_pattern(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("target\n", encoding="utf-8")
    (tmp_path / "notes.md").write_text("target\n", encoding="utf-8")

    result = SearchContentTool().execute(
        {"pattern": "target", "file_pattern": "*.md"},
        make_session(tmp_path),
    )

    assert result.success is True
    assert result.data["matches"] == [{"file": "notes.md", "line": 1, "content": "target"}]


def test_search_content_missing_path_returns_error(tmp_path: Path) -> None:
    result = SearchContentTool().execute({"pattern": "target", "path": "missing"}, make_session(tmp_path))

    assert result.success is False
    assert "not found" in result.error


def test_search_content_skips_binary_files(tmp_path: Path) -> None:
    (tmp_path / "blob.bin").write_bytes(b"\xff\xfe\x00\x00")
    (tmp_path / "app.py").write_text("target\n", encoding="utf-8")

    result = SearchContentTool().execute({"pattern": "target"}, make_session(tmp_path))

    assert result.success is True
    assert result.data["matches"] == [{"file": "app.py", "line": 1, "content": "target"}]