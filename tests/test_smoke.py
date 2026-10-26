"""Smoke tests for the tabgen package and CLI skeleton."""

from typer.testing import CliRunner

import tabgen
from tabgen.cli.main import app

runner = CliRunner()


def test_package_has_version() -> None:
    assert tabgen.__version__ == "0.1.0"


def test_cli_version_option() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "tabgen 0.1.0" in result.output
