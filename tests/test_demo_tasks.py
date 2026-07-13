"""Tests for packaged SafeCode demo task definitions."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

import safecode.cli.demo as demo_module
from safecode.cli import app
from safecode.config import TaskConfigLoader
from safecode.core.action_parser import TOOL_SCHEMAS

DEMO_ROOT = Path(__file__).resolve().parents[1] / "safecode" / "demos"
EXPECTED_DEMOS = {
    "guardrail_block": "fix_bug",
    "fix_bug": "fix_bug",
    "complete_function": "complete_function",
}
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"SAFECODE_API_KEY\s*="),
]


def test_demo_directories_and_task_yaml_exist():
    for demo_id in EXPECTED_DEMOS:
        demo_dir = DEMO_ROOT / demo_id
        assert demo_dir.is_dir(), demo_id
        assert (demo_dir / "task.yaml").is_file(), demo_id


def test_demo_task_yamls_load_and_have_valid_fields():
    loader = TaskConfigLoader()

    for demo_id, task_type in EXPECTED_DEMOS.items():
        task_path = DEMO_ROOT / demo_id / "task.yaml"
        task_config = loader.load(task_path)
        workspace_template = Path(task_config.workspace_template)

        assert task_config.id == demo_id
        assert task_config.task_type == task_type
        assert task_config.test_command == "pytest"
        assert task_config.max_iterations is not None and task_config.max_iterations > 0
        resolved_workspace = workspace_template if workspace_template.is_absolute() else task_path.parent / workspace_template
        assert resolved_workspace.exists(), demo_id
        assert resolved_workspace.resolve() == (DEMO_ROOT / demo_id).resolve()
        assert task_config.allowed_tools
        assert all(tool in TOOL_SCHEMAS for tool in task_config.allowed_tools)


def run_demo_pytest(demo_id: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=DEMO_ROOT / demo_id,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_fix_bug_initial_pytest_fails():
    result = run_demo_pytest("fix_bug")

    assert result.returncode != 0
    assert "test_add" in result.stdout


def test_complete_function_initial_pytest_fails():
    result = run_demo_pytest("complete_function")

    assert result.returncode != 0
    assert "test_add" in result.stdout


def test_demo_files_do_not_contain_api_keys_or_private_keys():
    for path in DEMO_ROOT.rglob("*"):
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            assert not pattern.search(text), path
        assert path.name not in {".env", "secrets.json", "id_rsa", "id_rsa.pub"}
        assert path.suffix not in {".key", ".pem"}


def test_demo_list_logic_recognizes_packaged_demos(monkeypatch):
    monkeypatch.setattr(demo_module, "DEMO_ROOT", DEMO_ROOT)

    result = CliRunner().invoke(app, ["demo", "list"])

    assert result.exit_code == 0
    for demo_id in EXPECTED_DEMOS:
        assert demo_id in result.output


