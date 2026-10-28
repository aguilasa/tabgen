"""Reference-annotation loaders and on-disk layout of the evaluation datasets.

Layout under ``--data-dir`` (the same names as the upstream archives/folders):

- GuitarSet: ``annotation/<id>.jams`` and ``audio_mono-mic/<id>_mic.wav``.
- EGDB: ``audio_label/<n>.midi`` and ``audio_DI/<n>.wav``.

String convention: every loader returns tabgen's guitarist numbering,
string 1 = highest (high E) ... string 6 = lowest (low E).

GuitarSet JAMS files are plain JSON, so they are read with ``json`` (no
``jams`` dependency). Each ``note_midi`` annotation carries
``annotation_metadata.data_source`` = string index 0..5 with **0 = low E,
5 = high E** (GuitarSet / mirdata convention), so ``string = 6 - index``.
Values are fractional MIDI pitches (kept as is; mir_eval compares in Hz with
a 50-cent tolerance).

EGDB's README only says the labels carry "pitch onset and string"; the
per-string encoding of the MIDI (tracks or channels, and their order) is not
documented. :func:`load_egdb_notes` therefore groups notes by MIDI track, or
by channel when a single track holds several channels, and picks the
group-to-string mapping (ascending or descending order, any offset) under
which the most notes are playable on that string in standard tuning (fret
0..24). If no mapping places at least ``EGDB_MIN_PLAYABLE`` of the notes,
the strings are left as ``None`` and the reason is returned so the report
can say why tab-F1 is missing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import mido
import pretty_midi

from scripts.eval.metrics import LabeledNote

GUITAR_OPEN_LOW_TO_HIGH = [40, 45, 50, 55, 59, 64]  # E2 A2 D3 G3 B3 E4
N_STRINGS = len(GUITAR_OPEN_LOW_TO_HIGH)
MAX_FRET = 24
EGDB_MIN_PLAYABLE = 0.95


@dataclass
class TrackPaths:
    """Audio and annotation file of one dataset track."""

    track_id: str
    audio: Path
    annotation: Path


@dataclass
class Reference:
    """Reference notes of one track and, if any, why strings are missing."""

    notes: list[LabeledNote]
    string_mapping: str
    tab_unavailable_reason: str | None = None


def track_paths(dataset: str, data_dir: Path, track_id: str) -> TrackPaths:
    """Where one track's files live under ``data_dir``."""
    if dataset == "guitarset":
        return TrackPaths(
            track_id,
            audio=data_dir / "audio_mono-mic" / f"{track_id}_mic.wav",
            annotation=data_dir / "annotation" / f"{track_id}.jams",
        )
    if dataset == "egdb":
        return TrackPaths(
            track_id,
            audio=data_dir / "audio_DI" / f"{track_id}.wav",
            annotation=data_dir / "audio_label" / f"{track_id}.midi",
        )
    raise ValueError(f"unknown dataset {dataset!r}")


def read_subset(path: Path) -> list[str]:
    """Track ids of a subset file (blank lines and ``#`` comment lines ignored).

    Comments are whole lines only: ``#`` is part of GuitarSet ids
    (e.g. ``03_Rock1-90-C#_comp``).
    """
    ids = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            ids.append(line)
    return ids


def guitarset_string(data_source: int) -> int:
    """GuitarSet string index (0 = low E) -> guitarist string (1 = high E)."""
    if not 0 <= data_source < N_STRINGS:
        raise ValueError(f"GuitarSet data_source out of range: {data_source}")
    return N_STRINGS - data_source


def load_guitarset_notes(jams_path: Path) -> Reference:
    """All ``note_midi`` notes of a GuitarSet JAMS file, with their string."""
    doc = json.loads(Path(jams_path).read_text(encoding="utf-8"))
    notes: list[LabeledNote] = []
    for ann in doc.get("annotations", []):
        if ann.get("namespace") != "note_midi":
            continue
        source = ann.get("annotation_metadata", {}).get("data_source")
        string = guitarset_string(int(source))
        data = ann.get("data", [])
        # JAMS "sparse" data is a list of observations; the dense layout
        # (dict of parallel lists) is accepted too.
        if isinstance(data, dict):
            data = [
                {"time": t, "duration": d, "value": v}
                for t, d, v in zip(data["time"], data["duration"], data["value"])
            ]
        for obs in data:
            onset = float(obs["time"])
            notes.append(
                LabeledNote(
                    onset_s=onset,
                    offset_s=onset + float(obs["duration"]),
                    pitch_midi=float(obs["value"]),
                    string=string,
                )
            )
    notes.sort(key=lambda n: (n.onset_s, n.pitch_midi))
    return Reference(notes, string_mapping="jams data_source 0..5 (low E..high E)")


MidiNote = tuple[float, float, int]


