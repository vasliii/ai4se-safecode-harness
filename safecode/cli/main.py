"""Minimal CLI entry point for SafeCode Harness."""

import typer

from safecode.cli.auth import auth_app
from safecode.cli.demo import demo_app
from safecode.cli.run import run_task_command
from safecode.cli.serve import serve_command

app = typer.Typer(
    help="SafeCode Harness: a controlled coding agent execution framework."
)
app.add_typer(auth_app, name="auth")
app.add_typer(demo_app, name="demo")
app.command("run")(run_task_command)
app.command("serve")(serve_command)


@app.callback(invoke_without_command=True)
def main() -> None:
    """SafeCode Harness command line entry point."""

