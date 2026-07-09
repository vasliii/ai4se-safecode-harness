"""Minimal CLI entry point for SafeCode Harness."""

import typer

app = typer.Typer(
    help="SafeCode Harness: a controlled coding agent execution framework."
)


@app.callback(invoke_without_command=True)
def main() -> None:
    """SafeCode Harness command line entry point."""
