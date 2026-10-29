"""Tests for the NDJSON worker (``python -m tabgen.worker``).

Tablature runs in-process with the injected fake stages of the pipeline
tests (no Demucs, madmom or Basic Pitch); the doctor runs for real in a
subprocess to prove the stdout stream holds only NDJSON lines.
"""

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest
from test_tablature_pipeline import make_fakes, write_input

from tabgen.core import pipeline
from tabgen.core.cache import StageCache
from tabgen.core.models import TECHNIQUE_KINDS, AnalysisResult, SeparationResult
from tabgen.core.separation import demucs
from tabgen.worker import run


def serve(request, stage_fns=None) -> tuple[int, list[dict]]:
    line = request if isinstance(request, str) else json.dumps(request)
    out = io.StringIO()
    code = run(io.StringIO(line + "\n"), out, stage_fns=stage_fns)
    return code, [json.loads(text) for text in out.getvalue().splitlines()]


def fake_stage_fns(tmp_path):
    separate, analysis, transcribe = make_fakes(tmp_path, [])
    return {
        "separate_fn": separate,
        "analysis_fn": analysis,
        "transcribe_fn": transcribe,
    }


def tablature_request(song, output) -> dict:
    return {"cmd": "tablature", "args": {"input": str(song), "output": str(output)}}


def test_tablature_reports_every_stage_and_returns_preview(tmp_path):
    song = write_input(tmp_path)
    code, messages = serve(
        tablature_request(song, tmp_path / "o.gp5"),
        fake_stage_fns(tmp_path),
    )

    assert code == 0
    progress = [m for m in messages if m["type"] == "progress"]
    stages = [*pipeline._tablature_stages(pipeline.TABLATURE_INSTRUMENTS), "export"]
    last_pct = {m["stage"]: m["pct"] for m in progress}
    for stage in stages:
        assert last_pct.get(stage) == 100.0, stage
    result = messages[-1]
    assert result["type"] == "result"
    assert [m["type"] for m in messages[:-1]] == ["progress"] * (len(messages) - 1)
    assert result["format"] == "gp5"
    assert [s["instrument"] for s in result["scores"]] == ["guitar", "bass"]
    assert result["ascii_preview"].strip()
    assert (tmp_path / "o.gp5").is_file()


def test_tablature_maps_tunings_capos_and_format(tmp_path):
    song = write_input(tmp_path)
    code, messages = serve(
        {
            "cmd": "tablature",
            "args": {
                "input": str(song),
                "output": str(tmp_path / "o.txt"),
                "instruments": ["guitar"],
                "tunings": {"guitar": "drop-d"},
                "capos": {"guitar": 2},
                "techniques": False,
            },
        },
        fake_stage_fns(tmp_path),
    )

    assert code == 0
    result = messages[-1]
    assert result["format"] == "ascii"
    (score,) = result["scores"]
    assert score["tuning_midi"] == pipeline.resolve_tuning("drop-d", "guitar")
    assert score["capo_fret"] == 2


def test_tablature_tracks_summarize_each_score(tmp_path):
    song = write_input(tmp_path)
    code, messages = serve(
        {
            "cmd": "tablature",
            "args": {
                "input": str(song),
                "output": str(tmp_path / "o.gp5"),
                "tunings": {"guitar": "drop-d", "bass": "30,35,40,45"},
                "capos": {"guitar": 3},
            },
        },
        fake_stage_fns(tmp_path),
    )

    assert code == 0
    result = messages[-1]
    guitar, bass = result["tracks"]
    assert [guitar["instrument"], bass["instrument"]] == ["guitar", "bass"]
    for track, score in zip(result["tracks"], result["scores"]):
        assert track["note_count"] == len(score["events"])
        assert track["unassigned"] == result["unassigned"].get(score["instrument"], 0)
        assert list(track["techniques"]) == list(TECHNIQUE_KINDS)
    assert guitar["tuning_name"] == "drop-d"
    assert guitar["tuning_notes"] == ["D2", "A2", "D3", "G3", "B3", "E4"]
    assert guitar["capo_fret"] == 3
    assert bass["tuning_name"] == ""
    assert bass["tuning_notes"] == ["F#1", "B1", "E2", "A2"]


def test_transcribe_reports_the_transcriber_per_instrument(tmp_path):
    song = write_input(tmp_path)
    separate, _, transcribe = make_fakes(tmp_path, [])
    stage_fns = {"separate_fn": separate, "transcribe_fn": transcribe}

    code, messages = serve(
        {"cmd": "transcribe", "args": {"input": str(song)}}, stage_fns
    )
    assert code == 0
    by_name = {i["instrument"]: i for i in messages[-1]["instruments"]}
    assert by_name["guitar"]["transcriber"] == pipeline.DEFAULT_TRANSCRIBER
    assert by_name["bass"]["transcriber"] == pipeline.TRANSCRIBER_BASIC_PITCH
    assert all(Path(i["midi_path"]).is_file() for i in by_name.values())

    code, messages = serve(
        {
            "cmd": "transcribe",
            "args": {"input": str(song), "transcriber": "basic-pitch"},
        },
        stage_fns,
    )
    assert code == 0
    assert {i["transcriber"] for i in messages[-1]["instruments"]} == {"basic-pitch"}


