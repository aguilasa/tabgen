"""Mix mode of the evaluation harness: guitar clip + drums/bass backing.

The clean subsets (GuitarSet mono mic, EGDB DI) are guitar-only. In tabgen
the transcriber sees a Demucs ``guitar`` stem instead, with leakage and
separation artifacts. This module rebuilds that condition per clip:

1. **Backing.** Drums + bass of one MUSDB18 track, from the 7-second
   excerpts of MUSDB18 (Rafii et al., Zenodo record 3270814,
   ``MUSDB18-7-STEMS.zip``, CC BY 4.0 per the record; nothing of it is
   versioned here). Only the 50
   ``test/`` tracks are used (held out from Demucs training). Stream order
   inside each ``.stem.mp4``: 0 mix, 1 drums, 2 bass, 3 other, 4 vocals.
   The track for clip ``i`` of the subset is ``sorted(test tracks)[i % 50]``.
2. **Mix.** The stereo backing (drums + bass) is looped to the clip length
   and scaled so that its RMS is :data:`GUITAR_TO_BACKING_DB` below the
   guitar's RMS (0 dB: equal RMS). The mono guitar goes to both channels.
   If the sum peaks above :data:`PEAK_LIMIT`, the whole mix is scaled down
   (one gain, so the ratio is kept). Written as 16-bit 44.1 kHz stereo wav.
3. **Separation.** ``tabgen.core.separation.demucs.separate`` (the same
   stage as ``tabgen export``) on the mix; the ``guitar`` stem goes to the
   transcriber.

Everything generated (extracted backings, mixes, stems, stage caches) lives
outside the repository, under ``--mix-dir`` (default
``$TABGEN_DATASETS/mixed``, else ``~/datasets/tabgen/mixed``):
``backing/<track>.wav`` and ``<dataset>/<track id>/mix.wav`` (+ ``stems/``
and ``.tabgen/`` next to it, written by the separation stage).
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile

SAMPLE_RATE = 44100
# Guitar RMS minus backing RMS, in dB (0 = guitar as loud as drums + bass).
GUITAR_TO_BACKING_DB = 0.0
PEAK_LIMIT = 0.99
# MUSDB18 .stem.mp4 audio streams (0 mix, 1 drums, 2 bass, 3 other, 4 vocals).
DRUMS_STREAM = 1
BASS_STREAM = 2
BACKING_SOURCE = (
    "MUSDB18 7-second excerpts (Zenodo record 3270814, MUSDB18-7-STEMS.zip), "
    "test/ tracks only, drums + bass streams"
)


def _datasets_root() -> Path:
    root = os.environ.get("TABGEN_DATASETS")
    return Path(root) if root else Path.home() / "datasets" / "tabgen"


def default_musdb_dir() -> Path:
    """Unzipped MUSDB18-7: ``<dir>/test/*.stem.mp4``."""
    return _datasets_root() / "musdb18-7" / "raw"


def default_mix_dir() -> Path:
    return _datasets_root() / "mixed"


def backing_tracks(musdb_dir: Path) -> list[Path]:
    """The MUSDB18 test tracks, sorted by file name (the selection order)."""
    tracks = sorted((musdb_dir / "test").glob("*.stem.mp4"), key=lambda p: p.name)
    if not tracks:
        raise FileNotFoundError(f"no MUSDB18 test tracks under {musdb_dir / 'test'}")
    return tracks


def backing_for(position: int, tracks: list[Path]) -> Path:
    """Backing track of the clip at ``position`` in the subset."""
    return tracks[position % len(tracks)]


def _extract_stream(stem_mp4: Path, stream: int) -> np.ndarray:
    """One audio stream of a .stem.mp4 as float32 (samples, 2) at 44.1 kHz."""
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(stem_mp4), "-map", f"0:a:{stream}",
        "-ac", "2", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-",
    ]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)


def backing_audio(stem_mp4: Path, mix_dir: Path) -> np.ndarray:
    """Drums + bass of one MUSDB18 track, cached as wav under ``mix_dir``."""
    name = stem_mp4.name.removesuffix(".stem.mp4")
    cached = mix_dir / "backing" / f"{name}.wav"
    if not cached.is_file():
        audio = _extract_stream(stem_mp4, DRUMS_STREAM) + _extract_stream(
            stem_mp4, BASS_STREAM
        )
        cached.parent.mkdir(parents=True, exist_ok=True)
        soundfile.write(str(cached), audio, SAMPLE_RATE, subtype="FLOAT")
    audio, rate = soundfile.read(str(cached), dtype="float32", always_2d=True)
    assert rate == SAMPLE_RATE
    return audio


def _rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))


def _guitar_mono(path: Path) -> np.ndarray:
    audio, rate = soundfile.read(str(path), dtype="float32", always_2d=True)
    mono = audio.mean(axis=1)
    if rate != SAMPLE_RATE:
        import librosa

        mono = librosa.resample(mono, orig_sr=rate, target_sr=SAMPLE_RATE)
    return mono.astype(np.float32)


def mix(guitar: np.ndarray, backing: np.ndarray) -> np.ndarray:
    """Guitar (mono) over the looped, level-matched backing (stereo)."""
    reps = int(np.ceil(len(guitar) / len(backing)))
    loop = np.tile(backing, (reps, 1))[: len(guitar)]
    gain = _rms(guitar) / max(_rms(loop.mean(axis=1)), 1e-9)
    gain *= 10 ** (-GUITAR_TO_BACKING_DB / 20)
    out = loop * gain + guitar[:, None]
    peak = float(np.abs(out).max(initial=0.0))
    if peak > PEAK_LIMIT:
        out *= PEAK_LIMIT / peak
    return out.astype(np.float32)


@dataclass
class MixedClip:
    track_id: str
    mix_path: Path
    backing: str


def build_mix(
    dataset: str, track_id: str, guitar_path: Path, position: int,
    musdb_dir: Path, mix_dir: Path,
) -> MixedClip:
    """Write (once) the mix of one clip; returns its path and backing name."""
    stem_mp4 = backing_for(position, backing_tracks(musdb_dir))
    backing_name = stem_mp4.name.removesuffix(".stem.mp4")
    mix_path = mix_dir / dataset / track_id / "mix.wav"
    if not mix_path.is_file():
        mixed = mix(_guitar_mono(guitar_path), backing_audio(stem_mp4, mix_dir))
        mix_path.parent.mkdir(parents=True, exist_ok=True)
        soundfile.write(str(mix_path), mixed, SAMPLE_RATE, subtype="PCM_16")
    return MixedClip(track_id, mix_path, backing_name)


def separated_guitar(mix_path: Path, device: str | None = None) -> Path:
    """Demucs ``guitar`` stem of a mix (tabgen's separation stage, cached)."""
    from tabgen.core.separation.demucs import separate

    result, _ = separate(mix_path, device=device)
    return Path(result.stems["guitar"])
