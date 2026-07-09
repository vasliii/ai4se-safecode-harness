from pathlib import Path

import pytest


@pytest.fixture
def tmp_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    readme = workspace / "README.md"
    readme.write_text("Temporary SafeCode workspace for tests.\n", encoding="utf-8")
    return Path(workspace)
