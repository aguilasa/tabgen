"""Tests for user-provided stems (STEM-TASK-01): Demucs is skipped when the
user stems cover every requested instrument, used as a fallback otherwise,
and the stems' content is part of the analysis/tablature cache versions.

Every stage is a fake; a separator that must not run raises when called.
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile
from test_analysis_pipeline import make_fake_beats, make_fake_harmony
from test_tablature_pipeline import failing, make_fakes, write_input

from tabgen.core import pipeline
from tabgen.core.pipeline import (
    PipelineError,
    _fretting_configs,
    analysis_version,
    resolve_tuning,
    run_analysis,
    run_tablature,
    run_transcription,
    tablature_version,
)
from tabgen.core.separation.prepared import (
    MIX_STEM,
    NORMALIZED_DIR,
    prepared_separate,
    stems_tag,
)


def write_stem(path: Path, value: float = 0.0, rate: int = 44100) -> Path:
    """Stereo wav; at 44.1 kHz it is already in the Demucs format (no conversion)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    soundfile.write(str(path), np.full((rate // 10, 2), value, dtype=np.float32), rate)
    return path


def recording_transcribe(fake, seen: list[tuple[str, str]]):
    def transcribe(input_path, instrument="guitar", on_progress=pipeline.null_progress):
        seen.append((instrument, str(input_path)))
        return fake(input_path, instrument=instrument, on_progress=on_progress)

    return transcribe


def test_full_cover_never_calls_demucs_and_uses_the_user_stem(tmp_path):
    write_input(tmp_path)
    stem = write_stem(tmp_path / "moises" / "lead.wav")
    calls: list[str] = []
    _, analysis, transcribe = make_fakes(tmp_path, calls)
    seen: list[tuple[str, str]] = []
    summary = run_tablature(
        tmp_path / "song.wav",
        output_path=tmp_path / "out.gp5",
        instruments=("guitar",),
        user_stems={"guitar": stem},
        separate_fn=failing("Demucs"),
        analysis_fn=analysis,
        transcribe_fn=recording_transcribe(transcribe, seen),
    )
    assert seen == [("guitar", str(stem.resolve()))]
    assert [s.instrument for s in summary.scores] == ["guitar"]
    assert (tmp_path / "out.gp5").is_file()


def test_partial_cover_runs_fallback_once_and_overrides_its_stem(tmp_path):
    write_input(tmp_path)
    stem = write_stem(tmp_path / "moises" / "rhythm.wav")
    calls: list[str] = []
    separate, analysis, transcribe = make_fakes(tmp_path, calls)
    seen: list[tuple[str, str]] = []
    run_tablature(
        tmp_path / "song.wav",
        output_path=tmp_path / "out.gp5",
        instruments=("guitar", "bass"),
        user_stems={"guitar": stem},
        separate_fn=separate,
        analysis_fn=analysis,
        transcribe_fn=recording_transcribe(transcribe, seen),
    )
    assert calls.count("separate") == 1
    assert dict(seen)["guitar"] == str(stem.resolve())
    assert dict(seen)["bass"] == str(tmp_path / "stems" / "bass.wav")


def test_analysis_with_user_stems_skips_demucs_and_adds_the_mix(tmp_path):
    song = write_input(tmp_path)
    stem = write_stem(tmp_path / "moises" / "lead.wav")
    beats_calls: list[Path] = []
    harmony_calls: list[dict[str, str]] = []
    run_analysis(
        song,
        user_stems={"guitar": stem},
        separate_fn=failing("Demucs"),
        beats_fn=make_fake_beats(beats_calls),
        harmony_fn=make_fake_harmony(harmony_calls),
    )
    assert beats_calls == [song]
    assert harmony_calls == [{"guitar": str(stem.resolve()), MIX_STEM: str(song)}]


def test_no_separate_style_input_is_not_added_twice(tmp_path):
    stem = write_stem(tmp_path / "lead.wav")
    sep = prepared_separate({"guitar": stem.resolve()}, ("guitar",))
    result, hit = sep(stem)
    assert hit is True
    assert result.stems == {"guitar": str(stem.resolve())}


def test_transcription_with_user_stems_skips_demucs(tmp_path):
    song = write_input(tmp_path)
    stem = write_stem(tmp_path / "moises" / "bass.wav")
    calls: list[str] = []
    _, _, transcribe = make_fakes(tmp_path, calls)
    seen: list[tuple[str, str]] = []
    summary = run_transcription(
        song,
        instruments=("bass",),
        user_stems={"bass": stem},
        separate_fn=failing("Demucs"),
        transcribe_fn=recording_transcribe(transcribe, seen),
        export_fn=lambda *a, **k: None,
    )
    assert seen == [("bass", str(stem.resolve()))]
    assert summary.instruments[0].instrument == "bass"


def test_different_stem_content_changes_the_tablature_cache_key(tmp_path):
    write_input(tmp_path)
    stem = write_stem(tmp_path / "moises" / "lead.wav", 0.0)
    calls: list[str] = []
    _, analysis, transcribe = make_fakes(tmp_path, calls)
    kwargs = dict(
        output_path=tmp_path / "out.gp5",
        instruments=("guitar",),
        user_stems={"guitar": stem},
        separate_fn=failing("Demucs"),
        analysis_fn=analysis,
        transcribe_fn=transcribe,
    )
    first = run_tablature(tmp_path / "song.wav", **kwargs)
    again = run_tablature(tmp_path / "song.wav", **kwargs)
    write_stem(stem, 0.25)  # same path, new content
    changed = run_tablature(tmp_path / "song.wav", **kwargs)
    assert (first.cache_hit, again.cache_hit, changed.cache_hit) == (False, True, False)
    names = sorted(p.name for p in (tmp_path / ".tabgen").glob("tablature-*.json"))
    assert len(names) == 2
    assert all(len(n) <= 255 for n in names)


def test_stems_tag_depends_on_content_and_on_demucs_use(tmp_path):
    a = write_stem(tmp_path / "a.wav", 0.0)
    b = write_stem(tmp_path / "b.wav", 0.5)
    assert stems_tag({"guitar": a}, False) != stems_tag({"guitar": b}, False)
    assert stems_tag({"guitar": a}, False) != stems_tag({"guitar": a}, True)
    assert stems_tag({"guitar": a}, False).startswith("stems-")


def test_versions_without_user_stems_are_unchanged():
    """Pinned from the HEAD before this cycle (3d5afb2): old caches stay valid."""
    configs = _fretting_configs(
        ("guitar", "bass"),
        {
            "guitar": resolve_tuning(None, "guitar"),
            "bass": resolve_tuning(None, "bass"),
        },
        {},
        "electric",
    )
    assert analysis_version() == "madmom-0.17.dev0+htdemucs_ft+htdemucs_6s+contract-2"
    assert tablature_version(configs, transcriber="basic-pitch") == (
        "tab-3+rev-3+madmom-0.17.dev0+htdemucs_ft+htdemucs_6s+contract-2"
        "+basic-pitch-icassp2022-onnx+note-2+params-63129f88ad3c+gtype-electric"
        "+tech-d5922bc07095"
    )


def test_missing_stem_file_raises(tmp_path):
    write_input(tmp_path)
    with pytest.raises(PipelineError, match="stem file not found"):
        run_tablature(
            tmp_path / "song.wav",
            instruments=("guitar",),
            user_stems={"guitar": tmp_path / "nope.wav"},
            separate_fn=failing("Demucs"),
        )


def test_unknown_stem_instrument_raises(tmp_path):
    write_input(tmp_path)
    stem = write_stem(tmp_path / "d.wav")
    with pytest.raises(PipelineError, match="unsupported stem instrument 'drums'"):
        run_tablature(
            tmp_path / "song.wav",
            instruments=("guitar",),
            user_stems={"drums": stem},
            separate_fn=failing("Demucs"),
        )


def test_mix_and_stems_at_other_rates_are_brought_to_44100(tmp_path):
    """FIX-STEM-001: a 48 kHz mix with a 44.1 kHz stem used to raise HarmonyError."""
    song = write_stem(tmp_path / "song.wav", 0.1, rate=48000)
    stem = write_stem(tmp_path / "moises" / "lead.wav", 0.2, rate=22050)
    harmony_calls: list[dict[str, str]] = []
    run_analysis(
        song,
        user_stems={"guitar": stem},
        separate_fn=failing("Demucs"),
        beats_fn=make_fake_beats([]),
        harmony_fn=make_fake_harmony(harmony_calls),
    )
    (stems,) = harmony_calls
    assert set(stems) == {"guitar", MIX_STEM}
    for path in stems.values():
        info = soundfile.info(path)
        assert (info.samplerate, info.channels) == (44100, 2)
        assert Path(path).parent == tmp_path / ".tabgen" / NORMALIZED_DIR
    # the real harmony summing accepts them now
    from tabgen.core.analysis.harmony import sum_harmonic_stems

    _, rate = sum_harmonic_stems(stems)
    assert rate == 44100


def test_compressed_mix_is_decoded_with_ffmpeg(tmp_path):
    import subprocess

    song = tmp_path / "song.m4a"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
         "sine=f=440:d=1:sample_rate=48000", "-ac", "2", str(song)],
        check=True,
    )
    stem = write_stem(tmp_path / "lead.wav", 0.2)
    sep = prepared_separate({"guitar": stem.resolve()}, ("guitar",))
    result, _ = sep(song)
    assert soundfile.info(result.stems[MIX_STEM]).samplerate == 44100
    assert result.stems["guitar"] == str(stem.resolve())  # already in format


def test_unreadable_stem_raises_pipeline_error(tmp_path):
    write_input(tmp_path)
    bad = tmp_path / "bad.wav"
    bad.write_bytes(b"not audio")
    with pytest.raises(PipelineError, match="cannot decode"):
        run_analysis(
            tmp_path / "song.wav",
            user_stems={"guitar": bad},
            separate_fn=failing("Demucs"),
            beats_fn=make_fake_beats([]),
            harmony_fn=make_fake_harmony([]),
        )
