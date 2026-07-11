from __future__ import annotations

from pathlib import Path

from safecode.guardrail import PathGuard
from safecode.models import GuardrailEvent


def assert_path_blocked(event: GuardrailEvent | None) -> None:
    assert event is not None
    assert event.blocked is True
    assert event.reason == "path_outside_workspace"
    assert event.tool == "path_guard"
    assert event.recoverable is True
    assert event.action_summary
    assert event.suggestion


def test_workspace_root_file_path_passes(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "file.txt").write_text("content", encoding="utf-8")

    assert PathGuard().check("file.txt", workspace) is None


def test_nested_workspace_path_passes(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    nested = workspace / "src" / "pkg"
    nested.mkdir(parents=True)
    (nested / "module.py").write_text("print('ok')", encoding="utf-8")

    assert PathGuard().check("src/pkg/module.py", workspace) is None


def test_none_and_empty_paths_pass(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    guard = PathGuard()

    assert guard.check(None, workspace) is None
    assert guard.check("", workspace) is None
    assert guard.check("   ", workspace) is None


def test_parent_directory_escape_is_blocked(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    event = PathGuard().check("../outside.txt", workspace)

    assert_path_blocked(event)


def test_absolute_path_is_blocked(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")

    event = PathGuard().check(str(outside), workspace)

    assert_path_blocked(event)


def test_symlink_pointing_outside_workspace_is_blocked(monkeypatch, tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    original_resolve = Path.resolve

    def fake_resolve(self: Path, *args, **kwargs) -> Path:
        if self.name == "outside-link.txt":
            return original_resolve(outside, *args, **kwargs)
        return original_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", fake_resolve)

    event = PathGuard().check("outside-link.txt", workspace)

    assert_path_blocked(event)


def test_guardrail_event_contains_path_context(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    event = PathGuard().check("../secret.txt", workspace)

    assert_path_blocked(event)
    assert "../secret.txt" in event.action_summary
    assert "workspace" in event.suggestion.lower()

