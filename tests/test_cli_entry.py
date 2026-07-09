from typer.testing import CliRunner

from safecode.cli import app


def test_safecode_help_exits_successfully():
    runner = CliRunner()

    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "SafeCode Harness" in result.output
    assert "--help" in result.output
