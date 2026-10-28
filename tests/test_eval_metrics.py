"""Eval harness (scripts/eval): metrics on synthetic notes, loaders, end-to-end run."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import mido
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.eval import loaders, run  # noqa: E402
from scripts.eval.metrics import LabeledNote, score  # noqa: E402

# A short phrase in guitarist strings (1 = high E): E2 open, A2 open,
# D3 fret 2 (E3), G3 fret 2 (A3), B3 fret 1 (C4), high E fret 0 (E4).
PHRASE = [
    LabeledNote(0.00, 0.40, 40.0, 6),
    LabeledNote(0.50, 0.90, 45.0, 5),
    LabeledNote(1.00, 1.40, 52.0, 4),
    LabeledNote(1.50, 1.90, 57.0, 3),
    LabeledNote(2.00, 2.40, 60.0, 2),
    LabeledNote(2.00, 2.40, 64.0, 1),
]


def test_identical_prediction_scores_one():
    s = score(PHRASE, list(PHRASE))
    assert s.note_f1 == 1.0
    assert s.tab_f1 == 1.0
    assert s.n_matched == s.n_tab_correct == len(PHRASE)


def test_swapped_string_keeps_note_f1_and_lowers_tab_f1():
    # E3 (52) moved from string 4 fret 2 to string 5 fret 7: same pitch.
    est = list(PHRASE)
    est[2] = LabeledNote(1.00, 1.40, 52.0, 5)
    s = score(PHRASE, est)
    assert s.note_f1 == 1.0
    assert s.tab_f1 < 1.0
    assert s.n_tab_correct == len(PHRASE) - 1
    assert s.tab_f1 == pytest.approx(5 / 6)


def test_onset_tolerance_is_50ms_and_pitch_matters():
    shifted = [LabeledNote(n.onset_s + 0.04, n.offset_s, n.pitch_midi, n.string)
               for n in PHRASE]
    assert score(PHRASE, shifted).note_f1 == 1.0
    late = [LabeledNote(n.onset_s + 0.07, n.offset_s, n.pitch_midi, n.string)
            for n in PHRASE]
    assert score(PHRASE, late).note_f1 == 0.0
    wrong_pitch = [LabeledNote(n.onset_s, n.offset_s, n.pitch_midi + 1, n.string)
                   for n in PHRASE]
    assert score(PHRASE, wrong_pitch).note_f1 == 0.0


def test_unassigned_estimate_counts_for_notes_not_tab():
    est = list(PHRASE)
    est[0] = LabeledNote(0.0, 0.4, 40.0, None)
    s = score(PHRASE, est)
    assert s.note_f1 == 1.0
    assert s.n_tab_correct == len(PHRASE) - 1


def test_empty_sides():
    assert score([], []).note_f1 == 1.0
    assert score(PHRASE, []).note_f1 == 0.0
    assert score([], PHRASE).tab_f1 == 0.0


# --- loaders -----------------------------------------------------------------


def _write_jams(path: Path, notes: list[LabeledNote]) -> None:
    """GuitarSet-style JAMS: one note_midi annotation per string, 0 = low E."""
    annotations = []
    for source in range(6):
        string = 6 - source
        data = [
            {"time": n.onset_s, "duration": n.offset_s - n.onset_s,
             "value": n.pitch_midi, "confidence": None}
            for n in notes if n.string == string
        ]
        annotations.append({
            "namespace": "note_midi",
            "annotation_metadata": {"data_source": str(source)},
            "data": data,
        })
    annotations.append({"namespace": "beat_position", "data": []})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"annotations": annotations}), encoding="utf-8")


def _write_string_midi(path: Path, notes: list[LabeledNote], high_first: bool) -> None:
    """Label MIDI with one track per string (order configurable), 120 bpm."""
    mid = mido.MidiFile(ticks_per_beat=480)
    conductor = mido.MidiTrack([mido.MetaMessage("set_tempo", tempo=500000)])
    mid.tracks.append(conductor)
    order = range(1, 7) if high_first else range(6, 0, -1)
    for string in order:
        events = []
        for n in notes:
            if n.string == string:
                events.append((round(n.onset_s * 960), 1, int(n.pitch_midi)))
                events.append((round(n.offset_s * 960), 0, int(n.pitch_midi)))
        events.sort()
        track = mido.MidiTrack()
        last = 0
        for tick, on, pitch in events:
            kind = "note_on" if on else "note_off"
            track.append(mido.Message(kind, note=pitch, velocity=90, time=tick - last))
            last = tick
        mid.tracks.append(track)
    path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(path))


def test_guitarset_string_convention():
    assert loaders.guitarset_string(0) == 6  # low E
    assert loaders.guitarset_string(5) == 1  # high E


def test_guitarset_loader_round_trip(tmp_path):
    path = tmp_path / "x.jams"
    _write_jams(path, PHRASE)
    ref = loaders.load_guitarset_notes(path)
    assert ref.tab_unavailable_reason is None
    assert score(PHRASE, ref.notes).tab_f1 == 1.0


@pytest.mark.parametrize("high_first", [True, False])
def test_egdb_loader_infers_string_order(tmp_path, high_first):
    path = tmp_path / "1.midi"
    _write_string_midi(path, PHRASE, high_first)
    ref = loaders.load_egdb_notes(path)
    assert ref.tab_unavailable_reason is None, ref.string_mapping
    s = score(PHRASE, ref.notes)
    assert s.note_f1 == 1.0
    assert s.tab_f1 == 1.0


def test_egdb_single_group_has_no_tab(tmp_path):
    path = tmp_path / "2.midi"
    _write_string_midi(path, [LabeledNote(0.0, 0.5, 64.0, 1)], high_first=True)
    ref = loaders.load_egdb_notes(path)
    assert ref.tab_unavailable_reason is not None
    assert all(n.string is None for n in ref.notes)


def test_versioned_subsets_are_small_and_parse():
    for name in ("guitarset", "egdb"):
        ids = loaders.read_subset(REPO_ROOT / "scripts/eval/subsets" / f"{name}.txt")
        assert 5 <= len(ids) <= 10
        assert len(set(ids)) == len(ids)


def test_subset_keeps_hash_inside_track_ids(tmp_path):
    subset = tmp_path / "s.txt"
    subset.write_text("# comment\n03_Rock1-90-C#_comp\n\n", encoding="utf-8")
    assert loaders.read_subset(subset) == ["03_Rock1-90-C#_comp"]


# --- end to end with a fake dataset dir and an injected estimator ---------


def _fake_dataset(tmp_path: Path, dataset: str) -> tuple[Path, Path, list[str]]:
    data_dir = tmp_path / dataset
    ids = ["t1", "t2"] if dataset == "guitarset" else ["216", "219"]
    for track_id in ids:
        paths = loaders.track_paths(dataset, data_dir, track_id)
        paths.audio.parent.mkdir(parents=True, exist_ok=True)
        paths.audio.write_bytes(b"RIFF fake")
        if dataset == "guitarset":
            _write_jams(paths.annotation, PHRASE)
        else:
            _write_string_midi(paths.annotation, PHRASE, high_first=False)
    subset = tmp_path / f"{dataset}-mini.txt"
    subset.write_text("# fake\n" + "\n".join(ids) + "\n", encoding="utf-8")
    return data_dir, subset, ids


def _swapping_estimator(audio: Path):
    est = list(PHRASE)
    est[2] = LabeledNote(1.00, 1.40, 52.0, 5)
    return est, "fake-model"


@pytest.mark.parametrize("dataset", ["guitarset", "egdb"])
def test_run_main_writes_reports(tmp_path, dataset, capsys):
    data_dir, subset, ids = _fake_dataset(tmp_path, dataset)
    out = tmp_path / "reports"
    code = run.main(
        ["--dataset", dataset, "--subset", str(subset),
         "--data-dir", str(data_dir), "--out", str(out)],
        estimator=_swapping_estimator,
    )
    assert code == 0
    report = json.loads((out / f"{dataset}-{subset.stem}.json").read_text())
    assert report["mean"]["note_f1"] == 1.0
    assert report["mean"]["tab_f1"] == pytest.approx(5 / 6)
    assert [t["track_id"] for t in report["tracks"]] == ids
    md = (out / f"{dataset}-{subset.stem}.md").read_text()
    assert "mean" in md and "0.833" in md
    assert "mean note-F1 1.000" in capsys.readouterr().out


def test_run_main_missing_files_exits_2_without_download(tmp_path):
    subset = tmp_path / "s.txt"
    subset.write_text("nope\n", encoding="utf-8")
    code = run.main(["--dataset", "egdb", "--subset", str(subset),
                     "--data-dir", str(tmp_path / "empty"),
                     "--out", str(tmp_path / "r")])
    assert code == 2
    assert not (tmp_path / "empty").exists()
