"""Tests for the analysis pipeline orchestration (run_analysis).

Separation, beats and harmony are injected fakes (no Demucs, no madmom).
The cache tests prove that a second run on the same input is served
entirely from the ``analysis`` cache entry: the injected stage functions
there raise if ever called.
"""

from pathlib import Path

import numpy as np
import pytest
import soundfile

from tabgen.core import pipeline
from tabgen.core.analysis.beats import BeatAnalysis
from tabgen.core.analysis.harmony import HarmonyResult
from tabgen.core.models import AnalysisResult, ChordSegment, SeparationResult
from tabgen.core.pipeline import PipelineError, run_analysis

CHORDS = [
    ChordSegment(start_s=0.0, end_s=2.0, label="A:min"),
    ChordSegment(start_s=2.0, end_s=4.0, label="C:maj"),
]


def write_input(tmp_path: Path, name: str = "song.wav") -> Path:
    """Write a short silent stereo wav as the pipeline input."""
    path = tmp_path / name
    soundfile.write(str(path), np.zeros((4410, 2), dtype=np.float32), 44100)
    return path


def make_fake_separate(tmp_path: Path, calls: list[Path], cache_hit: bool = False):
    """A separate() stand-in that writes stem placeholders and reports pct."""
    stems_dir = tmp_path / "stems"
    stems_dir.mkdir(exist_ok=True)
    stems = {}
    for name in ("guitar", "bass", "drums", "vocals", "other"):
        stem = stems_dir / f"{name}.wav"
        stem.touch()
        stems[name] = str(stem)

    def fake_separate(
        input_path: Path,
        device: str | None = None,
        on_progress: pipeline.ProgressCallback = pipeline.null_progress,
    ):
        calls.append(Path(input_path))
        on_progress("separation", 0.0)
        on_progress("separation", 100.0)
        return SeparationResult(stems=stems, model_version="fake"), cache_hit

    return fake_separate


def make_fake_beats(calls: list[Path]):
    """An analyze_beats() stand-in returning a canned BeatAnalysis."""

    def fake_beats(
        audio_path: Path,
        on_progress: pipeline.ProgressCallback = pipeline.null_progress,
    ) -> BeatAnalysis:
        calls.append(Path(audio_path))
        on_progress("analysis:beats", 0.0)
        on_progress("analysis:beats", 100.0)
        return BeatAnalysis(
            tempo_bpm=120.0,
            beat_times=[0.5, 1.0, 1.5, 2.0],
            downbeat_times=[0.5],
        )

    return fake_beats


def make_fake_harmony(calls: list[dict[str, str]]):
    """An analyze_harmony() stand-in returning a canned HarmonyResult."""

    def fake_harmony(
        stems,
        on_progress: pipeline.ProgressCallback = pipeline.null_progress,
    ) -> HarmonyResult:
        calls.append(dict(stems))
        on_progress("analysis:harmony", 0.0)
        on_progress("analysis:harmony", 100.0)
        return HarmonyResult(key="A minor", key_confidence=0.9, chords=list(CHORDS))

    return fake_harmony


def fail_if_called(*args, **kwargs):
    raise AssertionError("stage function must not be called on a cache hit")


def run_with_fakes(sample: Path, tmp_path: Path, **kwargs):
    return run_analysis(
        sample,
        separate_fn=kwargs.pop("separate_fn", make_fake_separate(tmp_path, [])),
        beats_fn=kwargs.pop("beats_fn", make_fake_beats([])),
        harmony_fn=kwargs.pop("harmony_fn", make_fake_harmony([])),
        **kwargs,
    )


