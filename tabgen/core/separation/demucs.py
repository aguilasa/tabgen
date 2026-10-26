"""Source separation built on the Demucs Python API (adefossez's fork).

Two pretrained models are run and their outputs merged into a single
:class:`~tabgen.core.models.SeparationResult`:

- ``htdemucs_ft`` (fine-tuned, bag of 4) provides vocals/drums/bass/other;
- ``htdemucs_6s`` (6 sources) provides the dedicated guitar stem.

Stems are written as wav files into a ``stems/`` directory next to the
input audio, and the result is cached through :class:`StageCache` so a
second run on the same file skips Demucs entirely.

This module is pure core: no print/typer/rich. Progress is reported
through the :data:`~tabgen.core.pipeline.ProgressCallback` contract.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Protocol

import soundfile

from tabgen.core.cache import StageCache
from tabgen.core.models import SeparationResult
from tabgen.core.pipeline import ProgressCallback, null_progress

STAGE = "separation"
MODEL_FT = "htdemucs_ft"
MODEL_6S = "htdemucs_6s"
MODEL_VERSION = f"{MODEL_FT}+{MODEL_6S}"
# Stems taken from each model when merging the two outputs.
FT_STEMS = ("vocals", "drums", "bass", "other")
SIX_STEMS = ("guitar",)
STEM_NAMES = FT_STEMS + SIX_STEMS
# Segment length in seconds fed to Demucs. htdemucs transformers are trained
# on 7.8 s segments (the hard upper bound); 7 s keeps htdemucs_ft inside the
# ~6 GB VRAM of smaller laptop GPUs.
DEFAULT_SEGMENT = 7
TARGET_SAMPLE_RATE = 44100
# Progress share of each phase: htdemucs_ft is a bag of 4 submodels, so it
# gets 4/5 of the bar; htdemucs_6s (single model) gets the remaining 1/5.
_FT_SPAN = 80.0
_6S_SPAN = 20.0


class SeparatorLike(Protocol):
    """The slice of ``demucs.api.Separator`` this module relies on."""

    samplerate: int

    def separate_audio_file(self, file: Path) -> tuple[Any, dict[str, Any]]: ...


# Builds a separator for (model_name, device, segment, demucs_callback).
SeparatorFactory = Callable[[str, str, int, Callable[[dict], None]], SeparatorLike]


class SeparationError(RuntimeError):
    """Raised when conversion or separation fails."""


def default_device() -> str:
    """Return "cuda" when a CUDA device is available, else "cpu"."""
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def convert_to_wav(
    input_path: Path,
    output_path: Path,
    sample_rate: int = TARGET_SAMPLE_RATE,
) -> Path:
    """Convert any ffmpeg-readable audio (mp3/flac/wav/...) to stereo wav."""
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-ar",
        str(sample_rate),
        "-ac",
        "2",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SeparationError(
            f"ffmpeg failed to convert {input_path}: {proc.stderr.strip()}"
        )
    return output_path


def _default_separator_factory(
    model: str,
    device: str,
    segment: int,
    callback: Callable[[dict], None],
) -> SeparatorLike:
    """Build a real ``demucs.api.Separator`` (imported lazily: it is heavy)."""
    from demucs.api import Separator

    return Separator(
        model=model,
        device=device,
        segment=segment,
        callback=callback,
    )


def _demucs_progress_adapter(
    on_progress: ProgressCallback, base: float, span: float
) -> Callable[[dict], None]:
    """Map Demucs chunk callbacks onto on_progress(STAGE, pct in base..base+span)."""

    def callback(info: dict) -> None:
        try:
            models = max(int(info.get("models", 1)), 1)
            length = max(int(info.get("audio_length", 1)), 1)
            offset = float(info.get("segment_offset", 0))
            idx = int(info.get("model_idx_in_bag", 0))
            fraction = min((idx + min(offset / length, 1.0)) / models, 1.0)
            on_progress(STAGE, base + span * fraction)
        except Exception:  # noqa: BLE001 - progress must never abort separation
            pass

    return callback


def _to_numpy(wave: Any) -> Any:
    """Convert a torch tensor (or array-like) to a numpy array on the CPU."""
    if hasattr(wave, "detach"):
        wave = wave.detach()
    if hasattr(wave, "cpu"):
        wave = wave.cpu()
    if hasattr(wave, "numpy"):
        wave = wave.numpy()
    return wave


def _write_stem(path: Path, wave: Any, sample_rate: int) -> None:
    """Write one (channels, frames) wave as a wav file."""
    data = _to_numpy(wave)
    soundfile.write(str(path), data.T, sample_rate, subtype="PCM_16")


def _compute_stems(
    input_path: Path,
    stems_dir: Path,
    device: str,
    segment: int,
    on_progress: ProgressCallback,
    separator_factory: SeparatorFactory,
) -> SeparationResult:
    """Run both Demucs models and write the merged stems to stems_dir."""
    stems_dir.mkdir(parents=True, exist_ok=True)
    stem_paths: dict[str, str] = {}
    sample_rate = TARGET_SAMPLE_RATE

    with tempfile.TemporaryDirectory(prefix="tabgen-separation-") as tmp:
        wav_path = Path(tmp) / "input.wav"
        convert_to_wav(input_path, wav_path)
        on_progress(STAGE, 0.0)

        phases = (
            (MODEL_FT, FT_STEMS, 0.0, _FT_SPAN),
            (MODEL_6S, SIX_STEMS, _FT_SPAN, _6S_SPAN),
        )
        for model_name, wanted, base, span in phases:
            separator = separator_factory(
                model_name,
                device,
                segment,
                _demucs_progress_adapter(on_progress, base, span),
            )
            _, separated = separator.separate_audio_file(wav_path)
            sample_rate = int(separator.samplerate)
            missing = [name for name in wanted if name not in separated]
            if missing:
                raise SeparationError(
                    f"{model_name} did not return expected stems: {missing}"
                )
            for name in wanted:
                stem_path = stems_dir / f"{name}.wav"
                _write_stem(stem_path, separated[name], sample_rate)
                stem_paths[name] = str(stem_path)
            on_progress(STAGE, base + span)

    on_progress(STAGE, 100.0)
    return SeparationResult(
        stems=stem_paths,
        sample_rate=sample_rate,
        model_version=MODEL_VERSION,
    )


# Payload key holding each stem file's identity at cache-write time. The
# stems/ directory is shared by every input in the folder, so a later run on
# another song overwrites the files; existence alone cannot prove the stems
# on disk are still the ones this entry was cached for.
_STEM_IDENTITY_KEY = "stem_identity"


def _stem_identity(path: Path) -> dict[str, int]:
    """Cheap identity fingerprint (size + mtime) of one stem file."""
    stat = path.stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def _cached_result_is_valid(payload: dict[str, Any]) -> bool:
    """A cached entry is a hit only if every stem file still exists and
    still matches the identity recorded when the entry was written."""
    stems = payload.get("stems", {})
    identities = payload.get(_STEM_IDENTITY_KEY, {})
    if set(stems) != set(STEM_NAMES):
        return False
    for name, path in stems.items():
        stem_path = Path(path)
        if not stem_path.is_file():
            return False
        if identities.get(name) != _stem_identity(stem_path):
            return False
    return True


def separate(
    input_path: str | Path,
    device: str | None = None,
    segment: int = DEFAULT_SEGMENT,
    on_progress: ProgressCallback = null_progress,
    cache: StageCache | None = None,
    separator_factory: SeparatorFactory = _default_separator_factory,
) -> tuple[SeparationResult, bool]:
    """Separate an audio file into guitar/bass/drums/vocals/other stems.

    Returns ``(result, cache_hit)``. Stems land in ``stems/`` next to the
    input file; the JSON result is cached per input hash + model version.
    """
    input_path = Path(input_path)
    if not input_path.is_file():
        raise SeparationError(f"input audio not found: {input_path}")
    if cache is None:
        cache = StageCache(input_path)

    cached = cache.get(STAGE, MODEL_VERSION)
    if cached is not None and _cached_result_is_valid(cached):
        on_progress(STAGE, 100.0)
        data = {k: v for k, v in cached.items() if k != _STEM_IDENTITY_KEY}
        return SeparationResult.from_dict(data), True

    result = _compute_stems(
        input_path=input_path,
        stems_dir=input_path.parent / "stems",
        device=device or default_device(),
        segment=segment,
        on_progress=on_progress,
        separator_factory=separator_factory,
    )
    payload = result.to_dict()
    payload[_STEM_IDENTITY_KEY] = {
        name: _stem_identity(Path(path)) for name, path in result.stems.items()
    }
    cache.put(STAGE, MODEL_VERSION, payload)
    return result, False
