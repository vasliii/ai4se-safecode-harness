"""CLI implementation for running SafeCode tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from safecode.auth import CredentialManager
from safecode.config import ConfigurationManager, TaskConfigLoader, ValidationError
from safecode.core.session_manager import SessionManager
from safecode.llm import create_llm_backend
from safecode.models import RuntimeConfig, Session, TaskConfig

DEFAULT_MOCK_ACTIONS = [{"tool": "finish", "params": {"summary": "Mock CLI run finished."}}]


def run_task_command(
    workspace: Path = typer.Option(..., "--workspace", help="Workspace containing task.yaml."),
    mock: bool = typer.Option(False, "--mock", help="Run with MockLLM instead of RealLLM."),
    max_iterations: int | None = typer.Option(None, "--max-iterations"),
    model: str | None = typer.Option(None, "--model"),
    keep_session: bool = typer.Option(False, "--keep-session"),
    timeout: int | None = typer.Option(None, "--timeout"),
) -> None:
    """Run a SafeCode task from a workspace directory."""
    run_workspace(
        workspace=workspace,
        mock=mock,
        max_iterations=max_iterations,
        model=model,
        keep_session=keep_session,
        timeout=timeout,
    )


def run_workspace(
    *,
    workspace: Path,
    mock: bool,
    max_iterations: int | None = None,
    model: str | None = None,
    keep_session: bool = False,
    timeout: int | None = None,
) -> Session:
    """Load a workspace task, execute it, print a compact trace, and return the session."""
    task_path = _task_path_for_workspace(workspace)
    task_config = _load_task_config(task_path)
    task_config = _resolve_workspace_template(task_config, workspace)
    return run_task_config(
        task_config=task_config,
        mock=mock,
        max_iterations=max_iterations,
        model=model,
        keep_session=keep_session,
        timeout=timeout,
    )


def run_task_config(
    *,
    task_config: TaskConfig,
    mock: bool,
    max_iterations: int | None = None,
    model: str | None = None,
    keep_session: bool = False,
    timeout: int | None = None,
) -> Session:
    """Execute an already-loaded task config and print the resulting trace."""
    cli_overrides = _build_cli_overrides(max_iterations=max_iterations, model=model, timeout=timeout)
    try:
        config = ConfigurationManager().load(cli_overrides=cli_overrides)
    except Exception as exc:
        _fail(f"Invalid runtime configuration: {exc}")

    credential_manager = CredentialManager()
    if not mock and credential_manager.status() == "missing":
        _fail("API key missing. Run `safecode auth set` before using real LLM mode.")

    llm_backend = create_llm_backend(
        config,
        credential_manager,
        mock=mock,
        mock_actions=DEFAULT_MOCK_ACTIONS if mock else None,
    )
    session = SessionManager(config, llm_backend).run(task_config, keep_session=keep_session)
    print_session_trace(session)
    return session


def print_session_trace(session: Session) -> None:
    """Print a compact, structured session trace."""
    typer.echo(f"session_id: {session.session_id}")
    for step in session.steps:
        typer.echo(f"step {step.step_id}")
        if step.parsed_action is not None:
            typer.echo(f"  action: {step.parsed_action.tool}")
        if step.tool_result is not None:
            typer.echo(
                f"  tool_result: {step.tool_result.tool} success={step.tool_result.success}"
            )
            if step.tool_result.error:
                typer.echo(f"  tool_error: {step.tool_result.error}")
        if step.test_feedback is not None:
            typer.echo(
                f"  tests: {step.test_feedback.status} "
                f"passed={step.test_feedback.passed_count} failed={step.test_feedback.failed_count}"
            )
        if step.guardrail_result is not None:
            typer.echo(f"  guardrail: {step.guardrail_result.reason}")
    typer.echo(f"final_status: {_status_value(session.final_status)}")


def _task_path_for_workspace(workspace: Path) -> Path:
    if not workspace.exists():
        _fail(f"Workspace path does not exist: {workspace}")
    if not workspace.is_dir():
        _fail(f"Workspace path is not a directory: {workspace}")
    task_path = workspace / "task.yaml"
    if not task_path.exists():
        _fail(f"task.yaml not found in workspace: {workspace}")
    return task_path


def _load_task_config(task_path: Path) -> TaskConfig:
    try:
        return TaskConfigLoader().load(task_path)
    except ValidationError as exc:
        _fail(f"Invalid task.yaml: {'; '.join(exc.errors)}")
    except Exception as exc:
        _fail(f"Invalid task.yaml: {exc}")


def _resolve_workspace_template(task_config: TaskConfig, workspace: Path) -> TaskConfig:
    template = Path(task_config.workspace_template)
    if not template.is_absolute():
        task_config.workspace_template = str((workspace / template).resolve())
    return task_config


def _build_cli_overrides(
    *, max_iterations: int | None, model: str | None, timeout: int | None
) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    if max_iterations is not None:
        overrides["max_iterations"] = max_iterations
    if model is not None:
        overrides["model"] = model
    if timeout is not None:
        overrides["timeout_seconds"] = timeout
    return overrides


def _status_value(status: object) -> str:
    return status.value if hasattr(status, "value") else str(status)


def _fail(message: str) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(code=1)
