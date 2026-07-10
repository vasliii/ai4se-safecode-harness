from pathlib import Path

import pytest

from safecode.models import TaskConfig


def test_task_config_creation_defaults():
    config = TaskConfig(
        id="fix_bug",
        title="Fix bug",
        task_type="fix_bug",
        description="Fix a bug",
        workspace_template="examples/fix_bug",
        test_command="pytest",
    )

    assert config.max_iterations is None
    assert config.timeout_seconds is None
    assert config.allowed_files == []
    assert config.protected_files == []
    assert config.allowed_tools == []
    assert config.demo_visible is False
    assert config.demo_order is None


def test_task_config_from_yaml_loads_valid_file(tmp_path):
    config_path = tmp_path / "task.yaml"
    config_path.write_text(
        """
id: fix_bug
title: Fix bug
task_type: fix_bug
description: Fix a bug
workspace_template: examples/fix_bug
test_command: pytest
max_iterations: 10
allowed_tools:
  - read_file
  - run_tests
demo_visible: true
demo_order: 2
""".strip(),
        encoding="utf-8",
    )

    config = TaskConfig.from_yaml(config_path)

    assert config.id == "fix_bug"
    assert config.max_iterations == 10
    assert config.allowed_tools == ["read_file", "run_tests"]
    assert config.demo_visible is True
    assert config.demo_order == 2


def test_task_config_from_yaml_rejects_missing_required_field(tmp_path):
    config_path = tmp_path / "task.yaml"
    config_path.write_text("id: missing_title\n", encoding="utf-8")

    with pytest.raises(ValueError, match="title"):
        TaskConfig.from_yaml(config_path)
