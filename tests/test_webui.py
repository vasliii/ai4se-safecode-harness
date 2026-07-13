"""Tests for the lightweight SafeCode WebUI."""

from __future__ import annotations

from pathlib import Path
import importlib

from fastapi.testclient import TestClient

webui_module = importlib.import_module("safecode.webui.app")
from safecode.webui import app
from safecode.models import (
    ContextPayload,
    GuardrailEvent,
    ParsedAction,
    RuntimeConfig,
    Session,
    SessionStatus,
    SessionStep,
    TaskConfig,
    TestFeedback,
    ToolResult,
)


class FakeCredentialManager:
    status_value = "configured"

    def status(self) -> str:
        return type(self).status_value


class FakeLLMBackend:
    pass


class FakeConfigurationManager:
    def load(self, cli_overrides=None) -> RuntimeConfig:
        return RuntimeConfig()


class FakeSessionManager:
    calls: list[dict] = []

    def __init__(self, config: RuntimeConfig, llm_backend) -> None:
        self.config = config
        self.llm_backend = llm_backend

    def run(self, task_config: TaskConfig, keep_session: bool = False) -> Session:
        type(self).calls.append({"task_config": task_config, "keep_session": keep_session})
        context = ContextPayload(
            system_prompt="system",
            task_description=task_config.description,
            step_id=0,
            blocked_count=0,
            remaining_steps=1,
        )
        return Session(
            session_id="session-123",
            task_config=task_config,
            workspace_root=Path(task_config.workspace_template),
            llm_backend="FakeLLMBackend",
            final_status=SessionStatus.SUCCESS,
            steps=[
                SessionStep(
                    step_id=0,
                    llm_request=context,
                    llm_response='{"tool":"run_tests","params":{}}',
                    parsed_action=ParsedAction(tool="run_tests", params={}),
                    tool_result=ToolResult(tool="run_tests", success=True, data={"exit_code": 0}),
                    test_feedback=TestFeedback(
                        exit_code=0,
                        passed_count=1,
                        failed_count=0,
                        skipped_count=0,
                        duration_ms=12,
                        status="passed",
                    ),
                ),
                SessionStep(
                    step_id=1,
                    llm_request=context,
                    llm_response='{"tool":"read_file","params":{"path":".env"}}',
                    parsed_action=ParsedAction(tool="read_file", params={"path": ".env"}),
                    guardrail_result=GuardrailEvent(
                        reason="sensitive_file_access",
                        tool="read_file",
                        action_summary="read_file .env",
                        recoverable=True,
                        suggestion="Use a non-sensitive file.",
                    ),
                ),
            ],
        )


def fake_create_llm_backend(config, credential_manager, **kwargs):
    fake_create_llm_backend.calls.append({"config": config, "credential_manager": credential_manager, **kwargs})
    return FakeLLMBackend()


fake_create_llm_backend.calls = []


def write_demo(root: Path, demo_id: str, *, order: int = 1) -> Path:
    demo_dir = root / demo_id
    demo_dir.mkdir(parents=True, exist_ok=True)
    (demo_dir / "task.yaml").write_text(
        "\n".join(
            [
                f"id: {demo_id}",
                f"title: {demo_id.title()} Demo",
                "task_type: fix_bug",
                f"description: Description for {demo_id}",
                "workspace_template: .",
                "test_command: pytest",
                "demo_visible: true",
                f"demo_order: {order}",
            ]
        ),
        encoding="utf-8",
    )
    return demo_dir


def setup_webui(monkeypatch, tmp_path: Path) -> TestClient:
    demo_root = tmp_path / "demos"
    write_demo(demo_root, "beta", order=2)
    write_demo(demo_root, "alpha", order=1)
    webui_module.SESSIONS.clear()
    FakeCredentialManager.status_value = "configured"
    FakeSessionManager.calls = []
    fake_create_llm_backend.calls = []
    monkeypatch.setattr(webui_module, "DEMO_ROOT", demo_root)
    monkeypatch.setattr(webui_module, "CredentialManager", FakeCredentialManager)
    monkeypatch.setattr(webui_module, "ConfigurationManager", FakeConfigurationManager)
    monkeypatch.setattr(webui_module, "SessionManager", FakeSessionManager)
    monkeypatch.setattr(webui_module, "create_llm_backend", fake_create_llm_backend)
    return TestClient(app)


def test_imports_app():
    assert app is webui_module.app


def test_index_returns_demo_list(tmp_path, monkeypatch):
    client = setup_webui(monkeypatch, tmp_path)

    response = client.get("/")

    assert response.status_code == 200
    assert "alpha" in response.text
    assert "beta" in response.text
    assert "Alpha Demo" in response.text
    assert "Run (Mock)" in response.text
    assert "Run (Real)" in response.text
    assert response.text.index("alpha") < response.text.index("beta")


def test_run_page_returns_200_for_known_demo(tmp_path, monkeypatch):
    client = setup_webui(monkeypatch, tmp_path)

    response = client.get("/run/alpha")

    assert response.status_code == 200
    assert "Alpha Demo" in response.text
    assert "execution-trace" in response.text


