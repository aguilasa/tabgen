"""Standalone end-to-end probe for the transcribe pipeline (FIX-FMVP-005).

Regenerates the verification sample deterministically (sine 220 Hz, 10 s, mp3)
with ffmpeg, runs ``tabgen transcribe`` on it and asserts only the facts that
are stable across runs/encoders:

- the command exits 0 and writes ``sample.guitar.mid`` and ``sample.bass.mid``;
- mido reopens both files without error;
- the bass track has at least one note and contains pitch 57 (A3 = 220 Hz).

Exact note counts (especially spurious low-pitch guitar detections) vary with
mp3 encode artifacts, so they are deliberately NOT asserted.

Not collected by pytest; run it directly:

    .venv/bin/python scripts/probe_e2e_sample.py

Takes ~10-15 s (Basic Pitch inference on CPU). Dependencies: stdlib, mido and
an ``ffmpeg`` binary on PATH.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import mido

REPO_ROOT = Path(__file__).resolve().parent.parent
TABGEN = REPO_ROOT / ".venv" / "bin" / "tabgen"
EXPECTED_BASS_PITCH = 57  # A3 = 220 Hz


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


def generate_sample(directory: Path) -> Path:
    sample = directory / "sample.mp3"
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=220:duration=10",
            "-q:a",
            "2",
            str(sample),
        ],
        step="ffmpeg sample generation",
    )
    if not sample.is_file():
        fail(f"ffmpeg exited 0 but {sample} was not written")
    return sample


def note_pitches(midi_path: Path) -> list[int]:
    """Reopen a .mid with mido and return the pitches of its note_on events."""
    try:
        midi = mido.MidiFile(midi_path)
    except Exception as err:  # noqa: BLE001 - any reopen failure fails the probe
        fail(f"mido could not reopen {midi_path.name}: {err}")
    return [
        msg.note
        for track in midi.tracks
        for msg in track
        if msg.type == "note_on" and msg.velocity > 0
    ]


def main() -> None:
    if not TABGEN.is_file():
        fail(f"{TABGEN} not found; install the project venv first")

    with tempfile.TemporaryDirectory(prefix="tabgen-probe-") as tmp:
        tmp_dir = Path(tmp)
        sample = generate_sample(tmp_dir)

        run([str(TABGEN), "transcribe", str(sample)], step="tabgen transcribe")

        guitar_mid = tmp_dir / "sample.guitar.mid"
        bass_mid = tmp_dir / "sample.bass.mid"
        for midi_path in (guitar_mid, bass_mid):
            if not midi_path.is_file():
                fail(f"expected MIDI file not written: {midi_path.name}")

        guitar_pitches = note_pitches(guitar_mid)
        bass_pitches = note_pitches(bass_mid)

        if not bass_pitches:
            fail("bass MIDI has no notes (expected at least one)")
        if EXPECTED_BASS_PITCH not in bass_pitches:
            fail(
                f"bass MIDI has no pitch {EXPECTED_BASS_PITCH} (A3 = 220 Hz); "
                f"got pitches {sorted(set(bass_pitches))}"
            )

    say(
        "PASS: transcribe exit 0; both .mid written and reopened by mido; "
        f"bass has {len(bass_pitches)} note(s) with pitch {EXPECTED_BASS_PITCH} "
        f"present (guitar: {len(guitar_pitches)} note(s), count not asserted)."
    )


if __name__ == "__main__":
    main()