def _midi_note_groups(path: Path) -> dict[tuple[int, int], list[MidiNote]]:
    """Notes as (onset_s, offset_s, pitch) keyed by (track index, channel)."""
    timing = pretty_midi.PrettyMIDI(str(path))
    groups: dict[tuple[int, int], list[MidiNote]] = {}
    for track_idx, track in enumerate(mido.MidiFile(str(path)).tracks):
        tick = 0
        open_notes: dict[tuple[int, int], list[int]] = {}
        for msg in track:
            tick += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                open_notes.setdefault((msg.channel, msg.note), []).append(tick)
            elif msg.type in ("note_off", "note_on"):
                starts = open_notes.get((msg.channel, msg.note))
                if starts:
                    start = starts.pop(0)
                    groups.setdefault((track_idx, msg.channel), []).append(
                        (
                            timing.tick_to_time(start),
                            timing.tick_to_time(tick),
                            msg.note,
                        )
                    )
    return groups


def _playable(pitch: int, low_to_high_index: int) -> bool:
    if not 0 <= low_to_high_index < N_STRINGS:
        return False
    fret = pitch - GUITAR_OPEN_LOW_TO_HIGH[low_to_high_index]
    return 0 <= fret <= MAX_FRET


def infer_string_mapping(
    groups: dict[int, list[int]],
) -> tuple[dict[int, int] | None, float, str]:
    """Best group-key -> guitarist-string mapping by playability.

    ``groups`` maps an integer group key (track or channel number) to its
    pitches. Candidates: key ``k`` -> low-to-high index ``k - base``
    (ascending) or ``base - k`` (descending). Returns
    ``(mapping or None, playable fraction, description)``; ``None`` when
    several distinct mappings tie for the best fraction (ambiguous).
    """
    keys = sorted(groups)
    total = sum(len(p) for p in groups.values())
    if not keys or total == 0:
        return None, 0.0, "no notes"
    if len(keys) > N_STRINGS:
        return None, 0.0, f"{len(keys)} note groups, more than {N_STRINGS} strings"
    candidates: list[tuple[float, dict[int, int], str]] = []
    for order in ("ascending", "descending"):
        for base in range(min(keys) - N_STRINGS, max(keys) + N_STRINGS + 1):
            mapping = {}
            ok = 0
            for k in keys:
                idx = k - base if order == "ascending" else base - k
                if not 0 <= idx < N_STRINGS:
                    break
                mapping[k] = N_STRINGS - idx
                ok += sum(1 for p in groups[k] if _playable(p, idx))
            else:
                candidates.append((ok / total, mapping, f"{order}, base {base}"))
    if not candidates:
        return None, 0.0, "no candidate mapping"
    fraction = max(c[0] for c in candidates)
    best = [c for c in candidates if c[0] == fraction]
    if len({tuple(sorted(c[1].items())) for c in best}) > 1:
        return None, fraction, f"ambiguous: {len(best)} mappings tie"
    return best[0][1], fraction, best[0][2]


def load_egdb_notes(midi_path: Path) -> Reference:
    """EGDB label MIDI -> notes with inferred strings (see module docstring)."""
    raw = _midi_note_groups(Path(midi_path))
    tracks = {t for t, _ in raw}
    channels = {c for _, c in raw}
    by = "track" if len(tracks) > 1 or len(channels) == 1 else "channel"
    keyed: dict[int, list[tuple[float, float, int]]] = {}
    for (track, channel), notes in raw.items():
        keyed.setdefault(track if by == "track" else channel, []).extend(notes)

    mapping, fraction, how = infer_string_mapping(
        {k: [p for _, _, p in v] for k, v in keyed.items()}
    )
    reason = None
    if len(keyed) <= 1:
        mapping, reason = None, "label MIDI has a single note group: no string info"
    elif mapping is None or fraction < EGDB_MIN_PLAYABLE:
        reason = (
            f"no unique {by}->string mapping makes >= {EGDB_MIN_PLAYABLE:.0%} "
            f"of notes playable (best {fraction:.1%}; {how})"
        )
        mapping = None
    notes = [
        LabeledNote(on, off, float(pitch), mapping[k] if mapping else None)
        for k, group in keyed.items()
        for on, off, pitch in group
    ]
    notes.sort(key=lambda n: (n.onset_s, n.pitch_midi))
    description = (
        f"by {by} ({how}; {fraction:.1%} playable)" if mapping else f"by {by}: none"
    )
    return Reference(notes, string_mapping=description, tab_unavailable_reason=reason)


def load_reference(dataset: str, annotation: Path) -> Reference:
    """Dispatch to the dataset's annotation loader."""
    if dataset == "guitarset":
        return load_guitarset_notes(annotation)
    if dataset == "egdb":
        return load_egdb_notes(annotation)
    raise ValueError(f"unknown dataset {dataset!r}")
