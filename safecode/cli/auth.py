"""Authentication CLI commands for SafeCode Harness."""

from __future__ import annotations

import getpass

import typer

from safecode.auth import CredentialManager

auth_app = typer.Typer(help="Manage SafeCode API key credentials.")


@auth_app.command("set")
def set_api_key() -> None:
    """Store an API key in the system keyring."""
    key = getpass.getpass("Enter API Key: ")
    if not key.strip():
        typer.echo("Key cannot be empty", err=True)
        raise typer.Exit(code=1)

    try:
        CredentialManager().set_api_key(key)
    except Exception as exc:
        typer.echo(f"Failed to save API Key: {exc}", err=True)
        typer.echo("Set SAFECODE_API_KEY as an environment variable instead.", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo("API Key saved successfully")


@auth_app.command("status")
def status() -> None:
    """Show whether an API key is configured without revealing it."""
    credential_status = CredentialManager().status()
    typer.echo(f"API Key: {credential_status}")


@auth_app.command("clear")
def clear_api_key() -> None:
    """Remove the API key from the system keyring."""
    CredentialManager().clear_api_key()
    typer.echo("API Key cleared")
