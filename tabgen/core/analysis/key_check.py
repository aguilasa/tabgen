"""Cross-check the madmom key against the transcribed-note histogram.

The analysis stage (madmom's CNN key model, see
:mod:`tabgen.core.analysis.harmony`) yields a global key plus a
confidence; this module validates that key against what was actually
transcribed. :func:`check_key` builds a duration-weighted pitch-class
histogram from the :class:`~tabgen.core.models.NoteEvents` of every
instrument (guitar and bass together), scores all 24 major/minor keys
by Pearson correlation against the Krumhansl–Kessler profiles, and
applies a conservative decision rule:

1. If the histogram's best key equals the madmom key, or is its
   relative major/minor, the keys agree: keep the madmom key.
2. Otherwise keep the madmom key unless BOTH hold: the madmom
   confidence is below :data:`MIN_MADMOM_CONFIDENCE` AND the histogram
   prefers its own key over the madmom key (or its relative) by at
   least :data:`MIN_MARGIN` of correlation. Only then the result
   switches to the histogram's key and flags ``switched=True``.

The final ``key`` feeds the key signature written by the export stages
(.gp5 / MusicXML), so it keeps the exact ``"<tonic> <mode>"`` contract
format (e.g. ``"A minor"``, ``"F# major"``) used by the analysis stage.

This module is pure core: no I/O, no print/typer/rich.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from tabgen.core.models import NoteEvents

# Krumhansl & Kessler (1982) key profiles: average "goodness of fit"
# ratings of each pitch class in a major/minor context, indexed from the
# tonic. Reference: C. L. Krumhansl, "Cognitive Foundations of Musical
# Pitch", Oxford University Press, 1990, Table 2.1.
KK_MAJOR_PROFILE: tuple[float, ...] = (
    6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88,
)
KK_MINOR_PROFILE: tuple[float, ...] = (
    6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17,
)

# Decision-rule constants (see module docstring). madmom's
# key_confidence is the winning softmax probability over 24 classes; a
# value at or above this keeps the madmom key even when the histogram
# disagrees.
MIN_MADMOM_CONFIDENCE = 0.7
# Minimum Pearson-correlation advantage of the histogram's key over the
# madmom key (or its relative) required to override a low-confidence
# madmom estimate. Correlations live in [-1, 1].
MIN_MARGIN = 0.10

# Canonical tonic spellings, matching madmom's KEY_LABELS (flats except
# F#), so histogram-suggested keys look exactly like analysis-stage ones.
_TONIC_NAMES: tuple[str, ...] = (
    "C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B",
)
_MODES: tuple[str, ...] = ("major", "minor")

# Accepted tonic spellings (sharps and flats) -> pitch class.
_TONIC_TO_PC: dict[str, int] = {
    "C": 0, "B#": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "F": 5, "E#": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}

# Interval from a major tonic to its relative minor tonic (and the
# complement, 3, from a minor tonic to its relative major).
_RELATIVE_MINOR_OFFSET = 9
_RELATIVE_MAJOR_OFFSET = 3


@dataclass
class KeyCheckResult:
    """Outcome of cross-checking the madmom key with the note histogram.

    ``key`` is the final key in contract form (``"<tonic> <mode>"``) and
    is what downstream export stages must write as the key signature.
    All fields are JSON-serializable builtins.
    """

    # Final key after the decision rule; "" only when nothing is known.
    key: str = ""
    # Confidence of the final key: madmom's probability when kept, the
    # histogram's best correlation clipped to [0, 1] when switched.
    key_confidence: float = 0.0
    # True when madmom and histogram name the same or relative keys.
    agreement: bool = False
    # True when the final key is the histogram's, not madmom's.
    switched: bool = False
    # Madmom's key as received (may be "").
    madmom_key: str = ""
    # Best-correlating key of the histogram (may be "" without notes).
    histogram_key: str = ""
    # Correlation advantage of histogram_key over the madmom key or its
    # relative (0.0 when not applicable).
    margin: float = 0.0
    # Why the decision came out this way: "match", "relative",
    # "madmom_confident", "margin_too_small", "histogram_override",
    # "no_notes" or "no_madmom_key".
    reason: str = ""
    # Pearson correlation of the histogram against each of the 24 keys.
    scores: dict[str, float] = field(default_factory=dict)


def parse_key(key: str) -> tuple[int, str]:
    """Parse ``"<tonic> <mode>"`` into ``(pitch_class, mode)``.

    Accepts sharp and flat tonic spellings; raises ``ValueError`` on
    anything else.
    """
    parts = key.strip().split()
    if len(parts) == 2:
        tonic, mode = parts[0], parts[1].lower()
        if tonic in _TONIC_TO_PC and mode in _MODES:
            return _TONIC_TO_PC[tonic], mode
    raise ValueError(f"unrecognized key string: {key!r}")


def key_name(pitch_class: int, mode: str) -> str:
    """Return the canonical ``"<tonic> <mode>"`` name of a key."""
    return f"{_TONIC_NAMES[pitch_class % 12]} {mode}"


def relative_key(key: str) -> str:
    """Return the relative major/minor of ``key`` (canonical spelling)."""
    pitch_class, mode = parse_key(key)
    if mode == "major":
        return key_name(pitch_class + _RELATIVE_MINOR_OFFSET, "minor")
    return key_name(pitch_class + _RELATIVE_MAJOR_OFFSET, "major")


def pitch_class_histogram(note_events: Iterable[NoteEvents]) -> list[float]:
    """Duration-weighted pitch-class histogram over every instrument.

    Each note contributes ``end_s - start_s`` seconds (negative
    durations are clamped to zero) to its ``pitch_midi % 12`` bin.
    """
    histogram = [0.0] * 12
    for events in note_events:
        for note in events.notes:
            duration = max(note.end_s - note.start_s, 0.0)
            histogram[note.pitch_midi % 12] += duration
    return histogram


def _pearson(a: list[float], b: tuple[float, ...]) -> float:
    """Pearson correlation; 0.0 when either vector is constant."""
    n = len(a)
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    dev_a = [x - mean_a for x in a]
    dev_b = [x - mean_b for x in b]
    var_a = sum(x * x for x in dev_a)
    var_b = sum(x * x for x in dev_b)
    if var_a == 0.0 or var_b == 0.0:
        return 0.0
    cov = sum(x * y for x, y in zip(dev_a, dev_b))
    return cov / (var_a * var_b) ** 0.5


def score_keys(histogram: list[float]) -> dict[str, float]:
    """Correlate ``histogram`` against all 24 Krumhansl–Kessler keys.

    For a key with tonic pitch class ``t``, the profile is rotated so
    its first value sits on bin ``t``. Returns ``{key name: Pearson r}``.
    """
    scores: dict[str, float] = {}
    for mode, profile in (("major", KK_MAJOR_PROFILE), ("minor", KK_MINOR_PROFILE)):
        for tonic in range(12):
            rotated = tuple(profile[(pc - tonic) % 12] for pc in range(12))
            scores[key_name(tonic, mode)] = _pearson(histogram, rotated)
    return scores


def _keys_compatible(key_a: str, key_b: str) -> bool:
    """True when the keys are equal or relative major/minor of each other."""
    pc_a, mode_a = parse_key(key_a)
    pc_b, mode_b = parse_key(key_b)
    if (pc_a, mode_a) == (pc_b, mode_b):
        return True
    return key_name(pc_b, mode_b) == relative_key(key_name(pc_a, mode_a))


def check_key(
    madmom_key: str,
    madmom_confidence: float,
    note_events: Iterable[NoteEvents],
) -> KeyCheckResult:
    """Validate the analysis-stage key against the transcribed notes.

    ``madmom_key`` and ``madmom_confidence`` come straight from
    :class:`~tabgen.core.models.AnalysisResult` (``key`` /
    ``key_confidence``); ``note_events`` are the transcription outputs
    of every instrument (guitar and bass together). Applies the decision
    rule described in the module docstring and returns a
    :class:`KeyCheckResult`. Raises ``ValueError`` when a non-empty
    ``madmom_key`` is not in ``"<tonic> <mode>"`` form.
    """
    if madmom_key:
        # Validate (and normalize the comparison basis) early.
        parse_key(madmom_key)

    histogram = pitch_class_histogram(note_events)
    if sum(histogram) <= 0.0:
        # Nothing transcribed: the histogram has no say.
        return KeyCheckResult(
            key=madmom_key,
            key_confidence=madmom_confidence if madmom_key else 0.0,
            agreement=False,
            switched=False,
            madmom_key=madmom_key,
            histogram_key="",
            reason="no_notes",
        )

    scores = score_keys(histogram)
    histogram_key = max(scores, key=lambda name: scores[name])
    histogram_score = scores[histogram_key]

    if not madmom_key:
        # No madmom estimate at all: adopt the histogram's key.
        return KeyCheckResult(
            key=histogram_key,
            key_confidence=max(0.0, min(histogram_score, 1.0)),
            agreement=False,
            switched=True,
            madmom_key="",
            histogram_key=histogram_key,
            reason="no_madmom_key",
            scores=scores,
        )

    if _keys_compatible(madmom_key, histogram_key):
        reason = "match" if histogram_key == madmom_key else "relative"
        return KeyCheckResult(
            key=madmom_key,
            key_confidence=madmom_confidence,
            agreement=True,
            switched=False,
            madmom_key=madmom_key,
            histogram_key=histogram_key,
            reason=reason,
            scores=scores,
        )

    # Disagreement: margin is the histogram key's advantage over the
    # best key compatible with madmom's (itself or its relative).
    madmom_family_score = max(
        scores[key_name(*parse_key(madmom_key))],
        scores[relative_key(madmom_key)],
    )
    margin = histogram_score - madmom_family_score

    if madmom_confidence >= MIN_MADMOM_CONFIDENCE:
        reason, switched = "madmom_confident", False
    elif margin < MIN_MARGIN:
        reason, switched = "margin_too_small", False
    else:
        reason, switched = "histogram_override", True

    if switched:
        key = histogram_key
        confidence = max(0.0, min(histogram_score, 1.0))
    else:
        key = madmom_key
        confidence = madmom_confidence
    return KeyCheckResult(
        key=key,
        key_confidence=confidence,
        agreement=False,
        switched=switched,
        madmom_key=madmom_key,
        histogram_key=histogram_key,
        margin=margin,
        reason=reason,
        scores=scores,
    )
