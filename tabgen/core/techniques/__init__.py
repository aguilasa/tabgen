"""Guitar technique detection from transcribed notes (pure, no I/O)."""

from tabgen.core.techniques.bends import (
    BASIC_PITCH_BINS_PER_SEMITONE,
    BASIC_PITCH_FPS,
    BendConfig,
    detect_bends_and_slides,
)
from tabgen.core.techniques.legato import LegatoConfig, detect_legato

__all__ = [
    "BASIC_PITCH_BINS_PER_SEMITONE",
    "BASIC_PITCH_FPS",
    "BendConfig",
    "LegatoConfig",
    "detect_bends_and_slides",
    "detect_legato",
]
