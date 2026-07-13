from safecode.models import RuntimeConfig


def test_runtime_config_defaults():
    config = RuntimeConfig()

    assert config.base_url == "https://njusehub.info/v1"
    assert config.model == "qwen3.7-max"
    assert config.temperature == 0
    assert config.max_iterations == 10
    assert config.timeout_seconds == 300
    assert config.test_command == "pytest"
    assert config.context_budget_chars == 8000
    assert config.guardrail_threshold == 3
    assert config.shell_allowlist == [
        "git diff",
        "git status",
        "python -m py_compile",
        "pip install pytest",
        "python -m pip install pytest",
    ]
