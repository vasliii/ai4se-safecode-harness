"""CLI implementation for built-in SafeCode demos."""

from __future__ import annotations

from pathlib import Path

import typer

from safecode.config import TaskConfigLoader, ValidationError
from safecode.cli.run import run_task_config
from safecode.demos.mock_actions import get_demo_mock_actions

DEMO_ROOT = Path(__file__).resolve().parents[1] / "demos"

demo_app = typer.Typer(help="List and run SafeCode demo tasks.")


@demo_app.command("list")
def list_demos() -> None:
    """List available packaged demo tasks."""
    found = False
    for task_path in sorted(DEMO_ROOT.glob("*/task.yaml")):
        try:
            task_config = TaskConfigLoader().load(task_path)
        except Exception:
            continue
        found = True
        typer.echo(f"{task_path.parent.name}: {task_config.title} - {task_config.description}")
    if not found:
        typer.echo("No demos found.")


@demo_app.command("run")
def run_demo(
    demo_id: str = typer.Argument(...),
    mock: bool = typer.Option(False, "--mock", help="Run with MockLLM instead of RealLLM."),
    max_iterations: int | None = typer.Option(None, "--max-iterations"),
    model: str | None = typer.Option(None, "--model"),
    keep_session: bool = typer.Option(False, "--keep-session"),
    timeout: int | None = typer.Option(None, "--timeout"),
) -> None:
    """Run a packaged demo task by id."""
    task_path = DEMO_ROOT / demo_id / "task.yaml"
    if not task_path.exists():
        typer.echo(f"Demo not found: {demo_id}", err=True)
        raise typer.Exit(code=1)

    try:
        task_config = TaskConfigLoader().load(task_path)
    except ValidationError as exc:
        typer.echo(f"Invalid demo task.yaml: {'; '.join(exc.errors)}", err=True)
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"Invalid demo task.yaml: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    template = Path(task_config.workspace_template)
    if not template.is_absolute():
        task_config.workspace_template = str(((DEMO_ROOT / demo_id) / template).resolve())

    run_task_config(
        task_config=task_config,
        mock=mock,
        mock_actions=get_demo_mock_actions(demo_id) if mock else None,
        max_iterations=max_iterations,
        model=model,
        keep_session=keep_session,
        timeout=timeout,
    )
