"""Evaluate the tabgen pipeline on a fixed subset of GuitarSet or EGDB.

Usage (from the repository root)::

    .venv/bin/python scripts/eval/run.py --dataset guitarset \\
        --subset scripts/eval/subsets/guitarset.txt
    .venv/bin/python scripts/eval/run.py --dataset egdb \\
        --subset scripts/eval/subsets/egdb.txt

Datasets live OUTSIDE the repository, in ``--data-dir`` (default
``$TABGEN_DATASETS/<dataset>``, else ``~/datasets/tabgen/<dataset>``).
Missing files are never fetched implicitly: ``--download`` only prints the
URLs and sizes of what the subset needs; ``--download --yes`` downloads them
(the user's explicit confirmation) and then evaluates.

Per track: Basic Pitch transcription of the audio file as is (GuitarSet
mono mic and EGDB DI are guitar-only, so source separation is skipped),
then fretting with ``guitar_config()`` (standard tuning), then note-F1 and
tab-F1 from :mod:`scripts.eval.metrics`. Reports (JSON + Markdown, no audio)
go to ``--out`` (default ``scripts/eval/reports/``, versionable) as
``<dataset>-<subset name>.json|.md``. Basic Pitch's stage cache is written
next to the audio (``<data-dir>/.../.tabgen/``), i.e. outside the repository.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.eval import download, loaders  # noqa: E402
from scripts.eval.metrics import (  # noqa: E402
    ONSET_TOLERANCE_S,
    PITCH_TOLERANCE_CENTS,
    LabeledNote,
    score,
)

DATASETS = ("guitarset", "egdb")
DEFAULT_OUT = REPO_ROOT / "scripts" / "eval" / "reports"

# Audio path -> estimated notes (with strings). Injectable for tests.
Estimator = Callable[[Path], tuple[list[LabeledNote], str]]


def pipeline_estimator(audio: Path) -> tuple[list[LabeledNote], str]:
    """Basic Pitch transcription + DP fretting (standard guitar tuning)."""
    from tabgen.core.fretting import assign_frets, guitar_config
    from tabgen.core.transcription.basic_pitch import transcribe, transcription_version

    result, _ = transcribe(audio, instrument="guitar")
    fretting = assign_frets(result.note_events, guitar_config())
    notes = [
        LabeledNote(a.note.start_s, a.note.end_s, float(a.note.pitch_midi), a.string)
        for a in fretting.assignments
    ]
    notes += [
        LabeledNote(u.note.start_s, u.note.end_s, float(u.note.pitch_midi), None)
        for u in fretting.unassigned
    ]
    notes.sort(key=lambda n: (n.onset_s, n.pitch_midi))
    return notes, transcription_version("guitar")


@dataclass
class TrackReport:
    track_id: str
    scores: dict
    string_mapping: str
    tab_unavailable_reason: str | None = None


@dataclass
class Report:
    dataset: str
    subset: str
    data_dir: str
    commit: str
    model_version: str
    onset_tolerance_s: float = ONSET_TOLERANCE_S
    pitch_tolerance_cents: float = PITCH_TOLERANCE_CENTS
    tracks: list[TrackReport] = field(default_factory=list)
    mean: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = dict(self.__dict__)
        data["tracks"] = [dict(t.__dict__) for t in self.tracks]
        return data


def _git_commit() -> str:
    try:
        sha = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain",
             "--untracked-files=no"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return f"{sha}-dirty" if dirty else sha


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def evaluate(
    dataset: str,
    track_ids: list[str],
    data_dir: Path,
    subset_name: str,
    estimator: Estimator = pipeline_estimator,
) -> Report:
    """Score every track of the subset; tab-F1 mean skips tracks without strings."""
    report = Report(
        dataset=dataset,
        subset=subset_name,
        data_dir=str(data_dir),
        commit=_git_commit(),
        model_version="",
    )
    for track_id in track_ids:
        paths = loaders.track_paths(dataset, data_dir, track_id)
        reference = loaders.load_reference(dataset, paths.annotation)
        estimate, model_version = estimator(paths.audio)
        report.model_version = model_version
        scores = score(reference.notes, estimate).to_dict()
        if reference.tab_unavailable_reason is not None:
            for key in ("tab_precision", "tab_recall", "tab_f1", "n_tab_correct"):
                scores[key] = None
        report.tracks.append(
            TrackReport(
                track_id, scores, reference.string_mapping,
                reference.tab_unavailable_reason,
            )
        )
    for key in ("note_precision", "note_recall", "note_f1",
                "tab_precision", "tab_recall", "tab_f1"):
        values = [t.scores[key] for t in report.tracks if t.scores[key] is not None]
        report.mean[key] = _mean(values)
    report.mean["n_tracks"] = len(report.tracks)
    report.mean["n_tracks_with_tab"] = sum(
        1 for t in report.tracks if t.scores["tab_f1"] is not None
    )
    return report


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def to_markdown(report: Report) -> str:
    mean = report.mean
    lines = [
        f"# Eval: {report.dataset} / {report.subset}",
        "",
        f"- commit: `{report.commit}`",
        f"- model: `{report.model_version}`",
        f"- matching: onset +-{report.onset_tolerance_s * 1000:.0f} ms, "
        f"pitch +-{report.pitch_tolerance_cents:.0f} cents, no offset criterion",
        f"- tracks: {mean['n_tracks']} (with tab annotation: "
        f"{mean['n_tracks_with_tab']})",
        "",
        "| | note P | note R | note F1 | tab P | tab R | tab F1 |",
        "|---|---|---|---|---|---|---|",
        "| **mean** | " + " | ".join(
            _fmt(mean[k]) for k in ("note_precision", "note_recall", "note_f1",
                                    "tab_precision", "tab_recall", "tab_f1")
        ) + " |",
    ]
    for t in report.tracks:
        s = t.scores
        lines.append(
            f"| {t.track_id} | " + " | ".join(
                _fmt(s[k]) for k in ("note_precision", "note_recall", "note_f1",
                                     "tab_precision", "tab_recall", "tab_f1")
            ) + " |"
        )
    lines += ["", "| track | ref | est | matched | tab correct | string mapping |",
              "|---|---|---|---|---|---|"]
    for t in report.tracks:
        s = t.scores
        mapping = t.string_mapping
        if t.tab_unavailable_reason:
            mapping += f"; tab n/a: {t.tab_unavailable_reason}"
        lines.append(
            f"| {t.track_id} | {s['n_ref']} | {s['n_est']} | {s['n_matched']} | "
            f"{s['n_tab_correct'] if s['n_tab_correct'] is not None else 'n/a'} | "
            f"{mapping} |"
        )
    return "\n".join(lines) + "\n"


def write_report(report: Report, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{report.dataset}-{report.subset}"
    json_path = out_dir / f"{stem}.json"
    md_path = out_dir / f"{stem}.md"
    json_path.write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(to_markdown(report), encoding="utf-8")
    return json_path, md_path


def default_data_dir(dataset: str) -> Path:
    root = os.environ.get("TABGEN_DATASETS")
    base = Path(root) if root else Path.home() / "datasets" / "tabgen"
    return base / dataset


def _say(message: str) -> None:
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


def main(
    argv: list[str] | None = None, estimator: Estimator = pipeline_estimator
) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dataset", choices=DATASETS, required=True)
    parser.add_argument("--subset", type=Path, required=True,
                        help="versioned subset file (one track id per line)")
    parser.add_argument("--data-dir", type=Path, default=None,
                        help="dataset root outside the repo (default: "
                             "$TABGEN_DATASETS/<dataset> or "
                             "~/datasets/tabgen/<dataset>)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="report directory (default: scripts/eval/reports)")
    parser.add_argument("--download", action="store_true",
                        help="print URL and size of the missing subset files")
    parser.add_argument("--yes", action="store_true",
                        help="with --download: confirm and actually download")
    args = parser.parse_args(argv)

    data_dir = (args.data_dir or default_data_dir(args.dataset)).expanduser().resolve()
    track_ids = loaders.read_subset(args.subset)
    if not track_ids:
        parser.error(f"empty subset: {args.subset}")

    if args.download:
        planned = download.plan(args.dataset, track_ids, data_dir)
        if not planned:
            _say(f"all {len(track_ids)} tracks already present in {data_dir}")
        else:
            _say(download.describe(planned))
            if not args.yes:
                _say("nothing downloaded; rerun with --download --yes to confirm")
                return 0
            download.execute(planned)
            _say(f"downloaded {len(planned)} file(s) into {data_dir}")

    missing = []
    for track_id in track_ids:
        paths = loaders.track_paths(args.dataset, data_dir, track_id)
        missing += [p for p in (paths.audio, paths.annotation) if not p.is_file()]
    if missing:
        _say(f"{len(missing)} file(s) missing under {data_dir}, e.g. {missing[0]}")
        _say("run with --download to see what would be fetched")
        return 2

    report = evaluate(args.dataset, track_ids, data_dir, args.subset.stem, estimator)
    json_path, md_path = write_report(report, args.out)
    mean = report.mean
    _say(f"{args.dataset}/{args.subset.stem}: {mean['n_tracks']} tracks, "
         f"mean note-F1 {_fmt(mean['note_f1'])}, mean tab-F1 {_fmt(mean['tab_f1'])}")
    _say(f"report: {json_path} and {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
