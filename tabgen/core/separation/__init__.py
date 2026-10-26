"""Source-separation stage (Demucs)."""

from tabgen.core.separation.demucs import (
    MODEL_VERSION,
    STEM_NAMES,
    SeparationError,
    separate,
)

__all__ = ["MODEL_VERSION", "STEM_NAMES", "SeparationError", "separate"]