def test_orchestration_merges_beats_and_harmony_into_analysis_result(
    tmp_path: Path,
) -> None:
    sample = write_input(tmp_path)
    separate_calls: list[Path] = []
    beats_calls: list[Path] = []
    harmony_calls: list[dict[str, str]] = []

    summary = run_analysis(
        sample,
        separate_fn=make_fake_separate(tmp_path, separate_calls),
        beats_fn=make_fake_beats(beats_calls),
        harmony_fn=make_fake_harmony(harmony_calls),
    )

    assert separate_calls == [sample]
    # Beats run on the original audio, not on a stem.
    assert beats_calls == [sample]
    # Harmony receives the stems mapping from the separation result.
    (stems,) = harmony_calls
    assert set(stems) == {"guitar", "bass", "drums", "vocals", "other"}

    assert not summary.analysis_cache_hit
    assert not summary.separation_cache_hit
    result = summary.result
    assert result.tempo_bpm == 120.0
    assert result.beat_times == [0.5, 1.0, 1.5, 2.0]
    assert result.downbeat_times == [0.5]
    assert result.key == "A minor"
    assert result.key_confidence == 0.9
    assert result.chords == CHORDS
    # The merged result survives a JSON round trip.
    assert AnalysisResult.from_json(result.to_json()) == result


def test_second_run_hits_analysis_cache_and_calls_no_stage(tmp_path: Path) -> None:
    sample = write_input(tmp_path)

    first = run_with_fakes(sample, tmp_path)
    assert not first.analysis_cache_hit
    assert (tmp_path / ".tabgen").is_dir()

    # Every stage function raises if called: the cache must serve everything.
    second = run_analysis(
        sample,
        separate_fn=fail_if_called,
        beats_fn=fail_if_called,
        harmony_fn=fail_if_called,
    )
    assert second.analysis_cache_hit
    assert second.separation_cache_hit
    assert second.result == first.result


def test_cache_hit_still_reports_every_stage_at_100(tmp_path: Path) -> None:
    sample = write_input(tmp_path)
    run_with_fakes(sample, tmp_path)

    events: list[tuple[str, float]] = []
    run_analysis(
        sample,
        on_progress=lambda stage, pct: events.append((stage, pct)),
        separate_fn=fail_if_called,
        beats_fn=fail_if_called,
        harmony_fn=fail_if_called,
    )
    assert events == [
        ("separation", 100.0),
        ("analysis:beats", 100.0),
        ("analysis:harmony", 100.0),
    ]


def test_changed_input_bytes_invalidate_the_analysis_cache(tmp_path: Path) -> None:
    sample = write_input(tmp_path)
    run_with_fakes(sample, tmp_path)

    # Rewrite the input with different content: the sha256 key changes.
    soundfile.write(str(sample), np.ones((4410, 2), dtype=np.float32) * 0.1, 44100)
    beats_calls: list[Path] = []
    summary = run_with_fakes(sample, tmp_path, beats_fn=make_fake_beats(beats_calls))
    assert not summary.analysis_cache_hit
    assert beats_calls == [sample]


def test_progress_reports_each_stage_in_order_up_to_100(tmp_path: Path) -> None:
    sample = write_input(tmp_path)
    events: list[tuple[str, float]] = []

    run_with_fakes(
        sample,
        tmp_path,
        on_progress=lambda stage, pct: events.append((stage, pct)),
    )

    stages = [stage for stage, _ in events]
    expected_order = ["separation", "analysis:beats", "analysis:harmony"]
    # Every expected stage appears, grouped and in pipeline order.
    assert [s for i, s in enumerate(stages) if i == 0 or stages[i - 1] != s] == (
        expected_order
    )
    # Each stage ends at 100.0 and never leaves [0, 100].
    for name in expected_order:
        stage_pcts = [pct for stage, pct in events if stage == name]
        assert stage_pcts[-1] == 100.0
    assert all(0.0 <= pct <= 100.0 for _, pct in events)


def test_missing_input_raises(tmp_path: Path) -> None:
    with pytest.raises(PipelineError, match="not found"):
        run_analysis(tmp_path / "nope.wav")


def test_analysis_version_pins_madmom_demucs_and_contract() -> None:
    version = pipeline.analysis_version()
    assert version.startswith("madmom-")
    assert "htdemucs_ft+htdemucs_6s" in version
    assert version.endswith(f"contract-{pipeline.ANALYSIS_CONTRACT_REVISION}")
