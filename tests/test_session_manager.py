"""Tests for complete SafeCode session lifecycle orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from safecode.llm import LLMBackend
from safecode.models import ContextPayload, RuntimeConfig, Session, SessionStatus, TaskConfig
from safecode.core.session_manager import SessionManager
import safecode.core.session_manager as session_manager_module


class FakeLLMBackend(LLMBackend):
    def query(self, context: ContextPayload) -> str:
        return '{"tool": "finish", "params": {}}'


class RecordingAgentLoop:
    called = False
    captured_config: RuntimeConfig | None = None
    captured_kwargs: dict | None = None

    def __init__(self, **kwargs):
        type(self).captured_kwargs = kwargs

    def run(self, session: Session, llm_backend: LLMBackend, config: RuntimeConfig) -> Session:
        type(self).called = True
        type(self).captured_config = config
        session.final_status = SessionStatus.SUCCESS
        return session


class FailingAgentLoop:
    def __init__(self, **kwargs):
        pass

    def run(self, session: Session, llm_backend: LLMBackend, config: RuntimeConfig) -> Session:
        raise RuntimeError("agent failed")


class RecordingMemoryManager:
    def __init__(self) -> None:
        self.saved: list[tuple[Session, Path]] = []

    def save_trace(self, session: Session, output_dir: Path) -> Path:
        self.saved.append((session, output_dir))
        return output_dir / ".safecode" / "session_trace.json"


def make_task_config(template: Path, **overrides) -> TaskConfig:
    data = {
        "id": "task-1",
        "title": "Task One",
        "task_type": "fix_bug",
        "description": "Fix the failing test.",
        "workspace_template": str(template),
        "test_command": "pytest",
    }
    data.update(overrides)
    return TaskConfig(**data)


def make_template(tmp_path: Path) -> Path:
    template = tmp_path / "template"
    template.mkdir()
    (template / "app.py").write_text("print('hello')\n", encoding="utf-8")
    return template


def reset_recording_loop() -> None:
    RecordingAgentLoop.called = False
    RecordingAgentLoop.captured_config = None
    RecordingAgentLoop.captured_kwargs = None


def test_run_returns_session_sets_workspace_calls_agent_and_saves_trace(tmp_path, monkeypatch):
    template = make_template(tmp_path)
    reset_recording_loop()
    monkeypatch.setattr(session_manager_module, "AgentLoop", RecordingAgentLoop)

    manager = SessionManager(RuntimeConfig(), FakeLLMBackend())
    session = manager.run(make_task_config(template), keep_session=True)

    assert isinstance(session, Session)
    assert session.workspace_root.exists()
    assert (session.workspace_root / "app.py").exists()
    assert RecordingAgentLoop.called is True
    assert session.end_time is not None
    assert (session.workspace_root / ".safecode" / "session_trace.json").exists()
    assert session.final_status == SessionStatus.SUCCESS
    assert RecordingAgentLoop.captured_kwargs is not None
    assert {"context_builder", "guardrail", "tool_dispatcher", "feedback_summarizer"}.issubset(
        RecordingAgentLoop.captured_kwargs
    )


def test_run_cleans_workspace_by_default(tmp_path, monkeypatch):
    template = make_template(tmp_path)
    reset_recording_loop()
    monkeypatch.setattr(session_manager_module, "AgentLoop", RecordingAgentLoop)

    session = SessionManager(RuntimeConfig(), FakeLLMBackend()).run(make_task_config(template))

    assert not session.workspace_root.exists()


def test_task_config_overrides_runtime_limits(tmp_path, monkeypatch):
    template = make_template(tmp_path)
    reset_recording_loop()
    monkeypatch.setattr(session_manager_module, "AgentLoop", RecordingAgentLoop)

    config = RuntimeConfig(max_iterations=10, timeout_seconds=300)
    task_config = make_task_config(template, max_iterations=2, timeout_seconds=5)

    SessionManager(config, FakeLLMBackend()).run(task_config)

    assert RecordingAgentLoop.captured_config is not None
    assert RecordingAgentLoop.captured_config.max_iterations == 2
    assert RecordingAgentLoop.captured_config.timeout_seconds == 5


def test_missing_workspace_template_raises_clear_error(tmp_path):
    missing = tmp_path / "missing-template"
    manager = SessionManager(RuntimeConfig(), FakeLLMBackend())

    with pytest.raises(FileNotFoundError, match="Workspace template"):
        manager.run(make_task_config(missing))


def test_agent_loop_exception_still_sets_end_time_persists_trace_and_cleans_workspace(
    tmp_path, monkeypatch
):
    template = make_template(tmp_path)
    memory = RecordingMemoryManager()
    monkeypatch.setattr(session_manager_module, "AgentLoop", FailingAgentLoop)
    monkeypatch.setattr(session_manager_module, "MemoryManager", lambda: memory)

    manager = SessionManager(RuntimeConfig(), FakeLLMBackend())

    with pytest.raises(RuntimeError, match="agent failed"):
        manager.run(make_task_config(template), keep_session=False)

    assert len(memory.saved) == 1
    saved_session, saved_output_dir = memory.saved[0]
    assert saved_session.end_time is not None
    assert saved_output_dir == saved_session.workspace_root
    assert not saved_session.workspace_root.exists()
