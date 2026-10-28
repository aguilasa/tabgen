"""Evaluate guitar-specific transcription candidates against Basic Pitch.

Experimental wrapper for REF-TASK-07, kept OUT of ``tabgen/core``: it swaps
the transcription step of :func:`scripts.eval.run.pipeline_estimator` for a
candidate model and keeps everything else (DP fretting with
``guitar_config()``, metrics, subsets, report format) the same, so the
numbers are comparable with the harness.

Usage (from the repository root)::

    .venv/bin/python scripts/eval/candidates.py --candidate riley-fl \\
        --dataset guitarset --subset scripts/eval/subsets/guitarset.txt
    .venv/bin/python scripts/eval/candidates.py --candidate basic-pitch \\
        --dataset egdb --subset scripts/eval/subsets/egdb.txt

Candidates:

- ``basic-pitch`` — the current stage 4 (same estimator as ``run.py``),
  re-run so baseline and candidates share one commit.
- ``riley-fl`` — Riley, Edwards & Dixon, "High Resolution Guitar
  Transcription via Domain Adaptation" (ICASSP 2024), checkpoint
  ``guitar-fl.pth`` (trained on the François Leduc dataset).
- ``riley-gaps`` — the same architecture trained on GAPS (Riley et al.,
  ISMIR 2024), checkpoint ``guitar-gaps.pth``.

The Riley models need two things that are NOT project dependencies and are
never fetched by this script: the checkpoints from
https://huggingface.co/xavriley/midi-transcription-models in
``<candidates-dir>/weights/`` and the inference code
(``git+https://github.com/xavriley/piano_transcription_inference`` and
``torchlibrosa``, installed with ``pip install --no-deps --target
<candidates-dir>/site``). ``--candidates-dir`` defaults to
``$TABGEN_DATASETS/candidates``, else ``~/datasets/tabgen/candidates``.

Reports go to ``--out`` (default ``scripts/eval/reports/candidates/<candidate>/``)
in the ``run.py`` format.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.eval import loaders  # noqa: E402
from scripts.eval.metrics import LabeledNote  # noqa: E402
from scripts.eval.run import (  # noqa: E402
    DATASETS,
    Estimator,
    default_data_dir,
    evaluate,
    pipeline_estimator,
    write_report,
)

RILEY_CHECKPOINTS = {
    "riley-fl": "guitar-fl.pth",
    "riley-gaps": "guitar-gaps.pth",
}
CANDIDATES = ("basic-pitch", *RILEY_CHECKPOINTS)
DEFAULT_OUT = REPO_ROOT / "scripts" / "eval" / "reports" / "candidates"

# Inference settings of xavriley/hf_midi_transcription (model.py): CRNN with
# onset/offset/frame/velocity regression, 10 s segments at 16 kHz.
RILEY_MODEL_TYPE = "Regress_onset_offset_frame_velocity_CRNN"
RILEY_SEGMENT_SECONDS = 10
RILEY_ONSET_THRESHOLD = 0.3
RILEY_OFFSET_THRESHOLD = 0.3
RILEY_FRAME_THRESHOLD = 0.1


def default_candidates_dir() -> Path:
    root = os.environ.get("TABGEN_DATASETS")
    base = Path(root) if root else Path.home() / "datasets" / "tabgen"
    return base / "candidates"


def _sha256_prefix(path: Path, length: int = 12) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()[:length]


@lru_cache(maxsize=None)
def _riley_transcriptor(checkpoint: Path, site_dir: Path, device: str):
    if str(site_dir) not in sys.path:
        sys.path.insert(0, str(site_dir))
    from piano_transcription_inference import PianoTranscription, sample_rate

    transcriptor = PianoTranscription(
        RILEY_MODEL_TYPE,
        checkpoint_path=str(checkpoint),
        device=device,
        segment_samples=RILEY_SEGMENT_SECONDS * sample_rate,
        batch_size=8,
        onset_threshold=RILEY_ONSET_THRESHOLD,
        offset_threshold=RILEY_OFFSET_THRESHOLD,
        frame_threshold=RILEY_FRAME_THRESHOLD,
    )
    return transcriptor, sample_rate


def riley_estimator(
    candidate: str, candidates_dir: Path, device: str = "cuda"
) -> Estimator:
    """Estimator: Riley CRNN transcription + the harness's DP fretting."""
    checkpoint = candidates_dir / "weights" / RILEY_CHECKPOINTS[candidate]
    site_dir = candidates_dir / "site"
    if not checkpoint.is_file():
        raise FileNotFoundError(
            f"missing checkpoint {checkpoint}: download it from "
            "https://huggingface.co/xavriley/midi-transcription-models"
        )
    version = f"{candidate}@sha256:{_sha256_prefix(checkpoint)}"

    def estimate(audio: Path) -> tuple[list[LabeledNote], str]:
        import librosa

        from tabgen.core.fretting import assign_frets, guitar_config
        from tabgen.core.models import Note, NoteEvents

        transcriptor, sample_rate = _riley_transcriptor(checkpoint, site_dir, device)
        samples, _ = librosa.load(str(audio), sr=sample_rate, mono=True)
        events = transcriptor.transcribe(samples, None)["est_note_events"]
        notes = NoteEvents(
            notes=[
                Note(
                    pitch_midi=int(e["midi_note"]),
                    start_s=float(e["onset_time"]),
                    end_s=float(e["offset_time"]),
                    velocity=float(e["velocity"]) / 127.0,
                )
                for e in events
                if e["offset_time"] > e["onset_time"]
            ],
            instrument="guitar",
            model_version=version,
        )
        fretting = assign_frets(notes, guitar_config())
        labeled = [
            LabeledNote(
                a.note.start_s, a.note.end_s, float(a.note.pitch_midi), a.string
            )
            for a in fretting.assignments
        ]
        labeled += [
            LabeledNote(u.note.start_s, u.note.end_s, float(u.note.pitch_midi), None)
            for u in fretting.unassigned
        ]
        labeled.sort(key=lambda n: (n.onset_s, n.pitch_midi))
        return labeled, version

    return estimate


