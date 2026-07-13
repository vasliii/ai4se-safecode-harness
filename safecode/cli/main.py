"""Minimal CLI entry point for SafeCode Harness."""

import typer

from safecode.cli.auth import auth_app

app = typer.Typer(
    help="SafeCode Harness: a controlled coding agent execution framework."
)
app.add_typer(auth_app, name="auth")


@app.callback(invoke_without_command=True)
def main() -> None:
    """SafeCode Harness command line entry point."""
