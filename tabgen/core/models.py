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


# Revision of the Note/NoteEvents contract. Bump it whenever their schema
# changes, so the transcription stage's cache key invalidates stale payloads.
# Revision 2 added ``Note.bends``.
NOTE_CONTRACT_REVISION = 2


@dataclass
class Note(_JsonMixin):
    """A single detected note event.

    ``bends`` holds Basic Pitch's per-frame pitch-bend offsets for this note,
    in 1/3-semitone bins relative to ``pitch_midi`` (e.g. 3 = +1 semitone,
    -3 = -1 semitone), one int per model frame from onset to offset. It is
    ``None`` when the transcriber reported no bend data for the note
    (payloads predating the field load as ``None``).
    """

    pitch_midi: int
    start_s: float
    end_s: float
    velocity: float = 1.0
    confidence: float = 1.0
    bends: list[int] | None = None


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


# Version of the TabScore schema; bump on schema changes so cache keys of
# the tablature stage can invalidate stale payloads (consumed by caching).
# Version 2 added ``TabNote.technique``.
TAB_FORMAT_VERSION = 2

# Tuning presets: open-string MIDI pitches ordered low-to-high
# (index 0 = lowest-pitched/thickest string).
GUITAR_STANDARD_TUNING = [40, 45, 50, 55, 59, 64]  # E2 A2 D3 G3 B3 E4
BASS_STANDARD_TUNING = [28, 33, 38, 43]  # E1 A1 D2 G2


# Guitar technique kinds carried by ``Technique.kind``.
TECHNIQUE_BEND = "bend"
TECHNIQUE_SLIDE = "slide"
TECHNIQUE_HAMMER_ON = "hammer_on"
TECHNIQUE_PULL_OFF = "pull_off"
TECHNIQUE_KINDS = (
    TECHNIQUE_BEND,
    TECHNIQUE_SLIDE,
    TECHNIQUE_HAMMER_ON,
    TECHNIQUE_PULL_OFF,
)

# Slide directions carried by ``Technique.slide_direction``.
SLIDE_UP = "up"
SLIDE_DOWN = "down"
SLIDE_DIRECTIONS = (SLIDE_UP, SLIDE_DOWN)


@dataclass
class Technique(_JsonMixin):
    """How a fretted note is articulated (attached to ``TabNote.technique``).

    Conventions (every technique lives on the note it STARTS from, the
    Guitar Pro convention):

    - ``kind``: one of :data:`TECHNIQUE_KINDS`.
    - ``bend`` (``kind == TECHNIQUE_BEND``): the note is picked at its fret
      and bent up. ``bend_semitones`` is the peak target, in semitones above
      the fretted pitch (> 0; e.g. 1.0 = half-step, 2.0 = whole-step).
      ``bend_curve`` is the simplified bend shape: semitone offsets above
      the fretted pitch sampled at evenly spaced points from onset (first
      value) to the note end (last value); empty means a plain bend that
      reaches ``bend_semitones`` and holds it.
    - ``slide`` (``kind == TECHNIQUE_SLIDE``): the note slides on the same
      string into the next note. ``slide_direction`` is :data:`SLIDE_UP`
      (towards higher frets/pitch) or :data:`SLIDE_DOWN` (required);
      ``target_fret`` is the destination fret on the same string, or
      ``None`` when unknown.
    - ``hammer_on`` / ``pull_off``: the NEXT note on the same string is
      sounded by hammering on (higher fret) or pulling off (lower fret)
      from this one, without a new pick attack. ``target_fret`` optionally
      records that next note's fret.

    Fields not used by ``kind`` keep their defaults. All values are JSON
    builtins.
    """

    kind: str
    bend_semitones: float = 0.0
    bend_curve: list[float] = field(default_factory=list)
    slide_direction: str = ""
    target_fret: int | None = None

    def __post_init__(self) -> None:
        if self.kind not in TECHNIQUE_KINDS:
            raise ValueError(
                f"unknown technique kind {self.kind!r}; "
                f"expected one of: {', '.join(TECHNIQUE_KINDS)}"
            )
        if self.kind == TECHNIQUE_BEND and self.bend_semitones <= 0:
            raise ValueError("bend technique needs bend_semitones > 0")
        slide = self.kind == TECHNIQUE_SLIDE
        if slide and self.slide_direction not in SLIDE_DIRECTIONS:
            raise ValueError(
                f"slide technique needs slide_direction in {SLIDE_DIRECTIONS}, "
                f"got {self.slide_direction!r}"
            )


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
    # Articulation of this note (see :class:`Technique` for conventions);
    # ``None`` = plainly picked note. Payloads predating the field load None.
    technique: Technique | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TabNote:
        data = dict(data)
        technique = data.get("technique")
        if technique is not None:
            data["technique"] = Technique.from_dict(technique)
        return cls(**data)


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
