"""CLI flags --stem / --no-separate (STEM-TASK-02): parsing and hand-off to
the core as ``user_stems``. The pipeline functions are replaced by fakes
that record their keyword arguments."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from tabgen.cli.main import app
from tabgen.core import pipeline

runner = CliRunner()


class Stop(Exception):
    pass


@pytest.fixture
def recorded(monkeypatch):
    calls: dict[str, dict] = {}

    def fake(name):
        def run(*args, **kwargs):
            calls[name] = kwargs
            raise Stop

        return run

    for name in ("run_tablature", "run_transcription", "run_analysis"):
        monkeypatch.setattr(pipeline, name, fake(name))
    return calls


def files(tmp_path: Path):
    song = tmp_path / "song.wav"
    lead = tmp_path / "lead.wav"
    song.write_bytes(b"x")
    lead.write_bytes(b"y")
    return song, lead


def test_stem_reaches_export_as_user_stems(tmp_path, recorded):
    song, lead = files(tmp_path)
    runner.invoke(app, ["export", str(song), "--stem", f"guitar={lead}",
                        "--instruments", "guitar"])
    assert recorded["run_tablature"]["user_stems"] == {"guitar": lead}


def test_repeated_stem_and_transcribe(tmp_path, recorded):
    song, lead = files(tmp_path)
    runner.invoke(app, ["transcribe", str(song), "--stem", f"guitar={lead}",
                        "--stem", f"bass={song}"])
    assert recorded["run_transcription"]["user_stems"] == {"guitar": lead, "bass": song}


def test_no_separate_uses_the_input_as_the_stem(tmp_path, recorded):
    song, _ = files(tmp_path)
    runner.invoke(
        app, ["export", str(song), "--no-separate", "--instruments", "guitar"]
    )
    assert recorded["run_tablature"]["user_stems"] == {"guitar": song}


def test_no_stem_flags_pass_none(tmp_path, recorded):
    song, _ = files(tmp_path)
    runner.invoke(app, ["analyze", str(song)])
    assert recorded["run_analysis"]["user_stems"] is None


def test_analyze_no_separate(tmp_path, recorded):
    song, _ = files(tmp_path)
    runner.invoke(app, ["analyze", str(song), "--no-separate"])
    assert recorded["run_analysis"]["user_stems"] == {"guitar": song}


@pytest.mark.parametrize("args", [
    ["--stem", "foo=LEAD"],
    ["--stem", "guitar"],
    ["--stem", "guitar=/nope/missing.wav"],
    ["--no-separate", "--instruments", "guitar,bass"],
    ["--no-separate", "--instruments", "guitar", "--stem", "guitar=LEAD"],
])
def test_invalid_stem_options_exit_2(tmp_path, recorded, args):
    song, lead = files(tmp_path)
    args = [a.replace("LEAD", str(lead)) for a in args]
    result = runner.invoke(app, ["export", str(song), *args])
    assert result.exit_code == 2, result.output
    assert "Invalid option" in result.output
    assert "run_tablature" not in recorded
