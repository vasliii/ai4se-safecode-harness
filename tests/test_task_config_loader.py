from pathlib import Path

import pytest

from safecode.config import TaskConfigLoader, ValidationError
from safecode.models import TaskConfig


def write_yaml(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "task.yaml"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_valid_minimal_task_yaml(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path,
        """
id: fix-add
title: Fix add
task_type: fix_bug
workspace_template: examples/fix_add
test_command: pytest
""".strip(),
    )

    config = TaskConfigLoader().load(path)

    assert isinstance(config, TaskConfig)
    assert config.id == "fix-add"
    assert config.title == "Fix add"
    assert config.task_type == "fix_bug"
    assert config.description == ""
    assert config.workspace_template == "examples/fix_add"
    assert config.test_command == "pytest"
    assert config.allowed_tools == []


def test_load_valid_full_task_yaml(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path,
        """
id: complete-function
title: Complete function
task_type: complete_function
description: Fill in implementation
workspace_template: examples/complete_function
test_command: pytest tests
max_iterations: 5
timeout_seconds: 120
allowed_files:
  - src/main.py
read_only_files:
  - tests/test_main.py
protected_files:
  - .env
allowed_tools:
  - read_file
  - edit_file
  - run_tests
forbidden_tools:
  - run_shell
forbidden_actions:
  - read_sensitive_file
hints: Read tests first
success_criteria:
  - pytest_exit_code_is_zero
expected_final_files:
  - src/main.py
mock_scenario: complete_function_demo
demo_visible: true
demo_order: 2
expected_trace_events:
  - tests_passed
""".strip(),
    )

    config = TaskConfigLoader().load(path)

    assert config.task_type == "complete_function"
    assert config.description == "Fill in implementation"
    assert config.max_iterations == 5
    assert config.timeout_seconds == 120
    assert config.allowed_files == ["src/main.py"]
    assert config.read_only_files == ["tests/test_main.py"]
    assert config.protected_files == [".env"]
    assert config.allowed_tools == ["read_file", "edit_file", "run_tests"]
    assert config.forbidden_tools == ["run_shell"]
    assert config.forbidden_actions == ["read_sensitive_file"]
    assert config.hints == "Read tests first"
    assert config.success_criteria == ["pytest_exit_code_is_zero"]
    assert config.expected_final_files == ["src/main.py"]
    assert config.mock_scenario == "complete_function_demo"
    assert config.demo_visible is True
    assert config.demo_order == 2
    assert config.expected_trace_events == ["tests_passed"]


def assert_validation_error(path: Path, expected: str) -> None:
    with pytest.raises(ValidationError) as exc_info:
        TaskConfigLoader().load(path)
    assert expected in str(exc_info.value)
    assert any(expected in error for error in exc_info.value.errors)


def test_missing_id_raises_validation_error(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path,
        """
title: Missing id
task_type: fix_bug
workspace_template: examples/fix
test_command: pytest
""".strip(),
    )

    assert_validation_error(path, "Missing required field: id")


def test_missing_workspace_template_raises_validation_error(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path,
        """
id: missing-template
title: Missing template
task_type: fix_bug
test_command: pytest
""".strip(),
    )

    assert_validation_error(path, "Missing required field: workspace_template")


def test_unknown_allowed_tool_raises_validation_error(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path,
        """
id: bad-tool
title: Bad tool
task_type: fix_bug
workspace_template: examples/fix
test_command: pytest
allowed_tools:
  - read_file
  - unknown_tool
""".strip(),
    )

    assert_validation_error(path, "Unknown allowed tool: unknown_tool")


def test_invalid_yaml_raises_validation_error(tmp_path: Path) -> None:
    path = write_yaml(tmp_path, "id: [unterminated")

    with pytest.raises(ValidationError) as exc_info:
        TaskConfigLoader().load(path)

    assert "Invalid YAML" in str(exc_info.value)
    assert exc_info.value.errors


def test_empty_file_raises_validation_error(tmp_path: Path) -> None:
    path = write_yaml(tmp_path, "")

    assert_validation_error(path, "Task config YAML must contain a mapping")


def test_invalid_task_type_raises_validation_error(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path,
        """
id: bad-type
title: Bad type
task_type: refactor
workspace_template: examples/fix
test_command: pytest
""".strip(),
    )

    assert_validation_error(path, "Invalid task_type: refactor")


def test_invalid_max_iterations_raises_validation_error(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path,
        """
id: bad-max
title: Bad max
task_type: fix_bug
workspace_template: examples/fix
test_command: pytest
max_iterations: 0
""".strip(),
    )

    assert_validation_error(path, "max_iterations must be a positive integer")


def test_invalid_timeout_seconds_raises_validation_error(tmp_path: Path) -> None:
    path = write_yaml(
        tmp_path,
        """
id: bad-timeout
title: Bad timeout
task_type: add_feature
workspace_template: examples/feature
test_command: pytest
timeout_seconds: false
""".strip(),
    )

    assert_validation_error(path, "timeout_seconds must be a positive integer")
