"""Disk cache for stage results.

Results live in a ``.tabgen/`` directory next to the input audio file.
The cache key combines the stage name, the sha256 of the input file's
bytes and the model version, so editing the audio or bumping the model
version both invalidate the entry (lookup misses and recomputes).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

CACHE_DIR_NAME = ".tabgen"


def _sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class StageCache:
    """Caches one input file's stage results as JSON files on disk."""

    def __init__(self, input_path: str | Path) -> None:
        self.input_path = Path(input_path)
        self.cache_dir = self.input_path.parent / CACHE_DIR_NAME
        self._input_hash: str | None = None

    @property
    def input_hash(self) -> str:
        """sha256 of the input file's bytes (computed once, then reused)."""
        if self._input_hash is None:
            self._input_hash = _sha256_of_file(self.input_path)
        return self._input_hash

    def entry_path(self, stage: str, version: str) -> Path:
        """Path of the cache file for stage + input hash + model version."""
        key = f"{stage}-{self.input_hash}-{version}"
        return self.cache_dir / f"{key}.json"

    def get(self, stage: str, version: str) -> dict[str, Any] | None:
        """Return the cached payload, or None on miss (including a
        version mismatch, since the version is part of the key)."""
        path = self.entry_path(stage, version)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None  # corrupt entry: treat as miss

    def put(self, stage: str, version: str, payload: dict[str, Any]) -> Path:
        """Write the payload for stage + input hash + model version."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path = self.entry_path(stage, version)
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def get_or_compute(
        self,
        stage: str,
        version: str,
        compute: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        """Return the cached payload; on miss, compute, store and return."""
        cached = self.get(stage, version)
        if cached is not None:
            return cached
        payload = compute()
        self.put(stage, version, payload)
        return payload
