from pathlib import Path


def test_tmp_workspace_fixture_creates_example_file(tmp_workspace):
    workspace = Path(tmp_workspace)

    assert workspace.exists()
    assert workspace.is_dir()
    assert (workspace / "README.md").read_text(encoding="utf-8")
