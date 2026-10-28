"""NDJSON worker: the boundary between the desktop UI and ``tabgen.core``.

A thin layer like ``tabgen.cli``: it parses one request, calls the matching
core function and serializes the outcome. One job per process; cancelling a
job means killing the process (the core has no cooperative cancellation).

Protocol (``python -m tabgen.worker``), one JSON object per line:

- **Request** — exactly one line on stdin::

      {"cmd": "doctor" | "analyze" | "transcribe" | "tablature", "args": {...}}

  ``args`` is optional (default ``{}``); unknown keys are rejected. Keys per
  ``cmd``, mirroring the core functions (``?`` = optional, core default):

  - ``doctor``: none (:func:`tabgen.core.doctor.run_checks`).
  - ``analyze``: ``input`` (str), ``device``? (str)
    (:func:`tabgen.core.pipeline.run_analysis`).
  - ``transcribe``: ``input`` (str), ``instruments``? (list of str),
    ``device``? (str), ``output_dir``? (str), ``guitar_type``? (str),
    ``transcriber``? (str) (:func:`tabgen.core.pipeline.run_transcription`).
  - ``tablature``: ``input`` (str), ``output``? (str, default
    ``<input>.gp5``), ``format``? (``gp5`` | ``musicxml`` | ``ascii``, default
    from the ``output`` suffix), ``instruments``? (list of str),
    ``tunings``? (object: instrument -> preset name, comma-separated notes
    or list of MIDI ints, resolved by ``resolve_tuning``), ``capos``?
    (object: instrument -> int), ``device``? (str), ``techniques``? (bool),
    ``guitar_type``? (str), ``transcriber``? (str)
    (:func:`tabgen.core.pipeline.run_tablature`).

- **Progress** — zero or more lines on stdout, one per ``on_progress`` call
  of the core, unchanged::

      {"type": "progress", "stage": "<core stage name>", "pct": 0.0-100.0}

- **End** — exactly one last line on stdout, then the exit code:

  - ``{"type": "result", ...}`` and exit 0. The other keys are the core
    summary as a plain dict (``DoctorReport.to_dict()``; ``asdict`` of
    ``AnalysisSummary`` / ``TranscriptionSummary`` / ``TablatureSummary``).
    ``tablature`` adds ``ascii_preview``: ``render_ascii_tab`` of the scores.
  - ``{"type": "error", "kind": "<exception class name>", "message": "..."}``
    and exit 1. A malformed request has kind ``RequestError``.

Stdout carries nothing but these lines: anything else written to it while a
job runs (core logs, third-party prints) is sent to stderr.
"""

from __future__ import annotations

import contextlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Mapping, TextIO

Emit = Callable[[dict[str, Any]], None]

COMMANDS = ("doctor", "analyze", "transcribe", "tablature")


class RequestError(ValueError):
    """The request line is not valid JSON or does not match the protocol."""


def _check_keys(args: Mapping[str, Any], allowed: set[str], required: set[str]) -> None:
    unknown = sorted(set(args) - allowed)
    if unknown:
        raise RequestError(f"unknown args: {', '.join(unknown)}")
    missing = sorted(required - set(args))
    if missing:
        raise RequestError(f"missing args: {', '.join(missing)}")


def _str(args: Mapping[str, Any], key: str) -> str | None:
    value = args.get(key)
    if value is not None and not isinstance(value, str):
        raise RequestError(f"{key} must be a string")
    return value


def _str_list(args: Mapping[str, Any], key: str) -> list[str] | None:
    value = args.get(key)
    if value is None:
        return None
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) for item in value)
    ):
        raise RequestError(f"{key} must be a non-empty list of strings")
    return value


def _object(args: Mapping[str, Any], key: str) -> dict[str, Any]:
    value = args.get(key, {})
    if not isinstance(value, dict):
        raise RequestError(f"{key} must be an object")
    return value


def _doctor(args: Mapping[str, Any], emit: Emit, stage_fns: Mapping[str, Any]) -> dict:
    from tabgen.core.doctor import run_checks

    _check_keys(args, set(), set())
    return run_checks().to_dict()


def _analyze(args: Mapping[str, Any], emit: Emit, stage_fns: Mapping[str, Any]) -> dict:
    from tabgen.core.pipeline import run_analysis

    _check_keys(args, {"input", "device"}, {"input"})
    summary = run_analysis(
        _str(args, "input"),
        device=_str(args, "device"),
        on_progress=_progress(emit),
        **stage_fns,
    )
    return asdict(summary)


