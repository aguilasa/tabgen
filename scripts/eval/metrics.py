"""Note-F1 and tab-F1 between reference and estimated guitar notes.

Definitions (both onset-only, no offset criterion):

- **note-F1**: ``mir_eval.transcription.precision_recall_f1_overlap`` with
  ``onset_tolerance=0.05`` s, ``pitch_tolerance=50`` cents and
  ``offset_ratio=None``. Strings are ignored.
- **tab-F1**: the same note matching (``mir_eval.transcription.match_notes``,
  a maximum bipartite matching on onset +-50 ms and pitch +-50 cents); a
  matched pair counts as *tab-correct* only if the estimated string equals
  the reference string. With pitch and string equal, the fret is implied
  (fret = pitch - open-string pitch), so tab-correct means right note on
  the right string and fret. ``tab_precision = tab_correct / n_est``,
  ``tab_recall = tab_correct / n_ref``. The matching itself is string
  agnostic, so tab-F1 <= note-F1 always holds. Estimated notes without a
  string (fretting left them unassigned) can match for note-F1 but are never
  tab-correct.

Strings follow tabgen's guitarist convention: string 1 is the highest
(high E), string 6 the lowest (low E).

Edge cases: no reference and no estimate gives 1.0 (nothing to find, nothing
wrongly found); exactly one side empty gives 0.0.
"""

from __future__ import annotations

from dataclasses import dataclass

import mir_eval
import numpy as np

ONSET_TOLERANCE_S = 0.05
PITCH_TOLERANCE_CENTS = 50.0


@dataclass(frozen=True)
class LabeledNote:
    """One note with its (optional) string, for either side of the comparison."""

    onset_s: float
    offset_s: float
    pitch_midi: float
    string: int | None = None


@dataclass(frozen=True)
class Scores:
    """Precision/recall/F1 for notes and for tablature, plus the counts."""

    note_precision: float
    note_recall: float
    note_f1: float
    tab_precision: float
    tab_recall: float
    tab_f1: float
    n_ref: int
    n_est: int
    n_matched: int
    n_tab_correct: int

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _arrays(notes: list[LabeledNote]) -> tuple[np.ndarray, np.ndarray]:
    if not notes:
        return np.zeros((0, 2)), np.zeros(0)
    intervals = np.array(
        [[n.onset_s, max(n.offset_s, n.onset_s + 1e-3)] for n in notes], dtype=float
    )
    pitches_hz = mir_eval.util.midi_to_hz(
        np.array([n.pitch_midi for n in notes], dtype=float)
    )
    return intervals, pitches_hz


def _f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def score(
    reference: list[LabeledNote],
    estimate: list[LabeledNote],
    onset_tolerance: float = ONSET_TOLERANCE_S,
) -> Scores:
    """Compute note-F1 and tab-F1 (see the module docstring)."""
    n_ref, n_est = len(reference), len(estimate)
    if n_ref == 0 or n_est == 0:
        value = 1.0 if n_ref == n_est else 0.0
        return Scores(value, value, value, value, value, value, n_ref, n_est, 0, 0)

    ref_iv, ref_hz = _arrays(reference)
    est_iv, est_hz = _arrays(estimate)
    note_p, note_r, note_f, _ = mir_eval.transcription.precision_recall_f1_overlap(
        ref_iv,
        ref_hz,
        est_iv,
        est_hz,
        onset_tolerance=onset_tolerance,
        pitch_tolerance=PITCH_TOLERANCE_CENTS,
        offset_ratio=None,
    )
    matches = mir_eval.transcription.match_notes(
        ref_iv,
        ref_hz,
        est_iv,
        est_hz,
        onset_tolerance=onset_tolerance,
        pitch_tolerance=PITCH_TOLERANCE_CENTS,
        offset_ratio=None,
    )
    tab_correct = sum(
        1
        for ref_idx, est_idx in matches
        if estimate[est_idx].string is not None
        and estimate[est_idx].string == reference[ref_idx].string
    )
    tab_p = tab_correct / n_est
    tab_r = tab_correct / n_ref
    return Scores(
        note_precision=float(note_p),
        note_recall=float(note_r),
        note_f1=float(note_f),
        tab_precision=tab_p,
        tab_recall=tab_r,
        tab_f1=_f1(tab_p, tab_r),
        n_ref=n_ref,
        n_est=n_est,
        n_matched=len(matches),
        n_tab_correct=tab_correct,
    )
