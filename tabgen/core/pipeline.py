"""Pipeline primitives shared by the stages.

Only the progress-reporting contract lives here for now; stage
orchestration will be added once the stages themselves exist.
"""

from __future__ import annotations

from typing import Callable

# Called as on_progress(stage, pct) with pct in [0.0, 100.0].
ProgressCallback = Callable[[str, float], None]


def null_progress(stage: str, pct: float) -> None:
    """A ProgressCallback that ignores every update."""
