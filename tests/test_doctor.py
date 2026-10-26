"""Tests for the environment doctor (core checks and CLI command)."""

import json
import sys

from typer.testing import CliRunner

from tabgen.cli.main import app
from tabgen.core import doctor

runner = CliRunner()


def _passing_report() -> doctor.DoctorReport:
    names = ["ffmpeg", "python", "torch+cuda", "disk space"]
    return doctor.DoctorReport(
        checks=[
            doctor.CheckResult(name=name, ok=True, essential=True, detail="ok")
            for name in names
        ]
    )


# --- core checks ------------------------------------------------------------


def test_check_ffmpeg_present(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    result = doctor.check_ffmpeg()
    assert result.ok is True
    assert result.data["path"] == "/usr/bin/ffmpeg"


def test_check_ffmpeg_absent(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    result = doctor.check_ffmpeg()
    assert result.ok is False
    assert result.essential is True


def test_check_python_version_rejects_unsupported(monkeypatch):
    monkeypatch.setattr(doctor, "MAX_PYTHON", (3, 9))
    result = doctor.check_python_version()
    assert result.ok is False


def test_check_python_version_accepts_current():
    assert (3, 10) <= sys.version_info[:2] <= (3, 11)
    result = doctor.check_python_version()
    assert result.ok is True


def test_check_torch_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", None)
    result = doctor.check_torch_cuda()
    assert result.ok is False
    assert "not installed" in result.detail


def test_check_disk_space_insufficient(tmp_path):
    result = doctor.check_disk_space(str(tmp_path), required_bytes=2**62)
    assert result.ok is False


def test_check_disk_space_sufficient(tmp_path):
    result = doctor.check_disk_space(str(tmp_path), required_bytes=1)
    assert result.ok is True


def test_report_fails_when_essential_check_fails(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    report = doctor.run_checks()
    assert report.ok is False
    by_name = {check.name: check for check in report.checks}
    assert by_name["ffmpeg"].ok is False


# --- CLI --------------------------------------------------------------------


def test_cli_doctor_exits_1_when_ffmpeg_absent(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "ffmpeg" in result.output


def test_cli_doctor_exits_0_when_all_checks_pass(monkeypatch):
    monkeypatch.setattr(doctor, "run_checks", _passing_report)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0


def test_cli_doctor_json_output(monkeypatch):
    monkeypatch.setattr(doctor, "run_checks", _passing_report)
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert [check["name"] for check in payload["checks"]] == [
        "ffmpeg",
        "python",
        "torch+cuda",
        "disk space",
    ]
