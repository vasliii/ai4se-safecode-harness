"""Tests for Render deployment configuration."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RENDER_YAML = ROOT / "render.yaml"
PROCFILE = ROOT / "Procfile"
SECRET_VALUE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----"),
    re.compile(r"SAFECODE_API_KEY\s*[:=]\s*['\"]?[^\s'\"${]+"),
]


def load_render_config() -> dict:
    return yaml.safe_load(RENDER_YAML.read_text(encoding="utf-8"))


def service_config() -> dict:
    config = load_render_config()
    services = config.get("services", [])
    assert services, "render.yaml must define at least one service"
    return services[0]


def test_render_yaml_exists():
    assert RENDER_YAML.is_file()


def test_procfile_exists():
    assert PROCFILE.is_file()


def test_render_yaml_defines_docker_web_service():
    service = service_config()

    assert service["type"] == "web"
    assert service.get("runtime") == "docker" or service.get("env") == "docker"
    assert service.get("dockerfilePath") in {"./Dockerfile", "Dockerfile"}


def test_render_yaml_health_check_path_is_root():
    service = service_config()

    assert service.get("healthCheckPath") == "/"


def test_render_yaml_declares_expected_environment_variables_without_secrets():
    service = service_config()
    env_vars = service.get("envVars", [])
    by_key = {item["key"]: item for item in env_vars}

    assert "SAFECODE_API_KEY" in by_key
    assert by_key["SAFECODE_API_KEY"].get("sync") is False
    assert "value" not in by_key["SAFECODE_API_KEY"]
    assert "SAFECODE_BASE_URL" in by_key
    assert "SAFECODE_MODEL" in by_key

    render_text = RENDER_YAML.read_text(encoding="utf-8")
    for pattern in SECRET_VALUE_PATTERNS:
        assert not pattern.search(render_text)


def test_procfile_starts_safecode_webui_on_render_port():
    content = PROCFILE.read_text(encoding="utf-8")

    assert content.startswith("web:")
    assert "safecode serve" in content
    assert "--host 0.0.0.0" in content
    assert "--port" in content
    assert "PORT" in content
    assert "8000" in content


def test_procfile_does_not_contain_secret_values():
    content = PROCFILE.read_text(encoding="utf-8")

    for pattern in SECRET_VALUE_PATTERNS:
        assert not pattern.search(content)
