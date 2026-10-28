"""Entry point: ``python -m tabgen.worker`` (protocol in ``tabgen.worker``)."""

from __future__ import annotations

import os
import sys

from tabgen.worker import run


def main() -> int:
    # Keep fd 1 for the NDJSON stream only: duplicate it for our own writes,
    # then point fd 1 at stderr so native libraries and child processes
    # that write to stdout cannot corrupt the stream.
    sys.stdout.flush()
    ndjson = os.fdopen(os.dup(1), "w", encoding="utf-8")
    os.dup2(2, 1)
    try:
        return run(sys.stdin, ndjson)
    finally:
        ndjson.close()


if __name__ == "__main__":
    raise SystemExit(main())
