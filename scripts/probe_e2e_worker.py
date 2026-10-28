"""Standalone end-to-end probe for the UI's worker path (FIX-UI-004).

Regenerates the verification sample deterministically (sine 220 Hz, 10 s, mp3)
with ffmpeg in a fresh temporary directory (so the ``.tabgen/`` cache next to
the input starts cold), sends ``{"cmd": "tablature", "args": {"input": ...}}``
to ``python -m tabgen.worker`` twice — one process per request, exactly like
the desktop UI (``desktop/src/lib/worker.ts``) — and asserts only the facts
that are stable across runs/encoders:

- both worker processes exit 0 and write nothing but NDJSON on stdout
  (every line parses as a JSON object with a ``type``);
- the last line of each run is a ``result``; every other line is a
  ``progress`` whose ``stage`` order follows ``_tablature_stages`` of the
  core pipeline plus the final ``export`` stage (order of first appearance:
  on a cold run ``_compute_tablature`` re-reports ``separation`` when it
  fetches the stems the analysis already separated, so a stage may show up
  again, but never a NEW stage out of order);
- the first (cold) run reports ``cache_hit: false`` and the second (warm)
  run ``cache_hit: true``, finishing in under 5 s wall clock;
- the exported .gp5 exists next to the sample.

Wall-clock times of both runs are printed; only the warm one is asserted
(<5 s). Note counts are deliberately NOT asserted (same policy as
probe_e2e_sample.py).

Not collected by pytest; run it directly:

    .venv/bin/python scripts/probe_e2e_worker.py

The cold run is slow (Demucs separation; ~1 min on GPU, longer on CPU).
Dependencies: the project venv (the worker runs under it) and an ``ffmpeg``
binary on PATH. Everything is written to a temporary directory, nothing to
the repo.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from tabgen.core.pipeline import TABLATURE_INSTRUMENTS, _tablature_stages

REPO_ROOT = Path(__file__).resolve().parent.parent
PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
WARM_BUDGET_S = 5.0
EXPECTED_STAGES = [*_tablature_stages(TABLATURE_INSTRUMENTS), "export"]


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


def run_worker(sample: Path, step: str) -> tuple[list[dict], float]:
    """One worker process, one tablature request; parsed NDJSON + wall time."""
    request = json.dumps({"cmd": "tablature", "args": {"input": str(sample)}})
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


def main() -> None:
    if not PYTHON.is_file():
        fail(f"{PYTHON} not found; install the project venv first")

    with tempfile.TemporaryDirectory(prefix="tabgen-probe-") as tmp:
        tmp_dir = Path(tmp)
        sample = generate_sample(tmp_dir)

        say("cold run (fresh temp dir, empty .tabgen cache; Demucs is slow)...")
        messages, cold_s = run_worker(sample, "cold tablature run")
        cold = check_run(messages, "cold run")
        if cold.get("cache_hit") is not False:
            fail(f"cold run cache_hit is {cold.get('cache_hit')!r}, expected false")
        gp5 = tmp_dir / "sample.gp5"
        if not gp5.is_file():
            fail(f"cold run reported a result but {gp5.name} was not written")
        say(f"cold run OK in {cold_s:.1f} s (not asserted)")

        say("warm run (same process arguments, cache populated)...")
        messages, warm_s = run_worker(sample, "warm tablature run")
        warm = check_run(messages, "warm run")
        if warm.get("cache_hit") is not True:
            fail(f"warm run cache_hit is {warm.get('cache_hit')!r}, expected true")
        if warm_s >= WARM_BUDGET_S:
            fail(f"warm run took {warm_s:.2f} s (budget < {WARM_BUDGET_S:.0f} s)")

    say(
        "PASS: two worker runs exit 0 with NDJSON-only stdout; stage order "
        "follows _tablature_stages + export in both; cold run cache_hit=false "
        f"in {cold_s:.1f} s (not asserted), warm run cache_hit=true in "
        f"{warm_s:.2f} s (< {WARM_BUDGET_S:.0f} s); .gp5 written."
    )


if __name__ == "__main__":
    main()