def test_run_page_returns_404_for_unknown_demo(tmp_path, monkeypatch):
    client = setup_webui(monkeypatch, tmp_path)

    response = client.get("/run/missing")

    assert response.status_code == 404


def test_api_run_mock_returns_session_payload(tmp_path, monkeypatch):
    client = setup_webui(monkeypatch, tmp_path)

    response = client.post("/api/run/alpha", json={"mode": "mock"})

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "session-123"
    assert data["final_status"] == "success"
    assert data["step_count"] == 2
    assert data["steps"][0]["action"] == "run_tests"
    assert data["steps"][0]["test_status"] == "passed"
    assert data["steps"][1]["guardrail_reason"] == "sensitive_file_access"
    assert fake_create_llm_backend.calls[0]["mock"] is True


def test_api_run_mock_guardrail_block_uses_demo_script():
    webui_module.SESSIONS.clear()
    response = TestClient(app).post("/api/run/guardrail_block", json={"mode": "mock"})

    assert response.status_code == 200
    data = response.json()
    assert data["final_status"] == "terminated_by_guardrail"
    assert [step["action"] for step in data["steps"]] == ["run_shell", "read_file", "read_file"]
    reasons = {step["guardrail_reason"] for step in data["steps"]}
    assert "dangerous_shell_command" in reasons
    assert "sensitive_file_access" in reasons
    assert "path_outside_workspace" in reasons


def test_api_run_mock_fix_bug_uses_demo_script():
    webui_module.SESSIONS.clear()
    response = TestClient(app).post("/api/run/fix_bug", json={"mode": "mock"})

    assert response.status_code == 200
    data = response.json()
    assert data["final_status"] == "success"
    assert [step["action"] for step in data["steps"][:3]] == ["run_tests", "edit_file", "run_tests"]


def test_api_run_mock_complete_function_uses_demo_script():
    webui_module.SESSIONS.clear()
    response = TestClient(app).post("/api/run/complete_function", json={"mode": "mock"})

    assert response.status_code == 200
    data = response.json()
    assert data["final_status"] == "success"
    assert [step["action"] for step in data["steps"][:4]] == [
        "list_files",
        "read_file",
        "edit_file",
        "run_tests",
    ]


def test_api_run_unknown_demo_returns_404(tmp_path, monkeypatch):
    client = setup_webui(monkeypatch, tmp_path)

    response = client.post("/api/run/missing", json={"mode": "mock"})

    assert response.status_code == 404


def test_api_run_invalid_mode_returns_400(tmp_path, monkeypatch):
    client = setup_webui(monkeypatch, tmp_path)

    response = client.post("/api/run/alpha", json={"mode": "invalid"})

    assert response.status_code == 400


def test_api_run_real_without_api_key_returns_actionable_error(tmp_path, monkeypatch):
    client = setup_webui(monkeypatch, tmp_path)
    FakeCredentialManager.status_value = "missing"

    response = client.post("/api/run/alpha", json={"mode": "real"})

    assert response.status_code == 200
    data = response.json()
    assert data["error"]
    assert "safecode auth set" in data["error"]
    assert "super-secret-api-key" not in response.text


def test_api_status_returns_existing_session(tmp_path, monkeypatch):
    client = setup_webui(monkeypatch, tmp_path)
    run_response = client.post("/api/run/alpha", json={"mode": "mock"})
    session_id = run_response.json()["session_id"]

    response = client.get(f"/api/status/{session_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session_id
    assert data["final_status"] == "success"
    assert data["step_count"] == 2
    assert data["steps"]


def test_api_status_unknown_session_returns_404(tmp_path, monkeypatch):
    client = setup_webui(monkeypatch, tmp_path)

    response = client.get("/api/status/missing-session")

    assert response.status_code == 404


def test_session_payload_includes_redacted_parser_error_summary(tmp_path: Path) -> None:
    context = ContextPayload(
        system_prompt="system",
        task_description="task",
        step_id=0,
        blocked_count=0,
        remaining_steps=1,
    )
    raw_response = (
        "I cannot comply. Bearer secret-token-123 sk-abcdefghijklmnopqrstuvwxyz "
        + "x" * 1200
    )
    session = Session(
        session_id="parser-failure",
        task_config=TaskConfig(
            id="task",
            title="Task",
            task_type="fix_bug",
            description="Task",
            workspace_template=str(tmp_path),
            test_command="pytest",
        ),
        workspace_root=tmp_path,
        llm_backend="real",
        steps=[
            SessionStep(
                step_id=0,
                llm_request=context,
                llm_response=raw_response,
                tool_result=ToolResult(tool="action_parser", success=False, error="invalid_json"),
            )
        ],
    )

    payload = webui_module.session_to_payload(session)
    step = payload["steps"][0]

    assert step["parser_error"] == "invalid_json"
    assert "llm_response_summary" in step
    assert len(step["llm_response_summary"]) <= 520
    assert "Bearer secret-token-123" not in step["llm_response_summary"]
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in step["llm_response_summary"]
    assert "[REDACTED]" in step["llm_response_summary"]

