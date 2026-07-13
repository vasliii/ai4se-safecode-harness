"""Tests for Docker deployment configuration."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "Dockerfile"
DOCKERIGNORE = ROOT / ".dockerignore"
COMPOSE_FILE = ROOT / "docker-compose.yml"
SECRET_VALUE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
]


def dockerfile_text() -> str:
    return DOCKERFILE.read_text(encoding="utf-8")


def test_dockerfile_uses_slim_python_base_and_installs_project_editable():
    text = dockerfile_text()

    assert "FROM python:3.10-slim" in text or "FROM python:3.11-slim" in text or "FROM python:3.12-slim" in text
    assert "pip install -e ." in text
    assert "PIP_NO_CACHE_DIR=1" in text


def test_dockerfile_installs_pytest_for_demo_test_execution():
    text = dockerfile_text()

    assert "pip install -e .[dev]" in text or "pip install pytest" in text


def test_dockerfile_serves_webui_on_expected_host_and_port():
    text = dockerfile_text()

    assert "safecode" in text
    assert "serve" in text
    assert "--host" in text
    assert "0.0.0.0" in text
    assert "--port" in text
    assert "8000" in text
    assert 'EXPOSE 8000' in text


def test_dockerfile_uses_non_root_user():
    text = dockerfile_text()

    assert "useradd" in text or "adduser" in text
    assert re.search(r"^USER\s+(?!root\b)\w+", text, re.MULTILINE)


def test_dockerfile_copies_source_and_demos():
    text = dockerfile_text()

    assert "COPY safecode" in text
    assert (ROOT / "safecode" / "demos").is_dir()


def test_docker_config_does_not_hardcode_api_key_values():
    combined = dockerfile_text()
    if COMPOSE_FILE.exists():
        combined += "\n" + COMPOSE_FILE.read_text(encoding="utf-8")

    for pattern in SECRET_VALUE_PATTERNS:
        assert not pattern.search(combined)
    assert "SAFECODE_API_KEY: " not in combined


def test_dockerignore_does_not_exclude_demo_directory():
    patterns = DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
    normalized = {line.strip().rstrip("/") for line in patterns if line.strip() and not line.strip().startswith("#")}

    assert "safecode/demos" not in normalized
    assert "demos" not in normalized


def test_docker_compose_builds_current_project_and_maps_webui_port():
    assert COMPOSE_FILE.is_file()
    compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    service = compose["services"]["safecode"]

    assert service["build"] == "."
    assert "8000:8000" in service["ports"]
    environment = service.get("environment", [])
    environment_text = "\n".join(environment) if isinstance(environment, list) else "\n".join(environment.keys())
    assert "SAFECODE_API_KEY" in environment_text
    assert "SAFECODE_MODEL" in environment_text
    assert "SAFECODE_BASE_URL" in environment_text
    assert "sk-" not in COMPOSE_FILE.read_text(encoding="utf-8")
