"""CLI tests for safecode run and demo commands."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from safecode.cli import app
import safecode.cli.demo as demo_module
import safecode.cli.run as run_module
from safecode.models import ParsedAction, RuntimeConfig, Session, SessionStatus, SessionStep, TaskConfig, ToolResult
from safecode.models.context import ContextPayload


class FakeCredentialManager:
    status_value = "configured"

    def status(self) -> str:
        return type(self).status_value


class FakeLLMBackend:
    pass


class FakeSessionManager:
    calls: list[dict] = []

    def __init__(self, config: RuntimeConfig, llm_backend) -> None:
        self.config = config
        self.llm_backend = llm_backend

    def run(self, task_config: TaskConfig, keep_session: bool = False) -> Session:
        type(self).calls.append(
            {"config": self.config, "llm_backend": self.llm_backend, "task_config": task_config, "keep_session": keep_session}
        )
        context = ContextPayload(
            system_prompt="system",
            task_description=task_config.description,
            step_id=0,
            blocked_count=0,
            remaining_steps=1,
        )
        return Session(
            session_id="session-1",
            task_config=task_config,
            workspace_root=Path(task_config.workspace_template),
            llm_backend="FakeLLMBackend",
            final_status=SessionStatus.SUCCESS,
            steps=[
                SessionStep(
                    step_id=0,
                    llm_request=context,
                    llm_response='{"tool":"finish","params":{"summary":"done"}}',
                    parsed_action=ParsedAction(tool="finish", params={"summary": "done"}),
                    tool_result=ToolResult(tool="finish", success=True, data={"summary": "done"}),
                )
            ],
        )


class FakeConfigurationManager:
    calls: list[dict] = []

    def load(self, cli_overrides: dict | None = None) -> RuntimeConfig:
        type(self).calls.append(cli_overrides or {})
        overrides = cli_overrides or {}
        return RuntimeConfig(
            model=overrides.get("model", "fake-model"),
            max_iterations=overrides.get("max_iterations", 10),
            timeout_seconds=overrides.get("timeout_seconds", 300),
        )


class FakeFactory:
    calls: list[dict] = []

    @classmethod
    def create(cls, config, credential_manager, **kwargs):
        cls.calls.append({"config": config, "credential_manager": credential_manager, **kwargs})
        return FakeLLMBackend()


def reset_fakes() -> None:
    FakeCredentialManager.status_value = "configured"
    FakeSessionManager.calls = []
    FakeConfigurationManager.calls = []
    FakeFactory.calls = []


def patch_run_dependencies(monkeypatch) -> None:
    monkeypatch.setattr(run_module, "CredentialManager", FakeCredentialManager)
    monkeypatch.setattr(run_module, "ConfigurationManager", FakeConfigurationManager)
    monkeypatch.setattr(run_module, "SessionManager", FakeSessionManager)
    monkeypatch.setattr(run_module, "create_llm_backend", FakeFactory.create)


def write_task_yaml(workspace: Path, *, title: str = "Example Task", description: str = "Fix it") -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "task.yaml").write_text(
        "\n".join(
            [
                "id: example",
                f"title: {title}",
                "task_type: fix_bug",
                f"description: {description}",
                "workspace_template: .",
                "test_command: pytest",
            ]
        ),
        encoding="utf-8",
    )


def test_run_workspace_mock_uses_mock_backend_and_outputs_final_status(tmp_path, monkeypatch):
    reset_fakes()
    patch_run_dependencies(monkeypatch)
    write_task_yaml(tmp_path)

    result = CliRunner().invoke(app, ["run", "--workspace", str(tmp_path), "--mock"])

    assert result.exit_code == 0
    assert FakeFactory.calls[0]["mock"] is True
    assert FakeFactory.calls[0]["mock_actions"] == [{"tool": "finish", "params": {"summary": "Mock CLI run finished."}}]
    assert FakeSessionManager.calls
    assert "final_status: success" in result.output
    assert "step 0" in result.output
    assert "action: finish" in result.output
    assert "tool_result: finish success=True" in result.output


def test_run_applies_cli_overrides(tmp_path, monkeypatch):
    reset_fakes()
    patch_run_dependencies(monkeypatch)
    write_task_yaml(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--workspace",
            str(tmp_path),
            "--mock",
            "--max-iterations",
            "3",
            "--model",
            "override-model",
            "--timeout",
            "9",
            "--keep-session",
        ],
    )

    assert result.exit_code == 0
    assert FakeConfigurationManager.calls[0] == {
        "max_iterations": 3,
        "model": "override-model",
        "timeout_seconds": 9,
    }
    assert FakeSessionManager.calls[0]["keep_session"] is True


def test_real_run_without_api_key_prompts_auth_set(tmp_path, monkeypatch):
    reset_fakes()
    patch_run_dependencies(monkeypatch)
    FakeCredentialManager.status_value = "missing"
    write_task_yaml(tmp_path)

    result = CliRunner().invoke(app, ["run", "--workspace", str(tmp_path)])

    assert result.exit_code != 0
    assert "safecode auth set" in result.output
    assert not FakeFactory.calls


def test_run_workspace_missing_reports_error(tmp_path, monkeypatch):
    reset_fakes()
    patch_run_dependencies(monkeypatch)
    missing = tmp_path / "missing"

    result = CliRunner().invoke(app, ["run", "--workspace", str(missing), "--mock"])

    assert result.exit_code != 0
    assert "Workspace path does not exist" in result.output


def test_run_task_yaml_missing_reports_error(tmp_path, monkeypatch):
    reset_fakes()
    patch_run_dependencies(monkeypatch)

    result = CliRunner().invoke(app, ["run", "--workspace", str(tmp_path), "--mock"])

    assert result.exit_code != 0
    assert "task.yaml not found" in result.output


def test_demo_list_outputs_available_demos(tmp_path, monkeypatch):
    demo_root = tmp_path / "demos"
    demo_dir = demo_root / "demo_one"
    write_task_yaml(demo_dir, title="Demo One", description="Demo description")
    monkeypatch.setattr(demo_module, "DEMO_ROOT", demo_root)

    result = CliRunner().invoke(app, ["demo", "list"])

    assert result.exit_code == 0
    assert "demo_one" in result.output
    assert "Demo One" in result.output
    assert "Demo description" in result.output


def test_demo_run_mock_executes_demo(tmp_path, monkeypatch):
    reset_fakes()
    patch_run_dependencies(monkeypatch)
    demo_root = tmp_path / "demos"
    demo_dir = demo_root / "demo_one"
    write_task_yaml(demo_dir, title="Demo One", description="Demo description")
    monkeypatch.setattr(demo_module, "DEMO_ROOT", demo_root)

    result = CliRunner().invoke(app, ["demo", "run", "demo_one", "--mock"])

    assert result.exit_code == 0
    assert FakeFactory.calls[0]["mock"] is True
    assert FakeSessionManager.calls
    assert "final_status: success" in result.output


def test_demo_run_missing_id_reports_error(tmp_path, monkeypatch):
    reset_fakes()
    patch_run_dependencies(monkeypatch)
    monkeypatch.setattr(demo_module, "DEMO_ROOT", tmp_path / "demos")

    result = CliRunner().invoke(app, ["demo", "run", "missing", "--mock"])

    assert result.exit_code != 0
    assert "Demo not found" in result.output


def test_main_help_registers_run_and_demo_commands():
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "run" in result.output
    assert "demo" in result.output