def plant_cached_analysis(song: Path) -> dict[str, str]:
    """Valid analysis and separation cache entries for ``song`` (no stage runs)."""
    cache = StageCache(song)
    cache.put(
        pipeline.ANALYSIS_STAGE,
        pipeline.analysis_version(),
        AnalysisResult(tempo_bpm=100.0, key="A minor").to_dict(),
    )
    stems_dir = song.parent / "stems"
    stems_dir.mkdir(exist_ok=True)
    stems = {}
    for name in reversed(demucs.STEM_NAMES):
        path = stems_dir / f"{name}.wav"
        path.write_bytes(name.encode())
        stems[name] = str(path)
    separation = SeparationResult(stems=stems, model_version=demucs.MODEL_VERSION)
    payload = separation.to_dict()
    payload[demucs._STEM_IDENTITY_KEY] = {
        name: demucs._stem_identity(Path(path)) for name, path in stems.items()
    }
    cache.put(demucs.STAGE, demucs.MODEL_VERSION, payload)
    return stems


def test_analyze_adds_the_cached_stems(tmp_path):
    song = write_input(tmp_path)
    stems = plant_cached_analysis(song)

    code, messages = serve({"cmd": "analyze", "args": {"input": str(song)}})

    assert code == 0
    result = messages[-1]
    assert result["analysis_cache_hit"] is True
    assert result["result"]["tempo_bpm"] == 100.0
    assert list(result["stems"]) == list(demucs.STEM_NAMES)
    assert result["stems"] == stems


def test_analyze_drops_stems_that_no_longer_match_the_cache(tmp_path):
    song = write_input(tmp_path)
    stems = plant_cached_analysis(song)
    Path(stems["guitar"]).write_bytes(b"another song's stem")

    code, messages = serve({"cmd": "analyze", "args": {"input": str(song)}})

    assert code == 0
    assert messages[-1]["stems"] == {}


TAB = {"cmd": "tablature", "args": {"input": "x.wav"}}


def with_args(base: dict, **args) -> str:
    return json.dumps({**base, "args": {**base["args"], **args}})


@pytest.mark.parametrize(
    "request_line",
    [
        "not json",
        json.dumps(["doctor"]),
        json.dumps({"cmd": "separate", "args": {}}),
        json.dumps({"cmd": "doctor", "args": [], "extra": 1}),
        json.dumps({"cmd": "doctor", "args": {"verbose": True}}),
        json.dumps({"cmd": "analyze", "args": {}}),
        with_args(TAB, input=3),
        with_args(TAB, capos={"guitar": "2"}),
        with_args(TAB, techniques="yes"),
        with_args({"cmd": "transcribe", "args": {"input": "x.wav"}}, instruments=[]),
    ],
)
def test_invalid_requests_end_with_request_error(request_line):
    code, messages = serve(request_line)

    assert code == 1
    assert messages == [
        {"type": "error", "kind": "RequestError", "message": messages[0]["message"]}
    ]
    assert messages[0]["message"]


def test_core_errors_keep_their_exception_name(tmp_path):
    song = write_input(tmp_path)
    code, messages = serve(
        tablature_request(song, tmp_path / "o.pdf"),
        fake_stage_fns(tmp_path),
    )

    assert code == 1
    assert messages[-1]["type"] == "error"
    assert messages[-1]["kind"] == "PipelineError"


def test_stage_prints_go_to_stderr_not_the_stream(tmp_path, capsys):
    song = write_input(tmp_path)
    separate, analysis, transcribe = make_fakes(tmp_path, [])

    def noisy_analysis(*args, **kwargs):
        print("noise from a stage")
        sys.stdout.write("more noise\n")
        return analysis(*args, **kwargs)

    code, messages = serve(
        tablature_request(song, tmp_path / "o.gp5"),
        {
            "separate_fn": separate,
            "analysis_fn": noisy_analysis,
            "transcribe_fn": transcribe,
        },
    )

    assert code == 0
    assert messages[-1]["type"] == "result"
    captured = capsys.readouterr()
    assert "noise from a stage" in captured.err
    assert "more noise" in captured.err
    assert captured.out == ""


def test_module_doctor_prints_only_ndjson():
    proc = subprocess.run(
        [sys.executable, "-m", "tabgen.worker"],
        input='{"cmd": "doctor", "args": {}}\n',
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    messages = [json.loads(line) for line in lines]
    assert messages[-1]["type"] == "result"
    assert [check["name"] for check in messages[-1]["checks"]]


def test_module_error_exits_one():
    proc = subprocess.run(
        [sys.executable, "-m", "tabgen.worker"],
        input='{"cmd": "nope"}\n',
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert proc.returncode == 1
    (message,) = [json.loads(line) for line in proc.stdout.splitlines()]
    assert message["type"] == "error"
    assert message["kind"] == "RequestError"
