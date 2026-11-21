"""Standalone end-to-end probe of user stems in ``tabgen export`` (STEM-TASK-02).

Generates a deterministic guitar-only stem (Karplus-Strong plucked strings:
an A-minor pentatonic phrase, 120 BPM, 10 s, wav), as a track exported by
Moises would be, then:

- ``tabgen export <stem>.wav --no-separate --instruments guitar`` exits 0;
- Demucs did not run: no ``stems/`` folder next to the input and no
  ``separation-*`` entry in its ``.tabgen/`` cache (``demucs_loaded=False``);
- the .gp5 reopens via ``guitarpro.parse`` with notes in the guitar track
  (``gp5 ok``);
- a second run with ``--stem guitar=<stem>`` (same file, input = stem) is a
  tablature cache hit;
- wall-clock times are reported, not asserted.

Not collected by pytest; run it directly:

    .venv/bin/python scripts/probe_e2e_stems.py

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
SAMPLE_RATE = 44100
BPM = 120.0
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
        fail(f"{step} exited {result.returncode}\ncommand: {' '.join(cmd)}\n"
             f"stdout: {result.stdout.strip()}\nstderr: {result.stderr.strip()}")
    return result


def pluck(pitch: int, seconds: float, rng: np.random.Generator) -> np.ndarray:
    freq = 440.0 * 2 ** ((pitch - 69) / 12)
    period = int(round(SAMPLE_RATE / freq))
    buffer = rng.uniform(-1.0, 1.0, period)
    out = np.empty(int(seconds * SAMPLE_RATE))
    for i in range(out.size):
        out[i] = buffer[i % period]
        j = i % period
        buffer[j] = 0.996 * 0.5 * (buffer[j] + buffer[(i + 1) % period])
    return out


def generate_stem(directory: Path) -> Path:
    rng = np.random.default_rng(7)
    beat = 60.0 / BPM
    audio = np.zeros(int((len(PHRASE) * beat + 0.5) * SAMPLE_RATE))
    for i, pitch in enumerate(PHRASE):
        note = pluck(pitch, beat, rng)
        start = int(i * beat * SAMPLE_RATE)
        audio[start:start + note.size] += note
    audio /= np.abs(audio).max() * 1.25
    stem = directory / "lead-guitar.wav"
    soundfile.write(str(stem), audio.astype(np.float32), SAMPLE_RATE)
    return stem


def guitar_notes(gp5_path: Path) -> int:
    song = guitarpro.parse(str(gp5_path))
    return sum(len(beat.notes) for measure in song.tracks[0].measures
               for voice in measure.voices for beat in voice.beats)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="tabgen-stems-") as tmp:
        tmp_dir = Path(tmp)
        stem = generate_stem(tmp_dir)
        out = tmp_dir / "lead.gp5"
        started = time.monotonic()
        first = run([str(TABGEN), "export", str(stem), "-o", str(out),
                     "--no-separate", "--instruments", "guitar"],
                    step="export --no-separate")
        cold = time.monotonic() - started
        separation = list((tmp_dir / ".tabgen").glob("separation-*"))
        demucs_loaded = (tmp_dir / "stems").exists() or bool(separation)
        say(f"demucs_loaded={demucs_loaded}")
        if demucs_loaded:
            fail("Demucs ran although the input is the guitar stem")
        notes = guitar_notes(out)
        if notes == 0:
            fail("guitar track of the .gp5 has no notes")
        say(f"gp5 ok: {notes} guitar notes")
        say(f"cold export: {cold:.1f} s")
        if "cache hit" in first.stdout:
            fail("first run must not be a cache hit")
        started = time.monotonic()
        second = run([str(TABGEN), "export", str(stem), "-o", str(out),
                      "--stem", f"guitar={stem}", "--instruments", "guitar"],
                     step="export --stem")
        warm = time.monotonic() - started
        if "cache hit" not in second.stdout:
            fail("--stem guitar=<input> must hit the --no-separate cache entry")
        say(f"warm export (--stem, cache hit): {warm:.1f} s")
    say("probe ok")


if __name__ == "__main__":
    main()
