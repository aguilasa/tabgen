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

``--transcriber riley`` swaps the guitar transcription for tabgen's hybrid
Riley model (``tabgen.core.transcription.riley``: Riley notes, Basic Pitch
bends); its reports default to ``scripts/eval/reports/riley/``. ``--mix``
evaluates on Demucs ``guitar`` stems of the clip mixed with a drums + bass
backing (see :mod:`scripts.eval.mix`); its reports default to
``scripts/eval/reports/mixed/<transcriber>/`` and record the backing of each
clip and the command. Without these options the output is unchanged::

    .venv/bin/python scripts/eval/run.py --dataset egdb \\
        --subset scripts/eval/subsets/egdb.txt --transcriber riley --mix
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
TRANSCRIBERS = ("basic-pitch", "riley")
DEFAULT_OUT = REPO_ROOT / "scripts" / "eval" / "reports"

# Audio path -> estimated notes (with strings). Injectable for tests.
Estimator = Callable[[Path], tuple[list[LabeledNote], str]]


def pipeline_estimator(audio: Path) -> tuple[list[LabeledNote], str]:
    """Basic Pitch transcription + DP fretting (standard guitar tuning)."""
    from tabgen.core.transcription.basic_pitch import transcribe, transcription_version

    result, _ = transcribe(audio, instrument="guitar")
    return _fretted_labels(result.note_events), transcription_version("guitar")


def _fretted_labels(note_events) -> list[LabeledNote]:
    from tabgen.core.fretting import assign_frets, guitar_config

    fretting = assign_frets(note_events, guitar_config())
    notes = [
        LabeledNote(a.note.start_s, a.note.end_s, float(a.note.pitch_midi), a.string)
        for a in fretting.assignments
    ]
    notes += [
        LabeledNote(u.note.start_s, u.note.end_s, float(u.note.pitch_midi), None)
        for u in fretting.unassigned
    ]
    notes.sort(key=lambda n: (n.onset_s, n.pitch_midi))
    return notes


def transcriber_estimator(transcriber: str, device: str | None = None) -> Estimator:
    """Estimator for one of :data:`TRANSCRIBERS`, through tabgen's core stage."""
    if transcriber == "basic-pitch":
        return pipeline_estimator
    from tabgen.core.transcription import riley

    def estimate(audio: Path) -> tuple[list[LabeledNote], str]:
        result, _ = riley.transcribe(audio, instrument="guitar", device=device)
        return _fretted_labels(result.note_events), riley.transcription_version()

    return estimate


def mixed_estimator(
    estimator: Estimator,
    dataset: str,
    track_ids: list[str],
    data_dir: Path,
    musdb_dir: Path,
    mix_dir: Path,
    device: str | None = None,
) -> tuple[Estimator, dict[str, str]]:
    """Wrap ``estimator`` to run on the Demucs guitar stem of each mixed clip.

    Returns the wrapped estimator and the backing track per clip id.
    """
    from scripts.eval import mix

    clips = {}
    for position, track_id in enumerate(track_ids):
        paths = loaders.track_paths(dataset, data_dir, track_id)
        clips[paths.audio] = mix.build_mix(
            dataset, track_id, paths.audio, position, musdb_dir, mix_dir
        )

    def estimate(audio: Path) -> tuple[list[LabeledNote], str]:
        stem = mix.separated_guitar(clips[audio].mix_path, device=device)
        notes, version = estimator(stem)
        from tabgen.core.separation.demucs import MODEL_VERSION

        return notes, f"{version} on {MODEL_VERSION} guitar stem"

    return estimate, {clip.track_id: clip.backing for clip in clips.values()}


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
    # Non-default runs only (--transcriber riley, --mix): transcriber,
    # command, backing per clip. Left out of the output when empty.
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = dict(self.__dict__)
        data["tracks"] = [dict(t.__dict__) for t in self.tracks]
        if not self.extra:
            data.pop("extra")
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
    ]
    extra = report.extra
    if "transcriber" in extra:
        lines.append(f"- transcriber: `{extra['transcriber']}`")
    if "mix" in extra:
        m = extra["mix"]
        lines.append(
            f"- mix: guitar over {m['backing_source']}, guitar-to-backing "
            f"{m['guitar_to_backing_db']:+.1f} dB RMS, separated by Demucs "
            f"(`{m['separation']}`), stem `guitar`"
        )
    if "command" in extra:
        lines.append(f"- command: `{extra['command']}`")
    lines += [
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
    backing = extra.get("mix", {}).get("backing", {})
    for t in report.tracks:
        s = t.scores
        mapping = t.string_mapping
        if t.track_id in backing:
            mapping += f"; backing: {backing[t.track_id]}"
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
    parser.add_argument("--transcriber", choices=TRANSCRIBERS,
                        default="basic-pitch",
                        help="guitar transcription (default: basic-pitch)")
    parser.add_argument("--mix", action="store_true",
                        help="evaluate on the Demucs guitar stem of the clip "
                             "mixed with a MUSDB18 drums + bass backing")
    parser.add_argument("--musdb-dir", type=Path, default=None,
                        help="unzipped MUSDB18-7 (default: "
                             "~/datasets/tabgen/musdb18-7/raw)")
    parser.add_argument("--mix-dir", type=Path, default=None,
                        help="where mixes and stems are written (default: "
                             "~/datasets/tabgen/mixed)")
    parser.add_argument("--device", default=None,
                        help="cuda or cpu for Demucs/Riley (default: autodetect)")
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

    extra: dict = {}
    out_dir = args.out
    if args.transcriber != "basic-pitch" or args.mix:
        if estimator is pipeline_estimator:
            estimator = transcriber_estimator(args.transcriber, args.device)
        extra["transcriber"] = args.transcriber
        extra["command"] = " ".join(
            [".venv/bin/python scripts/eval/run.py",
             *(argv if argv is not None else sys.argv[1:])]
        )
        if out_dir == DEFAULT_OUT:
            out_dir = (DEFAULT_OUT / "mixed" / args.transcriber if args.mix
                       else DEFAULT_OUT / args.transcriber)
    if args.mix:
        from scripts.eval import mix
        from tabgen.core.separation.demucs import MODEL_VERSION

        musdb_dir = (args.musdb_dir or mix.default_musdb_dir()).expanduser().resolve()
        mix_dir = (args.mix_dir or mix.default_mix_dir()).expanduser().resolve()
        estimator, backing = mixed_estimator(
            estimator, args.dataset, track_ids, data_dir, musdb_dir, mix_dir,
            args.device,
        )
        extra["mix"] = {
            "backing_source": mix.BACKING_SOURCE,
            "backing_selection": "sorted(test/*.stem.mp4)[clip position % 50]",
            "guitar_to_backing_db": mix.GUITAR_TO_BACKING_DB,
            "separation": MODEL_VERSION,
            "backing": backing,
        }

    report = evaluate(args.dataset, track_ids, data_dir, args.subset.stem, estimator)
    report.extra = extra
    json_path, md_path = write_report(report, out_dir)
    mean = report.mean
    _say(f"{args.dataset}/{args.subset.stem}: {mean['n_tracks']} tracks, "
         f"mean note-F1 {_fmt(mean['note_f1'])}, mean tab-F1 {_fmt(mean['tab_f1'])}")
    _say(f"report: {json_path} and {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
