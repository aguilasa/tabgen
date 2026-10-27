"""Guitar technique detection from transcribed notes (pure, no I/O)."""

from tabgen.core.techniques.bends import (
    BASIC_PITCH_BINS_PER_SEMITONE,
    BASIC_PITCH_FPS,
    BendConfig,
    detect_bends_and_slides,
)

__all__ = [
    "BASIC_PITCH_BINS_PER_SEMITONE",
    "BASIC_PITCH_FPS",
    "BendConfig",
    "detect_bends_and_slides",
]
