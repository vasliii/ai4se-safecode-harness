"""Shared helpers for SafeCode mechanism demo tests."""

from __future__ import annotations

from pathlib import Path
import shutil

from safecode.config import TaskConfigLoader
from safecode.core.session_manager import SessionManager
from safecode.demos.mock_actions import get_demo_mock_actions
from safecode.llm import MockLLM
from safecode.models import RuntimeConfig, Session, TaskConfig

ROOT = Path(__file__).resolve().parents[2]
DEMO_ROOT = ROOT / "safecode" / "demos"


def load_demo_task(demo_id: str) -> TaskConfig:
    """Load a packaged demo task and resolve its workspace template path."""
    task_path = DEMO_ROOT / demo_id / "task.yaml"
    task_config = TaskConfigLoader().load(task_path)
    template = Path(task_config.workspace_template)
    if not template.is_absolute():
        task_config.workspace_template = str((task_path.parent / template).resolve())
    return task_config


def run_demo_session(
    demo_id: str,
    actions: list[dict] | None = None,
    *,
    max_iterations: int | None = None,
    guardrail_threshold: int = 3,
) -> Session:
    """Run a packaged demo with scripted MockLLM actions."""
    _remove_demo_caches()
    task_config = load_demo_task(demo_id)
    scripted_actions = actions if actions is not None else get_demo_mock_actions(demo_id)
    if scripted_actions is None:
        raise ValueError(f"No mock actions configured for demo: {demo_id}")
    config = RuntimeConfig(guardrail_threshold=guardrail_threshold)
    if max_iterations is not None:
        config.max_iterations = max_iterations
    return SessionManager(config, MockLLM(actions=scripted_actions)).run(task_config, keep_session=False)


def _remove_demo_caches() -> None:
    """Remove generated caches so copied demo templates contain only source files."""
    for cache_dir in DEMO_ROOT.rglob("__pycache__"):
        shutil.rmtree(cache_dir)
