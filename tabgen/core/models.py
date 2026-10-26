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
class AnalysisResult(_JsonMixin):
    """Output of the musical-analysis stage (tempo, beats, key, tuning)."""

    tempo_bpm: float = 0.0
    beat_times: list[float] = field(default_factory=list)
    downbeat_times: list[float] = field(default_factory=list)
    key: str = ""
    tuning_offset_cents: float = 0.0


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


@dataclass
class TabScore(_JsonMixin):
    """Skeleton of the fretting-stage output: notes placed on string/fret.

    Each event is a plain dict with keys such as ``string`` (1-6),
    ``fret``, ``start_s`` and ``duration_s``. The full schema will be
    fleshed out when the fretting stage is implemented.
    """

    tuning_midi: list[int] = field(default_factory=lambda: [40, 45, 50, 55, 59, 64])
    capo_fret: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)
