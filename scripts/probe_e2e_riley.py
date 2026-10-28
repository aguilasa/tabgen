"""Standalone end-to-end probe of ``tabgen export --transcriber`` (REF-TASK-09).

Generates a deterministic guitar-like sample (Karplus-Strong plucked
strings: an A-minor pentatonic phrase, 120 BPM, 10 s, mp3 via ffmpeg),
then:

- ``tabgen export --transcriber basic-pitch`` exits 0 (warm-up: fills the
  separation and analysis caches);
- with the transcription and tablature cache entries removed (separation
  and analysis stay warm), ``--transcriber basic-pitch`` and then
  ``--transcriber riley`` each exit 0, and the riley .gp5 reopens via
  ``guitarpro.parse`` with notes in the guitar track;
- the riley run must not be served from the basic-pitch tablature cache
  entry (the transcriber is part of the cache version);
- an export without ``--transcriber`` is served from the riley entry
  (``riley`` is the default since REF-TASK-09);
- the wall-clock time of both timed runs and their difference (the extra
  time of the riley model plus Basic Pitch for the bends) is reported, not
  asserted.

Note counts drift with mp3 encoding, so they are only reported. The riley
run uses the pinned ``guitar-gaps.pth`` from the huggingface_hub cache
(downloaded on first use, ~99 MB).

Not collected by pytest; run it directly:

    .venv/bin/python scripts/probe_e2e_riley.py

Everything is written to a temporary directory, nothing to the repo.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import guitarpro
import numpy as np
import soundfile

REPO_ROOT = Path(__file__).resolve().parent.parent
TABGEN = REPO_ROOT / ".venv" / "bin" / "tabgen"
CACHE_HIT_MARKER = "cache hit"
SAMPLE_RATE = 44100
BPM = 120.0
# A-minor pentatonic phrase, one note per beat (MIDI pitches).
PHRASE = [57, 60, 62, 64, 67, 64, 62, 60, 57, 55, 57, 60, 64, 62, 60, 57,
          57, 60, 62, 64]


def say(message: str) -> None:
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


def fail(message: str) -> None:
    sys.exit(f"FAIL: {message}")


def run(cmd: list[str], step: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        fail(
            f"{step} exited {result.returncode}\n"
            f"command: {' '.join(cmd)}\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}"
        )
    return result


def pluck(pitch: int, seconds: float, rng: np.random.Generator) -> np.ndarray:
    """Karplus-Strong plucked string at ``pitch`` (deterministic via ``rng``)."""
    freq = 440.0 * 2 ** ((pitch - 69) / 12)
    period = int(round(SAMPLE_RATE / freq))
    buffer = rng.uniform(-1.0, 1.0, period)
    out = np.empty(int(seconds * SAMPLE_RATE))
    for i in range(len(out)):
        out[i] = buffer[i % period]
        buffer[i % period] = 0.996 * 0.5 * (buffer[i % period]
                                            + buffer[(i + 1) % period])
    return out


def generate_sample(directory: Path) -> Path:
    rng = np.random.default_rng(9)
    beat = 60.0 / BPM
    audio = np.zeros(int(10.0 * SAMPLE_RATE))
    for i, pitch in enumerate(PHRASE):
        start = int(i * beat * SAMPLE_RATE)
        note = pluck(pitch, beat * 0.95, rng)[: len(audio) - start]
        audio[start: start + len(note)] += note
    audio *= 0.5 / np.abs(audio).max()
    wav = directory / "sample.wav"
    soundfile.write(str(wav), audio.astype(np.float32), SAMPLE_RATE)
    sample = directory / "sample.mp3"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-q:a", "2",
         str(sample)], step="ffmpeg sample encoding")
    wav.unlink()
    return sample


def clear_transcription_caches(directory: Path) -> None:
    """Drop transcription + tablature entries; keep separation and analysis."""
    for pattern in ("tablature-*.json", "transcription-*.json"):
        for path in directory.rglob(f".tabgen/{pattern}"):
            path.unlink()


def export(sample: Path, output: Path, transcriber: str | None, step: str):
    option = ["--transcriber", transcriber] if transcriber else []
    start = time.monotonic()
    result = run([str(TABGEN), "export", str(sample), "-o", str(output),
                  *option], step=step)
    elapsed = time.monotonic() - start
    if not output.is_file():
        fail(f"{step} exited 0 but {output.name} was not written")
    return result, elapsed


def guitar_notes(gp5_path: Path) -> int:
    try:
        song = guitarpro.parse(str(gp5_path))
    except Exception as err:  # noqa: BLE001 - any reopen failure fails the probe
        fail(f"guitarpro could not reopen {gp5_path.name}: {err}")
    return sum(
        len(beat.notes)
        for track in song.tracks
        if "guitar" in track.name.lower()
        for measure in track.measures
        for voice in measure.voices
        for beat in voice.beats
    )


def main() -> None:
    if not TABGEN.is_file():
        fail(f"{TABGEN} not found; install the project venv first")
    with tempfile.TemporaryDirectory(prefix="tabgen-probe-riley-") as tmp:
        tmp_dir = Path(tmp)
        sample = generate_sample(tmp_dir)
        say("warm-up export (Demucs/madmom, cold)...")
        export(sample, tmp_dir / "warm.gp5", "basic-pitch", "warm-up export")

        clear_transcription_caches(tmp_dir)
        say("timed export --transcriber basic-pitch...")
        _, bp_s = export(sample, tmp_dir / "bp.gp5", "basic-pitch",
                         "export --transcriber basic-pitch")
        bp_notes = guitar_notes(tmp_dir / "bp.gp5")

        clear_transcription_caches(tmp_dir)
        say("timed export --transcriber riley...")
        result, riley_s = export(sample, tmp_dir / "riley.gp5", "riley",
                                 "export --transcriber riley")
        if CACHE_HIT_MARKER in result.stdout:
            fail("riley export was served from a tablature cache entry\n"
                 f"stdout: {result.stdout.strip()}")
        riley_notes = guitar_notes(tmp_dir / "riley.gp5")
        if riley_notes == 0:
            fail("riley .gp5 has no note in the guitar track")

        say("export without --transcriber (default)...")
        result, _ = export(sample, tmp_dir / "default.gp5", None,
                           "export with the default transcriber")
        if CACHE_HIT_MARKER not in result.stdout:
            fail("the default export was not served from the riley cache entry\n"
                 f"stdout: {result.stdout.strip()}")

    say(
        "PASS: export exit 0 with --transcriber basic-pitch and riley; riley "
        f"gp5 reopened by guitarpro with {riley_notes} guitar note(s) "
        f"(basic-pitch: {bp_notes}; {len(PHRASE)} played; counts not "
        f"asserted). Warm separation/analysis: basic-pitch {bp_s:.1f} s, "
        f"riley {riley_s:.1f} s, extra {riley_s - bp_s:+.1f} s. Default "
        "export (no option) hit the riley cache entry."
    )


if __name__ == "__main__":
    main()
