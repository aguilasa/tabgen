"""Unit tests for the separation stage with a mocked Demucs model.

No GPU, no model download: a fake separator factory stands in for
``demucs.api.Separator``. Only ffmpeg (input conversion) really runs.
"""

from pathlib import Path

import numpy as np
import soundfile
import torch

from tabgen.core.separation import demucs as demucs_core

SR = 44100


class FakeSeparator:
    """Mimics the demucs.api.Separator surface used by the wrapper."""

    def __init__(self, sources: dict[str, float]) -> None:
        self.samplerate = SR
        self._sources = sources

    def separate_audio_file(self, file: Path):
        origin = torch.zeros(2, SR)
        stems = {
            name: torch.full((2, SR), value) for name, value in self._sources.items()
        }
        return origin, stems


def make_factory(calls: list[str]):
    """A separator factory that records which models were instantiated."""

    def factory(model: str, device: str, segment: int, callback):
        calls.append(model)
        if model == demucs_core.MODEL_FT:
            # htdemucs_ft sources, each filled with a distinct constant.
            return FakeSeparator(
                {"vocals": 0.1, "drums": 0.2, "bass": 0.3, "other": 0.4}
            )
        if model == demucs_core.MODEL_6S:
            # htdemucs_6s adds guitar and piano on top of the base sources.
            return FakeSeparator(
                {
                    "vocals": 0.9,
                    "drums": 0.9,
                    "bass": 0.9,
                    "other": 0.9,
                    "guitar": 0.5,
                    "piano": 0.6,
                }
            )
        raise AssertionError(f"unexpected model {model}")

    return factory


def write_sample(path: Path) -> Path:
    """Write a one-second stereo wav test input."""
    tone = np.zeros((SR, 2), dtype=np.float32)
    soundfile.write(str(path), tone, SR)
    return path


def test_merge_ft_and_6s_into_five_stems(tmp_path: Path) -> None:
    sample = write_sample(tmp_path / "song.wav")
    calls: list[str] = []

    result, cache_hit = demucs_core.separate(
        sample, device="cpu", separator_factory=make_factory(calls)
    )

    assert not cache_hit
    assert calls == [demucs_core.MODEL_FT, demucs_core.MODEL_6S]
    assert set(result.stems) == {"vocals", "drums", "bass", "other", "guitar"}
    assert result.sample_rate == SR
    assert result.model_version == demucs_core.MODEL_VERSION

    stems_dir = tmp_path / "stems"
    for name, path in result.stems.items():
        assert Path(path).parent == stems_dir
        assert Path(path).is_file()

    # Provenance: vocals must come from htdemucs_ft (0.1), guitar from
    # htdemucs_6s (0.5) — not from the other model's conflicting output.
    vocals, _ = soundfile.read(result.stems["vocals"])
    guitar, _ = soundfile.read(result.stems["guitar"])
    assert abs(float(vocals.mean()) - 0.1) < 0.01
    assert abs(float(guitar.mean()) - 0.5) < 0.01
    # piano from htdemucs_6s is dropped from the merged result.
    assert not (stems_dir / "piano.wav").exists()


def test_second_run_is_a_cache_hit_without_recompute(tmp_path: Path) -> None:
    sample = write_sample(tmp_path / "song.wav")
    calls: list[str] = []
    factory = make_factory(calls)

    first, first_hit = demucs_core.separate(
        sample, device="cpu", separator_factory=factory
    )
    assert not first_hit
    assert len(calls) == 2

    progress: list[float] = []
    second, second_hit = demucs_core.separate(
        sample,
        device="cpu",
        separator_factory=factory,
        on_progress=lambda stage, pct: progress.append(pct),
    )

    assert second_hit
    assert len(calls) == 2  # no new model instantiation on the cache hit
    assert second == first
    assert progress == [100.0]


def test_missing_stem_file_invalidates_the_cache(tmp_path: Path) -> None:
    sample = write_sample(tmp_path / "song.wav")
    calls: list[str] = []
    factory = make_factory(calls)

    result, _ = demucs_core.separate(sample, device="cpu", separator_factory=factory)
    Path(result.stems["guitar"]).unlink()

    _, cache_hit = demucs_core.separate(
        sample, device="cpu", separator_factory=factory
    )
    assert not cache_hit
    assert len(calls) == 4  # both models ran again
    assert Path(result.stems["guitar"]).is_file()


def test_progress_reaches_100_and_stays_in_range(tmp_path: Path) -> None:
    sample = write_sample(tmp_path / "song.wav")
    progress: list[float] = []

    demucs_core.separate(
        sample,
        device="cpu",
        separator_factory=make_factory([]),
        on_progress=lambda stage, pct: progress.append(pct),
    )

    assert progress[-1] == 100.0
    assert all(0.0 <= pct <= 100.0 for pct in progress)