def build_estimator(candidate: str, candidates_dir: Path, device: str) -> Estimator:
    if candidate == "basic-pitch":
        return pipeline_estimator
    return riley_estimator(candidate, candidates_dir, device)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--candidate", choices=CANDIDATES, required=True)
    parser.add_argument("--dataset", choices=DATASETS, required=True)
    parser.add_argument("--subset", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--candidates-dir", type=Path, default=None,
                        help="weights/ and site/ of the candidate models")
    parser.add_argument("--device", default="cuda", help="cuda or cpu (Riley only)")
    parser.add_argument("--out", type=Path, default=None,
                        help="report directory (default: "
                             "scripts/eval/reports/candidates/<candidate>)")
    args = parser.parse_args(argv)

    data_dir = (args.data_dir or default_data_dir(args.dataset)).expanduser().resolve()
    candidates_dir = (args.candidates_dir or default_candidates_dir()).expanduser()
    track_ids = loaders.read_subset(args.subset)
    if not track_ids:
        parser.error(f"empty subset: {args.subset}")
    estimator = build_estimator(args.candidate, candidates_dir.resolve(), args.device)
    report = evaluate(args.dataset, track_ids, data_dir, args.subset.stem, estimator)
    out_dir = args.out or DEFAULT_OUT / args.candidate
    json_path, md_path = write_report(report, out_dir)
    mean = report.mean
    tab_f1 = "n/a" if mean["tab_f1"] is None else f"{mean['tab_f1']:.3f}"
    sys.stdout.write(
        f"{args.candidate} {args.dataset}: note-F1 {mean['note_f1']:.3f} "
        f"tab-F1 {tab_f1} "
        f"({mean['n_tracks']} tracks, {mean['n_tracks_with_tab']} with tab) "
        f"-> {md_path}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
