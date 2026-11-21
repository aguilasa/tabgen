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
    """A user stem is invalid (unknown instrument, missing or unreadable file)."""


# Folder (inside the input's ``.tabgen/`` cache) for stems normalized to the
# Demucs format: stereo wav at ``TARGET_SAMPLE_RATE``, one file per content.
NORMALIZED_DIR = "user-stems"


def _is_target_wav(path: Path, sample_rate: int) -> bool:
    import soundfile

    try:
        info = soundfile.info(str(path))
    except Exception:  # noqa: BLE001 - any unreadable file gets converted
        return False
    return (
        info.format == "WAV"
        and info.samplerate == sample_rate
        and info.channels == 2
    )


def normalize_audio(path: Path, workdir: Path) -> Path:
    """Return ``path`` as a stereo wav at the Demucs rate, converting if needed.

    The harmony stage sums stems with soundfile and needs one sample rate;
    Demucs output is 44.1 kHz stereo wav, so user stems and the mix are
    brought to the same format (ffmpeg, like the Demucs input). Converted
    files are named after the source content's sha256 and reused.
    """
    from tabgen.core.separation.demucs import (
        TARGET_SAMPLE_RATE,
        SeparationError,
        convert_to_wav,
    )

    if _is_target_wav(path, TARGET_SAMPLE_RATE):
        return path
    workdir.mkdir(parents=True, exist_ok=True)
    target = workdir / f"{_sha256_of_file(path)[:16]}.wav"
    if not target.is_file():
        tmp = target.with_suffix(".tmp.wav")
        try:
            convert_to_wav(path, tmp, TARGET_SAMPLE_RATE)
        except SeparationError as err:
            raise PreparedStemsError(f"cannot decode {path}: {err}") from err
        tmp.replace(target)
    return target


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
    sources = {
        name: Path(path).expanduser().resolve() for name, path in user_stems.items()
    }
    full = covers(sources, instruments)
    # e.g. "user-stems:3f2a9c01de" -- the same digest as stems_tag
    model = f"{USER_STEMS_MODEL}:{stems_tag(sources, uses_demucs=not full)[6:]}"

    def separate(input_path, device=None, on_progress=None, **kwargs):
        input_path = Path(input_path)
        workdir = input_path.parent / ".tabgen" / NORMALIZED_DIR
        stems = {
            name: str(normalize_audio(src, workdir)) for name, src in sources.items()
        }
        if full:
            if on_progress is not None:
                on_progress("separation", 100.0)
            result = dict(stems)
            if input_path.expanduser().resolve() not in set(sources.values()):
                result[MIX_STEM] = str(normalize_audio(input_path, workdir))
            return SeparationResult(stems=result, model_version=model), True
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
                model_version=f"{separation.model_version}+{model}",
            ),
            hit,
        )

    return separate
