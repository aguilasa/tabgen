"""Separation from stems the user already has (e.g. exported by Moises).

:func:`prepared_separate` builds a drop-in replacement for
:func:`tabgen.core.separation.demucs.separate`: when every requested
instrument has a user stem, Demucs never runs and the stems are returned as
given; otherwise the fallback separator runs and the user stems override its
output. :func:`stems_tag` is the cache-version tag that replaces the Demucs
model version in the analysis and tablature cache keys.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from tabgen.core.cache import _sha256_of_file
from tabgen.core.models import SeparationResult

USER_STEMS_MODEL = "user-stems"

# Name under which the input audio joins the stems handed to the harmony
# stage when it is not itself one of the user stems.
MIX_STEM = "mix"

_SeparateFn = Callable[..., tuple[SeparationResult, bool]]


class PreparedStemsError(ValueError):
    """A user stem is invalid (unknown instrument or missing file)."""


def check_user_stems(
    user_stems: Mapping[str, str | Path], allowed: Sequence[str]
) -> dict[str, Path]:
    """Validate instrument names and files; return resolved paths."""
    checked: dict[str, Path] = {}
    for name, path in user_stems.items():
        if name not in allowed:
            raise PreparedStemsError(
                f"unsupported stem instrument {name!r}; choose from "
                f"{', '.join(allowed)}"
            )
        resolved = Path(path).expanduser().resolve()
        if not resolved.is_file():
            raise PreparedStemsError(f"stem file not found: {path}")
        checked[name] = resolved
    return checked


def covers(user_stems: Mapping[str, object], instruments: Sequence[str]) -> bool:
    """True when every requested instrument has a user stem (no Demucs)."""
    return all(name in user_stems for name in instruments)


def stems_tag(
    user_stems: Mapping[str, str | Path], uses_demucs: bool
) -> str:
    """Short cache tag: digest of each stem's instrument and content.

    When Demucs still runs (some instrument has no user stem) the Demucs
    model version is part of the digest, so the tag also changes with it.
    """
    from tabgen.core.separation.demucs import MODEL_VERSION

    parts = [
        f"{name}={_sha256_of_file(Path(path))}"
        for name, path in sorted(user_stems.items())
    ]
    if uses_demucs:
        parts.append(MODEL_VERSION)
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:10]
    return f"stems-{digest}"


def prepared_separate(
    user_stems: Mapping[str, str | Path],
    instruments: Sequence[str],
    fallback: _SeparateFn | None = None,
) -> _SeparateFn:
    """Return a separate_fn that serves ``user_stems``.

    All ``instruments`` covered: ``fallback`` is never called and the input
    audio is added as stem ``mix`` (unless it is one of the user stems), so
    the harmony stage still hears the whole song. Otherwise ``fallback``
    (default: Demucs) separates the input and the user stems replace its
    stems of the same name.
    """
    stems = {name: str(Path(path)) for name, path in user_stems.items()}
    full = covers(stems, instruments)

    def separate(input_path, device=None, on_progress=None, **kwargs):
        if full:
            if on_progress is not None:
                on_progress("separation", 100.0)
            result = dict(stems)
            input_resolved = str(Path(input_path).expanduser().resolve())
            if input_resolved not in {str(Path(p).resolve()) for p in result.values()}:
                result[MIX_STEM] = str(input_path)
            return SeparationResult(stems=result, model_version=USER_STEMS_MODEL), True
        sep = fallback
        if sep is None:
            from tabgen.core.separation.demucs import separate as sep
        call_kwargs = dict(kwargs)
        if on_progress is not None:
            call_kwargs["on_progress"] = on_progress
        separation, hit = sep(input_path, device=device, **call_kwargs)
        merged = dict(separation.stems)
        merged.update(stems)
        return (
            SeparationResult(
                stems=merged,
                sample_rate=separation.sample_rate,
                model_version=f"{separation.model_version}+{USER_STEMS_MODEL}",
            ),
            hit,
        )

    return separate