def _transcribe(
    args: Mapping[str, Any], emit: Emit, stage_fns: Mapping[str, Any]
) -> dict:
    from tabgen.core.pipeline import run_transcription

    _check_keys(
        args,
        {"input", "instruments", "device", "output_dir", "guitar_type", "transcriber"},
        {"input"},
    )
    kwargs: dict[str, Any] = {}
    for key in ("instruments", "transcriber"):
        value = _str_list(args, key) if key == "instruments" else _str(args, key)
        if value is not None:
            kwargs[key] = value
    summary = run_transcription(
        _str(args, "input"),
        device=_str(args, "device"),
        output_dir=_str(args, "output_dir"),
        guitar_type=_str(args, "guitar_type"),
        on_progress=_progress(emit),
        **kwargs,
        **stage_fns,
    )
    return asdict(summary)


def _tablature(
    args: Mapping[str, Any], emit: Emit, stage_fns: Mapping[str, Any]
) -> dict:
    from tabgen.core.export.ascii_tab import render_ascii_tab
    from tabgen.core.pipeline import (
        TABLATURE_INSTRUMENTS,
        resolve_export_format,
        resolve_tuning,
        run_tablature,
    )

    _check_keys(
        args,
        {
            "input",
            "output",
            "format",
            "instruments",
            "tunings",
            "capos",
            "device",
            "techniques",
            "guitar_type",
            "transcriber",
        },
        {"input"},
    )
    input_path = Path(_str(args, "input"))
    output = _str(args, "output") or str(input_path.with_suffix(".gp5"))
    instruments = _str_list(args, "instruments") or list(TABLATURE_INSTRUMENTS)
    tunings = {
        name: resolve_tuning(spec, name)
        for name, spec in _object(args, "tunings").items()
    }
    capos = _object(args, "capos")
    if not all(
        isinstance(fret, int) and not isinstance(fret, bool) for fret in capos.values()
    ):
        raise RequestError("capos values must be integers")
    techniques = args.get("techniques", True)
    if not isinstance(techniques, bool):
        raise RequestError("techniques must be a boolean")
    kwargs: dict[str, Any] = {}
    for key in ("guitar_type", "transcriber"):
        value = _str(args, key)
        if value is not None:
            kwargs[key] = value

    summary = run_tablature(
        input_path,
        output_path=output,
        fmt=resolve_export_format(output, _str(args, "format")),
        instruments=instruments,
        tunings=tunings,
        capos=capos,
        device=_str(args, "device"),
        on_progress=_progress(emit),
        techniques=techniques,
        **kwargs,
        **stage_fns,
    )
    result = asdict(summary)
    result["ascii_preview"] = render_ascii_tab(summary.scores, summary.beat_grids)
    return result


_HANDLERS = {
    "doctor": _doctor,
    "analyze": _analyze,
    "transcribe": _transcribe,
    "tablature": _tablature,
}


def _progress(emit: Emit) -> Callable[[str, float], None]:
    def on_progress(stage: str, pct: float) -> None:
        emit({"type": "progress", "stage": stage, "pct": pct})

    return on_progress


def parse_request(line: str) -> tuple[str, dict[str, Any]]:
    """Validate one request line and return ``(cmd, args)``."""
    try:
        request = json.loads(line)
    except json.JSONDecodeError as err:
        raise RequestError(f"request is not valid JSON: {err}") from err
    if not isinstance(request, dict):
        raise RequestError("request must be a JSON object")
    unknown = sorted(set(request) - {"cmd", "args"})
    if unknown:
        raise RequestError(f"unknown request keys: {', '.join(unknown)}")
    cmd = request.get("cmd")
    if cmd not in COMMANDS:
        raise RequestError(f"unknown cmd {cmd!r}; choose one of {', '.join(COMMANDS)}")
    args = request.get("args", {})
    if not isinstance(args, dict):
        raise RequestError("args must be a JSON object")
    return cmd, args


def run(
    stdin: TextIO,
    stdout: TextIO,
    stage_fns: Mapping[str, Any] | None = None,
) -> int:
    """Serve one request from ``stdin``, writing NDJSON to ``stdout``.

    ``stage_fns`` are extra keyword arguments for the core ``run_*`` call
    (``separate_fn``, ``transcribe_fn``, ``analysis_fn``...), for dependency
    injection in tests. Returns the exit code (0 result, 1 error).
    """

    def emit(message: dict[str, Any]) -> None:
        # allow_nan=False: NaN/Infinity are not JSON; such a payload fails
        # the job instead of breaking the reader.
        stdout.write(json.dumps(message, allow_nan=False) + "\n")
        stdout.flush()

    # Anything printed while the job runs goes to stderr, never into the
    # NDJSON stream.
    with contextlib.redirect_stdout(sys.stderr):
        try:
            cmd, args = parse_request(stdin.readline())
            payload = _HANDLERS[cmd](args, emit, stage_fns or {})
            emit({"type": "result", **payload})
        except Exception as err:  # noqa: BLE001 - every failure becomes an error line
            emit({"type": "error", "kind": type(err).__name__, "message": str(err)})
            return 1
    return 0
