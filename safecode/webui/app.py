"""Lightweight FastAPI WebUI for SafeCode Harness demos."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from safecode.auth import CredentialManager
from safecode.config import ConfigurationManager, TaskConfigLoader
from safecode.core.session_manager import SessionManager
from safecode.demos.mock_actions import get_demo_mock_actions
from safecode.llm import create_llm_backend
from safecode.models import RuntimeConfig, Session, TaskConfig

PACKAGE_ROOT = Path(__file__).resolve().parent
DEMO_ROOT = PACKAGE_ROOT.parent / "demos"
TEMPLATE_ROOT = PACKAGE_ROOT / "templates"
STATIC_ROOT = PACKAGE_ROOT / "static"

app = FastAPI(title="SafeCode Harness")
templates = Jinja2Templates(directory=str(TEMPLATE_ROOT))
app.mount("/static", StaticFiles(directory=str(STATIC_ROOT)), name="static")

SESSIONS: dict[str, dict[str, Any]] = {}
LLM_RESPONSE_SUMMARY_LIMIT = 500
SECRET_PATTERNS = (
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"(?i)(api[_-]?key|token|secret)\s*[=:]\s*[^\s,'\"}]+"),
)


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Render the demo index page."""
    return templates.TemplateResponse(request, "index.html", {"demos": list_demos()})


@app.get("/run/{demo_id}", response_class=HTMLResponse)
def run_page(request: Request, demo_id: str) -> HTMLResponse:
    """Render the run page for a single demo."""
    demo = get_demo(demo_id)
    if demo is None:
        raise HTTPException(status_code=404, detail="Demo not found")
    return templates.TemplateResponse(request, "run.html", {"demo": demo})


@app.post("/api/run/{demo_id}")
async def api_run_demo(demo_id: str, request: Request) -> dict[str, Any]:
    """Run a demo in mock or real mode and return a session summary."""
    demo = get_demo(demo_id)
    if demo is None:
        raise HTTPException(status_code=404, detail="Demo not found")

    payload = await request.json()
    mode = payload.get("mode")
    if mode not in {"mock", "real"}:
        raise HTTPException(status_code=400, detail="mode must be mock or real")

    mock = mode == "mock"
    credential_manager = CredentialManager()
    if not mock and credential_manager.status() == "missing":
        return {
            "session_id": None,
            "final_status": "error",
            "step_count": 0,
            "steps": [],
            "error": "API key missing. Run safecode auth set before using real mode.",
        }

    task_config = _prepare_demo_task_config(demo)
    config = ConfigurationManager().load(cli_overrides={})
    llm_backend = create_llm_backend(
        config,
        credential_manager,
        mock=mock,
        mock_actions=get_demo_mock_actions(demo_id) if mock else None,
    )
    session = SessionManager(config, llm_backend).run(task_config, keep_session=False)
    summary = session_to_payload(session)
    SESSIONS[session.session_id] = summary
    return summary


@app.get("/api/status/{session_id}")
def api_status(session_id: str) -> dict[str, Any]:
    """Return the latest in-memory session status."""
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def list_demos() -> list[dict[str, Any]]:
    """Load visible demos from DEMO_ROOT sorted by demo_order."""
    demos: list[dict[str, Any]] = []
    for task_path in sorted(DEMO_ROOT.glob("*/task.yaml")):
        try:
            task_config = TaskConfigLoader().load(task_path)
        except Exception:
            continue
        demos.append(_demo_payload(task_path.parent.name, task_path, task_config))
    return sorted(demos, key=lambda item: (item.get("demo_order") is None, item.get("demo_order") or 0, item["id"]))


def get_demo(demo_id: str) -> dict[str, Any] | None:
    """Return a demo payload by id."""
    task_path = DEMO_ROOT / demo_id / "task.yaml"
    if not task_path.exists():
        return None
    try:
        task_config = TaskConfigLoader().load(task_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Invalid demo task.yaml: {exc}") from exc
    return _demo_payload(demo_id, task_path, task_config)


def session_to_payload(session: Session) -> dict[str, Any]:
    """Convert a Session to the compact JSON shape used by the WebUI."""
    return {
        "session_id": session.session_id,
        "final_status": _status_value(session.final_status),
        "step_count": len(session.steps),
        "steps": [_step_payload(step) for step in session.steps],
    }


def _demo_payload(demo_id: str, task_path: Path, task_config: TaskConfig) -> dict[str, Any]:
    return {
        "id": demo_id,
        "title": task_config.title,
        "description": task_config.description,
        "task_type": task_config.task_type,
        "demo_order": task_config.demo_order,
        "task_path": task_path,
    }


def _prepare_demo_task_config(demo: dict[str, Any]) -> TaskConfig:
    task_config = TaskConfigLoader().load(demo["task_path"])
    template = Path(task_config.workspace_template)
    if not template.is_absolute():
        task_config.workspace_template = str((demo["task_path"].parent / template).resolve())
    return task_config


def _step_payload(step: Any) -> dict[str, Any]:
    parsed_action = step.parsed_action
    tool_result = step.tool_result
    test_feedback = step.test_feedback
    guardrail = step.guardrail_result
    payload = {
        "step_id": step.step_id,
        "action": parsed_action.tool if parsed_action is not None else None,
        "params": parsed_action.params if parsed_action is not None else None,
        "tool": tool_result.tool if tool_result is not None else None,
        "tool_success": tool_result.success if tool_result is not None else None,
        "test_status": test_feedback.status if test_feedback is not None else None,
        "guardrail_reason": guardrail.reason if guardrail is not None else None,
        "guardrail_summary": guardrail.action_summary if guardrail is not None else None,
    }
    if tool_result is not None and tool_result.tool == "action_parser" and not tool_result.success:
        payload["parser_error"] = tool_result.error
        payload["llm_response_summary"] = _summarize_llm_response(step.llm_response)
    return payload


def _status_value(status: object) -> str:
    return status.value if hasattr(status, "value") else str(status)


def _summarize_llm_response(response: str | None) -> str:
    if not response:
        return ""
    redacted = response
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    if len(redacted) <= LLM_RESPONSE_SUMMARY_LIMIT:
        return redacted
    return redacted[:LLM_RESPONSE_SUMMARY_LIMIT].rstrip() + "\n[truncated]"

