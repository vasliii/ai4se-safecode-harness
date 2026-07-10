from pathlib import Path

import yaml


CI_CONFIG = Path(".gitlab-ci.yml")


def load_ci_config():
    assert CI_CONFIG.exists(), ".gitlab-ci.yml must exist"
    return yaml.safe_load(CI_CONFIG.read_text(encoding="utf-8"))


def flatten_commands(commands):
    if isinstance(commands, str):
        return commands
    return "\n".join(commands)


def test_gitlab_ci_defines_unit_test_job():
    config = load_ci_config()

    assert "unit-test" in config
    job = config["unit-test"]

    assert job["image"] in {"python:3.10", "python:3.11"}
    assert "test" in config.get("stages", [])
    assert job["stage"] == "test"

    before_script = flatten_commands(job.get("before_script", []))
    script = flatten_commands(job.get("script", []))

    assert "pip install -e .[dev]" in before_script
    assert "pytest --cov=safecode --cov-report=term" in script
    assert "--cov-fail-under=80" in script

    artifacts = job.get("artifacts", {})
    assert "coverage.xml" in artifacts.get("paths", [])
    assert "reports" in artifacts
    assert artifacts["reports"].get("junit") == "junit.xml"
    assert artifacts["reports"].get("coverage_report", {}).get("coverage_format") == "cobertura"
    assert artifacts["reports"].get("coverage_report", {}).get("path") == "coverage.xml"
