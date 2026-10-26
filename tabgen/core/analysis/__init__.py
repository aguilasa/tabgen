"""Musical-analysis stages (beats/tempo, key, chords).

Each stage returns a partial result the caller merges into
:class:`~tabgen.core.models.AnalysisResult`.
"""

from tabgen.core.analysis.beats import (
    BeatAnalysis,
    BeatAnalysisError,
    analyze_beats,
)

__all__ = [
    "BeatAnalysis",
    "BeatAnalysisError",
    "analyze_beats",
]
