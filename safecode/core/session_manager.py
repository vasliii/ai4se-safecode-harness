"""Session lifecycle orchestration for SafeCode Harness."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
import uuid

from safecode.context import ContextBuilder, MemoryManager
from safecode.core.agent_loop import AgentLoop
from safecode.core.workspace_manager import WorkspaceManager
from safecode.feedback import TestFeedbackSummarizer
from safecode.guardrail import Guardrail
from safecode.llm import LLMBackend
from safecode.models import ContextPayload, RuntimeConfig, Session, SessionStatus, TaskConfig
from safecode.tools import ToolDispatcher, create_default_tools


class _AgentLoopContextBuilder:
    """Adapt ContextBuilder to AgentLoop's current build(session, config) protocol."""

    def __init__(self, config: RuntimeConfig) -> None:
        self.config = config
        self.builder = ContextBuilder(config)

    def build(self, session: Session, config: RuntimeConfig) -> ContextPayload:
        if config is not self.config:
            self.config = config
            self.builder = ContextBuilder(config)
        return self.builder.build(session)


class SessionManager:
    """Create, run, persist, and clean up one SafeCode session."""

    def __init__(self, config: RuntimeConfig, llm_backend: LLMBackend) -> None:
        self.config = config
        self.llm_backend = llm_backend
        self.workspace_manager = WorkspaceManager()
        self.memory_manager = MemoryManager()
        self._effective_config = config

    def run(self, task_config: TaskConfig, keep_session: bool = False) -> Session:
        """Run a full session lifecycle and return the final Session."""
        session: Session | None = None
        try:
            session = self._create_session(task_config)
            self._effective_config = self._merge_task_overrides(task_config)
            session = self._run_agent_loop(session)
            return session
        finally:
            if session is not None:
                session.end_time = session.end_time or datetime.now()
                self._persist_trace(session)
                self._cleanup(session, keep_session)

    def _create_session(self, task_config: TaskConfig) -> Session:
        workspace_root = self._setup_workspace(task_config)
        return Session(
            session_id=str(uuid.uuid4()),
            task_config=task_config,
            workspace_root=workspace_root,
            llm_backend=self.llm_backend.__class__.__name__,
        )

    def _setup_workspace(self, task_config: TaskConfig) -> Path:
        template_path = Path(task_config.workspace_template)
        if not template_path.exists():
            raise FileNotFoundError(f"Workspace template does not exist: {template_path}")
        if not template_path.is_dir():
            raise NotADirectoryError(f"Workspace template is not a directory: {template_path}")
        return self.workspace_manager.setup(template_path)

    def _run_agent_loop(self, session: Session) -> Session:
        if session.final_status is not SessionStatus.RUNNING:
            return session

        agent_loop = AgentLoop(
            context_builder=_AgentLoopContextBuilder(self._effective_config),
            guardrail=Guardrail(self._effective_config.shell_allowlist),
            tool_dispatcher=ToolDispatcher(create_default_tools()),
            feedback_summarizer=TestFeedbackSummarizer(),
        )
        return agent_loop.run(session, self.llm_backend, self._effective_config)

    def _persist_trace(self, session: Session) -> Path:
        return self.memory_manager.save_trace(session, session.workspace_root)

    def _cleanup(self, session: Session, keep: bool) -> None:
        if keep:
            return
        self.workspace_manager.workspace_root = session.workspace_root
        self.workspace_manager.cleanup()

    def _merge_task_overrides(self, task_config: TaskConfig) -> RuntimeConfig:
        updates: dict[str, int] = {}
        if task_config.max_iterations is not None:
            updates["max_iterations"] = task_config.max_iterations
        if task_config.timeout_seconds is not None:
            updates["timeout_seconds"] = task_config.timeout_seconds
        if updates:
            return replace(self.config, **updates)
        return replace(self.config)
