"""CLI command for running the SafeCode WebUI server."""

from __future__ import annotations

import typer
import uvicorn

from safecode.webui import app


def serve_command(
    host: str = typer.Option("0.0.0.0", "--host", help="Host interface for the WebUI server."),
    port: int = typer.Option(8000, "--port", help="Port for the WebUI server."),
) -> None:
    """Start the SafeCode WebUI server."""
    typer.echo(f"Starting SafeCode WebUI at http://{host}:{port}")
    try:
        uvicorn.run(app, host=host, port=port)
    except KeyboardInterrupt:
        typer.echo("SafeCode WebUI stopped")
