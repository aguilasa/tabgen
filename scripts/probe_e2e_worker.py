"""Standalone end-to-end probe for the UI's worker path (FIX-UI-004, FIX-UI-008).

Regenerates the verification sample deterministically (sine 220 Hz, 10 s, mp3)
with ffmpeg in a fresh temporary directory (so the ``.tabgen/`` cache next to
the input starts cold) and sends ``{"cmd": "tablature", ...}`` requests to
``python -m tabgen.worker`` — one process per request, exactly like the
desktop UI (``desktop/src/lib/worker.ts``). Five runs, asserting only the
facts that are stable across runs/encoders.

Every run must exit 0 and write nothing but NDJSON on stdout (every line
parses as a JSON object with a ``type``); the last line is a ``result``,
every other line a ``progress`` whose ``stage`` order of first appearance
follows ``_tablature_stages`` of the core pipeline plus the final ``export``
stage (on a cold run ``_compute_tablature`` re-reports ``separation`` when it
fetches the stems the analysis already separated, so a stage may show up
again, but never a NEW stage out of order). On top of that shape:

1. cold run (``transcriber: basic-pitch``): ``cache_hit: false``; the
   exported .gp5 exists next to the sample (FIX-UI-004);
2. warm run (same args): ``cache_hit: true`` in under 5 s wall clock
   (FIX-UI-004);
3. transcriber switch (``transcriber: riley``, UI-TASK-06): invalidates only
   the transcription of the guitar — ``cache_hit: false`` overall, while the
   analysis stages and ``transcription:bass`` are stage-cache hits (their
   first reported pct is already 100.0) and ``transcription:guitar`` re-runs
   (first pct below 100.0);
4. options run (``tunings: {"guitar": "drop-d"}``, ``capos: {"guitar": 2}``,
   ``guitar_type: "nylon"``, UI-TASK-06): the exported .gp5, reopened with
   ``guitarpro.parse``, has strings ``[64, 59, 55, 50, 45, 38]`` (drop-d
   low-to-high reversed: GP5 lists string 1 = highest pitch first), capo
   ``offset == 2`` and GM program ``24`` (Acoustic Guitar nylon, 0-based);
5. warm options run (same args as 4, UI-TASK-06): the tablature cache
   answers with ``cache_hit: true`` in under 5 s wall clock.

Wall-clock times of every run are printed; only the warm ones (2 and 5) are
asserted (< 5 s). Note counts are deliberately NOT asserted (same policy as
probe_e2e_sample.py).

Not collected by pytest; run it directly:

    .venv/bin/python scripts/probe_e2e_worker.py

The cold run is slow (Demucs separation; ~1 min on GPU, longer on CPU) and
the transcriber switch re-runs the riley guitar transcription. Dependencies:
the project venv (the worker runs under it, and ``guitarpro`` reopens the
.gp5) and an ``ffmpeg`` binary on PATH. Everything is written to a temporary
directory, nothing to the repo.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import guitarpro

from tabgen.core.pipeline import (
    ANALYSIS_STAGES,
    TABLATURE_INSTRUMENTS,
    _tablature_stages,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
WARM_BUDGET_S = 5.0
EXPECTED_STAGES = [*_tablature_stages(TABLATURE_INSTRUMENTS), "export"]

# UI-TASK-06 numbers for the drop-d + capo 2 + nylon export, read back from
# the .gp5: open strings as GP5 lists them (string 1 = highest pitch first,
# so drop-d low-to-high reversed), capo fret and GM program (0-based).
DROP_D_GP5_STRINGS = [64, 59, 55, 50, 45, 38]
OPTIONS_CAPO = 2
NYLON_GM_PROGRAM = 24
OPTIONS_ARGS = {
    "tunings": {"guitar": "drop-d"},
    "capos": {"guitar": OPTIONS_CAPO},
    "guitar_type": "nylon",
}

# Stages the transcriber switch must answer from the stage caches: everything
# that runs before transcription, plus the bass (basic-pitch either way).
SWITCH_CACHED_STAGES = [*ANALYSIS_STAGES, "transcription:bass"]


def say(message: str) -> None:
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


def fail(message: str) -> None:
    sys.exit(f"FAIL: {message}")


def generate_sample(directory: Path) -> Path:
    sample = directory / "sample.mp3"
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=220:duration=10",
            "-q:a",
            "2",
            str(sample),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail(
            f"ffmpeg sample generation exited {result.returncode}\n"
            f"stderr: {result.stderr.strip()[-500:]}"
        )
    if not sample.is_file():
        fail(f"ffmpeg exited 0 but {sample} was not written")
    return sample


def run_worker(
    sample: Path, step: str, extra_args: dict | None = None
) -> tuple[list[dict], float]:
    """One worker process, one tablature request; parsed NDJSON + wall time."""
    args = {"input": str(sample), **(extra_args or {})}
    request = json.dumps({"cmd": "tablature", "args": args})
    start = time.monotonic()
    result = subprocess.run(
        [str(PYTHON), "-m", "tabgen.worker"],
        input=request + "\n",
        capture_output=True,
        text=True,
    )
    elapsed = time.monotonic() - start
    if result.returncode != 0:
        fail(
            f"{step} exited {result.returncode}\n"
            f"stdout tail: {result.stdout.strip()[-500:]}\n"
            f"stderr tail: {result.stderr.strip()[-500:]}"
        )
    messages: list[dict] = []
    for number, line in enumerate(result.stdout.splitlines(), start=1):
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            fail(f"{step}: stdout line {number} is not JSON (NDJSON only): {line!r}")
        if not isinstance(message, dict) or "type" not in message:
            fail(f"{step}: stdout line {number} is not a protocol object: {line!r}")
        messages.append(message)
    return messages, elapsed


def check_run(messages: list[dict], step: str) -> dict:
    """Assert the NDJSON shape and stage order; return the result line."""
    if not messages:
        fail(f"{step}: worker wrote nothing on stdout")
    end = messages[-1]
    if end.get("type") != "result":
        fail(f"{step}: last stdout line is not a result: {end}")
    first_seen: list[str] = []
    for message in messages[:-1]:
        if message.get("type") != "progress":
            fail(f"{step}: non-progress line before the result: {message}")
        stage = message.get("stage")
        if stage not in first_seen:
            first_seen.append(stage)
    if first_seen != EXPECTED_STAGES:
        fail(
            f"{step}: stage order (first appearance) diverges from "
            f"_tablature_stages + export\n"
            f"expected: {EXPECTED_STAGES}\n"
            f"got:      {first_seen}"
        )
    return end


def first_pcts(messages: list[dict]) -> dict[str, float]:
    """First reported pct per stage (100.0 right away = stage cache hit)."""
    seen: dict[str, float] = {}
    for message in messages[:-1]:
        seen.setdefault(message.get("stage"), message.get("pct"))
    return seen


def check_switch_invalidation(messages: list[dict], step: str) -> None:
    """The switch re-runs only the guitar transcription (UI-TASK-06)."""
    pcts = first_pcts(messages)
    for stage in SWITCH_CACHED_STAGES:
        if pcts.get(stage) != 100.0:
            fail(
                f"{step}: stage {stage!r} first pct is {pcts.get(stage)!r}, "
                f"expected 100.0 (stage-cache hit)"
            )
    guitar_pct = pcts.get("transcription:guitar")
    if guitar_pct is None or guitar_pct >= 100.0:
        fail(
            f"{step}: transcription:guitar first pct is {guitar_pct!r}, "
            f"expected below 100.0 (the switch must re-run it)"
        )


def check_options_gp5(gp5: Path, step: str) -> str:
    """Reopen the drop-d + capo 2 + nylon export; return the read numbers."""
    track = guitarpro.parse(str(gp5)).tracks[0]
    strings = [string.value for string in track.strings]
    numbers = f"{strings} {track.offset} {track.channel.instrument}"
    if strings != DROP_D_GP5_STRINGS:
        fail(
            f"{step}: .gp5 strings are {strings}, expected {DROP_D_GP5_STRINGS} "
            f"(drop-d as GP5 lists it, highest string first)"
        )
    if track.offset != OPTIONS_CAPO:
        fail(f"{step}: .gp5 capo (offset) is {track.offset}, expected {OPTIONS_CAPO}")
    if track.channel.instrument != NYLON_GM_PROGRAM:
        fail(
            f"{step}: .gp5 GM program is {track.channel.instrument}, "
            f"expected {NYLON_GM_PROGRAM} (Acoustic Guitar nylon, 0-based)"
        )
    return numbers


def main() -> None:
    if not PYTHON.is_file():
        fail(f"{PYTHON} not found; install the project venv first")

    with tempfile.TemporaryDirectory(prefix="tabgen-probe-") as tmp:
        tmp_dir = Path(tmp)
        sample = generate_sample(tmp_dir)

        say("cold run (fresh temp dir, empty .tabgen cache; Demucs is slow)...")
        base_args = {"transcriber": "basic-pitch"}
        messages, cold_s = run_worker(sample, "cold tablature run", base_args)
        cold = check_run(messages, "cold run")
        if cold.get("cache_hit") is not False:
            fail(f"cold run cache_hit is {cold.get('cache_hit')!r}, expected false")
        gp5 = tmp_dir / "sample.gp5"
        if not gp5.is_file():
            fail(f"cold run reported a result but {gp5.name} was not written")
        say(f"cold run OK in {cold_s:.1f} s (not asserted)")

        say("warm run (same process arguments, cache populated)...")
        messages, warm_s = run_worker(sample, "warm tablature run", base_args)
        warm = check_run(messages, "warm run")
        if warm.get("cache_hit") is not True:
            fail(f"warm run cache_hit is {warm.get('cache_hit')!r}, expected true")
        if warm_s >= WARM_BUDGET_S:
            fail(f"warm run took {warm_s:.2f} s (budget < {WARM_BUDGET_S:.0f} s)")
        say(f"warm run OK in {warm_s:.2f} s")

        say("transcriber switch run (riley; re-runs the guitar transcription)...")
        messages, switch_s = run_worker(
            sample, "transcriber switch run", {"transcriber": "riley"}
        )
        switch = check_run(messages, "transcriber switch run")
        if switch.get("cache_hit") is not False:
            fail(
                f"transcriber switch run cache_hit is "
                f"{switch.get('cache_hit')!r}, expected false (new transcriber)"
            )
        check_switch_invalidation(messages, "transcriber switch run")
        say(
            f"transcriber switch OK in {switch_s:.1f} s (not asserted): "
            f"analysis + transcription:bass cached, transcription:guitar re-ran"
        )

        say("options run (drop-d + capo 2 + nylon; fretting recomputes)...")
        options_gp5 = tmp_dir / "options.gp5"
        options_args = {"output": str(options_gp5), **OPTIONS_ARGS}
        messages, options_s = run_worker(sample, "options run", options_args)
        options = check_run(messages, "options run")
        if options.get("cache_hit") is not False:
            fail(
                f"options run cache_hit is {options.get('cache_hit')!r}, "
                f"expected false (new tuning/capo/guitar_type)"
            )
        if not options_gp5.is_file():
            fail(f"options run reported a result but {options_gp5.name} not written")
        numbers = check_options_gp5(options_gp5, "options run")
        say(f"options .gp5 reopened via guitarpro.parse: {numbers}")
        say(f"options run OK in {options_s:.1f} s (not asserted)")

        say("warm options run (same options, tablature cache)...")
        messages, warm_options_s = run_worker(sample, "warm options run", options_args)
        warm_options = check_run(messages, "warm options run")
        if warm_options.get("cache_hit") is not True:
            fail(
                f"warm options run cache_hit is "
                f"{warm_options.get('cache_hit')!r}, expected true"
            )
        if warm_options_s >= WARM_BUDGET_S:
            fail(
                f"warm options run took {warm_options_s:.2f} s "
                f"(budget < {WARM_BUDGET_S:.0f} s)"
            )
        say(f"warm options run OK in {warm_options_s:.2f} s")

    say(
        "PASS: five worker runs exit 0 with NDJSON-only stdout and stage order "
        "following _tablature_stages + export; cold (basic-pitch) "
        f"cache_hit=false in {cold_s:.1f} s (not asserted), warm cache_hit=true "
        f"in {warm_s:.2f} s (< {WARM_BUDGET_S:.0f} s); transcriber switch to "
        "riley: cache_hit=false, analysis + transcription:bass first pct 100.0, "
        f"transcription:guitar re-ran, in {switch_s:.1f} s (not asserted); "
        f"drop-d + capo 2 + nylon .gp5 reopened as {DROP_D_GP5_STRINGS} "
        f"{OPTIONS_CAPO} {NYLON_GM_PROGRAM} in {options_s:.1f} s (not "
        f"asserted); warm options cache_hit=true in {warm_options_s:.2f} s "
        f"(< {WARM_BUDGET_S:.0f} s)."
    )


if __name__ == "__main__":
    main()
