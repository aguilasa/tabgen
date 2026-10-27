"""Fretting stage: place note events on (string, fret) via dynamic programming."""

from tabgen.core.fretting.dp import (
    CHORD_SHAPES,
    FrettedNote,
    FrettingConfig,
    FrettingResult,
    UnassignedNote,
    assign_frets,
    bass_config,
    guitar_config,
)

__all__ = [
    "CHORD_SHAPES",
    "FrettedNote",
    "FrettingConfig",
    "FrettingResult",
    "UnassignedNote",
    "assign_frets",
    "bass_config",
    "guitar_config",
]
