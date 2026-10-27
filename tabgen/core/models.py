"""Stage contracts: plain dataclasses exchanged between pipeline stages.

Every field uses only JSON-serializable builtins (str, int, float, bool,
lists and dicts of those). No torch/numpy objects may ever appear here, so
``json.dumps`` works on the ``to_dict()`` output without a custom encoder.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


class _JsonMixin:
    """Shared to/from JSON helpers for stage contract dataclasses."""

    def to_dict(self) -> dict[str, Any]:
        """Return a plain-dict representation (recursively, builtins only)."""
        return asdict(self)  # type: ignore[call-overload]

    def to_json(self) -> str:
        """Serialize to a JSON string using only the standard encoder."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        """Rebuild an instance from a plain dict (inverse of ``to_dict``)."""
        return cls(**data)  # type: ignore[call-arg]

    @classmethod
    def from_json(cls, payload: str):
        """Rebuild an instance from a JSON string (inverse of ``to_json``)."""
        return cls.from_dict(json.loads(payload))


@dataclass
class SeparationResult(_JsonMixin):
    """Output of the source-separation stage."""

    # Mapping of stem name (e.g. "guitar", "other") to audio file path.
    stems: dict[str, str] = field(default_factory=dict)
    sample_rate: int = 44100
    model_version: str = ""


@dataclass
class ChordSegment(_JsonMixin):
    """A chord detected over a time span of the audio."""

    start_s: float
    end_s: float
    # Chord label in Harte-style notation, e.g. "A:min", "C:maj", "N" (none).
    label: str


@dataclass
class AnalysisResult(_JsonMixin):
    """Output of the musical-analysis stage (tempo, beats, key, chords, tuning)."""

    tempo_bpm: float = 0.0
    beat_times: list[float] = field(default_factory=list)
    downbeat_times: list[float] = field(default_factory=list)
    # Global key as "<tonic> <mode>", e.g. "A minor"; empty when unknown.
    key: str = ""
    # Confidence of the key estimate in [0.0, 1.0].
    key_confidence: float = 0.0
    chords: list[ChordSegment] = field(default_factory=list)
    # Not computed in this phase; kept for the tuning-estimation stage.
    tuning_offset_cents: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalysisResult:
        data = dict(data)
        data["chords"] = [ChordSegment.from_dict(c) for c in data.get("chords", [])]
        return cls(**data)


@dataclass
class Note(_JsonMixin):
    """A single detected note event."""

    pitch_midi: int
    start_s: float
    end_s: float
    velocity: float = 1.0
    confidence: float = 1.0


@dataclass
class NoteEvents(_JsonMixin):
    """Output of the transcription stage: the detected note events."""

    notes: list[Note] = field(default_factory=list)
    instrument: str = "guitar"
    model_version: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NoteEvents:
        data = dict(data)
        data["notes"] = [Note.from_dict(n) for n in data.get("notes", [])]
        return cls(**data)


# Version of the TabScore schema; bump on breaking changes so cache keys of
# the tablature stage can invalidate stale payloads (consumed by caching).
TAB_FORMAT_VERSION = 1

# Tuning presets: open-string MIDI pitches ordered low-to-high
# (index 0 = lowest-pitched/thickest string).
GUITAR_STANDARD_TUNING = [40, 45, 50, 55, 59, 64]  # E2 A2 D3 G3 B3 E4
BASS_STANDARD_TUNING = [28, 33, 38, 43]  # E1 A1 D2 G2


@dataclass
class TabNote(_JsonMixin):
    """A single note placed on the fretboard, quantized to the measure grid."""

    # String index, 1-based, guitarist convention: 1 is the highest-pitched
    # string and N (= len(tuning_midi)) the lowest-pitched/thickest one.
    # Note: this is the REVERSE of the low-to-high ``TabScore.tuning_midi``
    # order (open pitch of string ``s`` is ``tuning_midi[len(tuning_midi) - s]``).
    string: int
    fret: int
    # Quantized position: measure and beat are 1-based; subdivision is the
    # 0-based offset inside the beat, in units of the score's grid.
    measure: int
    beat: int
    subdivision: int
    # Duration in grid subdivisions (>= 1 once quantized).
    duration_subdivisions: int
    # Original (unquantized) times from the transcription stage, in seconds.
    start_s: float
    end_s: float


@dataclass
class MeasureChord(_JsonMixin):
    """A chord annotation attached to a measure of the score."""

    # Measure index, 1-based, matching ``TabNote.measure``.
    measure: int
    # Chord label in Harte-style notation, e.g. "A:min" (see ChordSegment).
    label: str


@dataclass
class TabScore(_JsonMixin):
    """Output of the fretting stage: notes placed on string/fret over a grid."""

    instrument: str = "guitar"
    # Open-string MIDI pitches, low-to-high; length is the string count.
    tuning_midi: list[int] = field(default_factory=lambda: list(GUITAR_STANDARD_TUNING))
    capo_fret: int = 0
    tempo_bpm: float = 0.0
    # Global key as "<tonic> <mode>", e.g. "A minor"; empty when unknown.
    key: str = ""
    # Time signature as [numerator, denominator], e.g. [4, 4].
    time_signature: list[int] = field(default_factory=lambda: [4, 4])
    events: list[TabNote] = field(default_factory=list)
    chords: list[MeasureChord] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TabScore:
        data = dict(data)
        data["events"] = [TabNote.from_dict(e) for e in data.get("events", [])]
        data["chords"] = [MeasureChord.from_dict(c) for c in data.get("chords", [])]
        return cls(**data)
