"""CLI tests for safecode serve command."""

from __future__ import annotations

from typer.testing import CliRunner

from safecode.cli import app
import safecode.cli.serve as serve_module
from safecode.webui import app as webui_app


class FakeUvicorn:
    calls: list[dict] = []
    error: BaseException | None = None

    @classmethod
    def run(cls, target_app, host: str, port: int) -> None:
        cls.calls.append({"app": target_app, "host": host, "port": port})
        if cls.error is not None:
            raise cls.error


def reset_fake_uvicorn() -> None:
    FakeUvicorn.calls = []
    FakeUvicorn.error = None


def invoke(args: list[str]):
    return CliRunner().invoke(app, args)


def test_serve_uses_default_host_and_port(monkeypatch):
    reset_fake_uvicorn()
    monkeypatch.setattr(serve_module.uvicorn, "run", FakeUvicorn.run)

    result = invoke(["serve"])

    assert result.exit_code == 0
    assert FakeUvicorn.calls == [{"app": webui_app, "host": "0.0.0.0", "port": 8000}]
    assert "Starting SafeCode WebUI at http://0.0.0.0:8000" in result.output


def test_serve_host_option_overrides_default(monkeypatch):
    reset_fake_uvicorn()
    monkeypatch.setattr(serve_module.uvicorn, "run", FakeUvicorn.run)

    result = invoke(["serve", "--host", "127.0.0.1"])

    assert result.exit_code == 0
    assert FakeUvicorn.calls[0]["host"] == "127.0.0.1"
    assert FakeUvicorn.calls[0]["port"] == 8000


def test_serve_port_option_overrides_default(monkeypatch):
    reset_fake_uvicorn()
    monkeypatch.setattr(serve_module.uvicorn, "run", FakeUvicorn.run)

    result = invoke(["serve", "--port", "9001"])

    assert result.exit_code == 0
    assert FakeUvicorn.calls[0]["host"] == "0.0.0.0"
    assert FakeUvicorn.calls[0]["port"] == 9001


def test_serve_host_and_port_options_both_apply(monkeypatch):
    reset_fake_uvicorn()
    monkeypatch.setattr(serve_module.uvicorn, "run", FakeUvicorn.run)

    result = invoke(["serve", "--host", "127.0.0.1", "--port", "8080"])

    assert result.exit_code == 0
    assert FakeUvicorn.calls[0]["host"] == "127.0.0.1"
    assert FakeUvicorn.calls[0]["port"] == 8080


def test_main_help_registers_serve_command():
    result = invoke(["--help"])

    assert result.exit_code == 0
    assert "serve" in result.output


def test_serve_handles_keyboard_interrupt(monkeypatch):
    reset_fake_uvicorn()
    FakeUvicorn.error = KeyboardInterrupt()
    monkeypatch.setattr(serve_module.uvicorn, "run", FakeUvicorn.run)

    result = invoke(["serve"])

    assert result.exit_code == 0
    assert "SafeCode WebUI stopped" in result.output
