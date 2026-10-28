"""Standalone end-to-end probe for the export pipeline (FIX-TAB-005).

Regenerates the verification sample deterministically (sine 220 Hz, 10 s, mp3)
with ffmpeg, runs ``tabgen export`` on it for the three formats and asserts
only the facts that are stable across runs/encoders:

- every export exits 0 and writes its output file;
- the .gp5 reopens via ``guitarpro.parse`` with both tracks (guitar and bass)
  holding at least one note each;
- the .musicxml reopens via ``music21.converter.parse``;
- the ASCII .txt is non-empty;
- a second gp5 run reuses the tablature cache (stdout mentions "cache hit";
  its wall-clock time is reported but not hard-asserted);
- a ``--no-techniques`` gp5 run (REF-TASK-04) exits 0, is NOT served from
  the techniques-on cache entry (the switch is part of the cache version)
  and its .gp5 carries no note effect at all (no bend, slide or hammer).

Exact note and technique counts drift with mp3 encode artifacts, so they
are deliberately NOT asserted (same policy as probe_e2e_sample.py); the
techniques-on effect count is only reported.

Not collected by pytest; run it directly:

    .venv/bin/python scripts/probe_e2e_export.py

The first run is slow (Demucs separation; ~1 min cold on GPU, longer on CPU).
Dependencies: guitarpro, music21 (both project deps) and an ``ffmpeg`` binary
on PATH. Everything is written to a temporary directory, nothing to the repo.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

import guitarpro
import music21

REPO_ROOT = Path(__file__).resolve().parent.parent
TABGEN = REPO_ROOT / ".venv" / "bin" / "tabgen"
CACHE_HIT_MARKER = "cache hit"
CACHE_HIT_BUDGET_S = 5.0  # informational only, not a hard assert


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


def export(
    sample: Path, output: Path, step: str, extra: tuple[str, ...] = ()
) -> subprocess.CompletedProcess[str]:
    result = run(
        [str(TABGEN), "export", str(sample), "-o", str(output), *extra],
        step=step,
    )
    if not output.is_file():
        fail(f"{step} exited 0 but {output.name} was not written")
    return result


def gp5_track_note_counts(gp5_path: Path) -> dict[str, int]:
    """Reopen the .gp5 with PyGuitarPro and count notes per track."""
    try:
        song = guitarpro.parse(str(gp5_path))
    except Exception as err:  # noqa: BLE001 - any reopen failure fails the probe
        fail(f"guitarpro could not reopen {gp5_path.name}: {err}")
    return {
        track.name: sum(
            len(beat.notes)
            for measure in track.measures
            for voice in measure.voices
            for beat in voice.beats
        )
        for track in song.tracks
    }


def gp5_effect_count(gp5_path: Path) -> int:
    """Notes of the .gp5 carrying a bend, slide or hammer/pull effect."""
    song = guitarpro.parse(str(gp5_path))
    return sum(
        1
        for track in song.tracks
        for measure in track.measures
        for voice in measure.voices
        for beat in voice.beats
        for note in beat.notes
        if note.effect.bend is not None or note.effect.slides or note.effect.hammer
    )


def check_no_techniques(sample: Path, output: Path) -> None:
    result = export(
        sample, output, step="tabgen export --no-techniques", extra=("--no-techniques",)
    )
    if CACHE_HIT_MARKER in result.stdout:
        fail(
            "--no-techniques run was served from the techniques-on cache entry\n"
            f"stdout: {result.stdout.strip()}"
        )
    effects = gp5_effect_count(output)
    if effects:
        fail(f"--no-techniques gp5 still has {effects} note effect(s)")


def check_gp5(gp5_path: Path) -> dict[str, int]:
    counts = gp5_track_note_counts(gp5_path)
    for instrument in ("guitar", "bass"):
        matches = [name for name in counts if instrument in name.lower()]
        if not matches:
            fail(
                f"gp5 has no {instrument} track; "
                f"tracks found: {sorted(counts)}"
            )
        if all(counts[name] == 0 for name in matches):
            fail(f"gp5 {instrument} track has no notes (expected at least one)")
    return counts


def check_musicxml(xml_path: Path) -> None:
    try:
        music21.converter.parse(str(xml_path))
    except Exception as err:  # noqa: BLE001 - any reopen failure fails the probe
        fail(f"music21 could not reopen {xml_path.name}: {err}")


def check_ascii(txt_path: Path) -> int:
    size = txt_path.stat().st_size
    if size == 0:
        fail(f"ASCII tab {txt_path.name} is empty")
    return size


def check_cache_hit(sample: Path, output: Path) -> float:
    start = time.monotonic()
    result = export(sample, output, step="tabgen export (cached rerun)")
    elapsed = time.monotonic() - start
    if CACHE_HIT_MARKER not in result.stdout:
        fail(
            f"cached rerun stdout does not mention '{CACHE_HIT_MARKER}'\n"
            f"stdout: {result.stdout.strip()}"
        )
    return elapsed


def main() -> None:
    if not TABGEN.is_file():
        fail(f"{TABGEN} not found; install the project venv first")

    with tempfile.TemporaryDirectory(prefix="tabgen-probe-") as tmp:
        tmp_dir = Path(tmp)
        sample = generate_sample(tmp_dir)

        gp5_path = tmp_dir / "sample.gp5"
        xml_path = tmp_dir / "sample.musicxml"
        txt_path = tmp_dir / "sample.txt"

        say("exporting gp5 (cold run: Demucs/Basic Pitch/madmom may be slow)...")
        export(sample, gp5_path, step="tabgen export gp5")
        counts = check_gp5(gp5_path)
        effects = gp5_effect_count(gp5_path)

        say("exporting musicxml...")
        export(sample, xml_path, step="tabgen export musicxml")
        check_musicxml(xml_path)

        say("exporting ascii txt...")
        export(sample, txt_path, step="tabgen export ascii")
        ascii_bytes = check_ascii(txt_path)

        say("rerunning gp5 export to check the tablature cache...")
        elapsed = check_cache_hit(sample, gp5_path)

        say("exporting gp5 with --no-techniques...")
        check_no_techniques(sample, tmp_dir / "plain.gp5")

    counts_text = ", ".join(f"{name}: {n}" for name, n in sorted(counts.items()))
    timing_note = (
        "" if elapsed < CACHE_HIT_BUDGET_S else " (slower than the usual <5 s)"
    )
    say(
        "PASS: export exit 0 for gp5/musicxml/ascii; gp5 reopened by guitarpro "
        f"with notes in both tracks ({counts_text}; counts not asserted); "
        "musicxml reopened by music21; ASCII tab non-empty "
        f"({ascii_bytes} bytes); cached rerun mentioned '{CACHE_HIT_MARKER}' "
        f"in {elapsed:.2f} s{timing_note}; --no-techniques gp5 has 0 note "
        f"effects on its own cache entry (techniques on: {effects} effect(s), "
        "not asserted)."
    )


if __name__ == "__main__":
    main()
