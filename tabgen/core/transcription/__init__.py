"""Transcription stage: Basic Pitch (ONNX backend) and, for the guitar, the
hybrid Riley model in :mod:`tabgen.core.transcription.riley` (imported on
demand: it needs torch)."""

from tabgen.core.transcription.basic_pitch import (
    INSTRUMENT_PROFILES,
    MODEL_VERSION,
    InstrumentProfile,
    TranscriptionError,
    TranscriptionResult,
    transcribe,
)

__all__ = [
    "INSTRUMENT_PROFILES",
    "MODEL_VERSION",
    "InstrumentProfile",
    "TranscriptionError",
    "TranscriptionResult",
    "transcribe",
]
