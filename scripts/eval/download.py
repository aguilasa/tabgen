"""Download only the files a subset needs, outside the repository.

Nothing here runs implicitly: :func:`plan` resolves URLs and sizes (HTTP
metadata only) so the caller can show them to the user, and
:func:`execute` downloads only after an explicit confirmation flag
(``run.py --download --yes``).

Sources (looked up 2026-10-27):

- GuitarSet 1.1.0, Zenodo record 3371780 (CC BY 4.0). The zips are big
  (``audio_mono-mic.zip`` 657 MB, ``annotation.zip`` 39 MB), but Zenodo
  serves HTTP range requests, so :class:`HttpRangeFile` lets the stdlib
  ``zipfile`` read the central directory and extract only the subset's
  members (a few MB per track).
- EGDB (Chen et al., ICASSP 2022), a public Google Drive folder with one
  file per clip (``audio_DI/<n>.wav`` about 1.6 MB, ``audio_label/<n>.midi``).
  The file ids are resolved from the folder's ``embeddedfolderview`` page;
  if Google changes that page, download the files by hand into the same
  layout (see :mod:`scripts.eval.loaders`).
"""

from __future__ import annotations

import io
import re
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

USER_AGENT = "tabgen-eval/0.1"

GUITARSET_RECORD = "https://zenodo.org/api/records/3371780"
GUITARSET_ZIPS = {
    "annotation": f"{GUITARSET_RECORD}/files/annotation.zip/content",
    "audio_mono-mic": f"{GUITARSET_RECORD}/files/audio_mono-mic.zip/content",
}

EGDB_FOLDERS = {
    "audio_DI": "1AfpAaWnBvrTLHxe2DafgQ4mz4GGBjwAa",
    "audio_label": "1a6wDDbu_yYVAEGdeC2fRs6SnmXsKq9tN",
}
EGDB_FOLDER_VIEW = "https://drive.google.com/embeddedfolderview?id={folder_id}"
EGDB_FILE_URL = (
    "https://drive.usercontent.google.com/download?id={file_id}"
    "&export=download&confirm=t"
)


class DownloadError(RuntimeError):
    """Raised when a source cannot be resolved or fetched."""


@dataclass
class PlannedFile:
    """One file to fetch: where it comes from and where it lands."""

    url: str
    target: Path
    size_bytes: int | None
    # For zip-backed sources: the member to extract from ``url``.
    zip_member: str | None = None


def _request(url: str, method: str = "GET", headers: dict | None = None):
    req = urllib.request.Request(url, method=method)
    req.add_header("User-Agent", USER_AGENT)
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    return urllib.request.urlopen(req, timeout=60)


class HttpRangeFile(io.RawIOBase):
    """Seekable read-only file over HTTP range requests (for ``zipfile``)."""

    def __init__(self, url: str) -> None:
        self.url = url
        with _request(url, headers={"Range": "bytes=0-0"}) as resp:
            if resp.status != 206:
                raise DownloadError(f"server ignores range requests: {url}")
            content_range = resp.headers.get("Content-Range", "")
        match = re.search(r"/(\d+)$", content_range)
        if not match:
            raise DownloadError(f"no Content-Range total for {url}")
        self.size = int(match.group(1))
        self.pos = 0

    def seekable(self) -> bool:
        return True

    def readable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            self.pos = offset
        elif whence == io.SEEK_CUR:
            self.pos += offset
        else:
            self.pos = self.size + offset
        return self.pos

    def read(self, n: int = -1) -> bytes:
        if self.pos >= self.size:
            return b""
        end = self.size - 1 if n is None or n < 0 else min(self.pos + n, self.size) - 1
        headers = {"Range": f"bytes={self.pos}-{end}"}
        with _request(self.url, headers=headers) as resp:
            data = resp.read()
        self.pos += len(data)
        return data

    def readinto(self, buffer) -> int:
        data = self.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)


def guitarset_member_names(track_id: str) -> dict[str, str]:
    """Zip member name per GuitarSet zip for one track id."""
    return {
        "annotation": f"{track_id}.jams",
        "audio_mono-mic": f"{track_id}_mic.wav",
    }


def plan_guitarset(track_ids: list[str], data_dir: Path) -> list[PlannedFile]:
    """Resolve the subset members inside the Zenodo zips (sizes from the zip)."""
    planned: list[PlannedFile] = []
    for zip_key, url in GUITARSET_ZIPS.items():
        archive = zipfile.ZipFile(HttpRangeFile(url))
        by_basename = {Path(info.filename).name: info for info in archive.infolist()}
        for track_id in track_ids:
            name = guitarset_member_names(track_id)[zip_key]
            info = by_basename.get(name)
            if info is None:
                raise DownloadError(f"{name} not found in {zip_key}.zip")
            planned.append(
                PlannedFile(
                    url=url,
                    target=data_dir / zip_key / name,
                    size_bytes=info.file_size,
                    zip_member=info.filename,
                )
            )
    return planned


def egdb_folder_listing(folder_id: str) -> dict[str, str]:
    """Map file name -> Drive file id from a public folder's embedded view."""
    with _request(EGDB_FOLDER_VIEW.format(folder_id=folder_id)) as resp:
        html = resp.read().decode("utf-8", "replace")
    pairs = re.findall(
        r'file/d/([A-Za-z0-9_-]+)/view.*?flip-entry-title">([^<]+)<', html, re.S
    )
    if not pairs:
        raise DownloadError(f"could not list Drive folder {folder_id}")
    return {name: file_id for file_id, name in pairs}


def _content_length(url: str) -> int | None:
    with _request(url, method="HEAD") as resp:
        value = resp.headers.get("Content-Length")
    return int(value) if value else None


def plan_egdb(track_ids: list[str], data_dir: Path) -> list[PlannedFile]:
    """Resolve DI audio and label MIDI per clip (sizes via HTTP HEAD)."""
    suffix = {"audio_DI": ".wav", "audio_label": ".midi"}
    planned: list[PlannedFile] = []
    for folder, folder_id in EGDB_FOLDERS.items():
        listing = egdb_folder_listing(folder_id)
        for track_id in track_ids:
            name = f"{track_id}{suffix[folder]}"
            if name not in listing:
                raise DownloadError(f"{name} not found in EGDB {folder}")
            url = EGDB_FILE_URL.format(file_id=listing[name])
            planned.append(
                PlannedFile(
                    url=url,
                    target=data_dir / folder / name,
                    size_bytes=_content_length(url),
                )
            )
    return planned


def plan(dataset: str, track_ids: list[str], data_dir: Path) -> list[PlannedFile]:
    """Files still missing under ``data_dir`` for the subset (metadata only)."""
    if dataset == "guitarset":
        planned = plan_guitarset(track_ids, data_dir)
    elif dataset == "egdb":
        planned = plan_egdb(track_ids, data_dir)
    else:
        raise DownloadError(f"unknown dataset {dataset!r}")
    return [item for item in planned if not item.target.is_file()]


def execute(planned: list[PlannedFile]) -> None:
    """Fetch every planned file (call only after explicit user confirmation)."""
    archives: dict[str, zipfile.ZipFile] = {}
    for item in planned:
        item.target.parent.mkdir(parents=True, exist_ok=True)
        partial = item.target.with_name(item.target.name + ".part")
        if item.zip_member is not None:
            archive = archives.get(item.url)
            if archive is None:
                archive = zipfile.ZipFile(HttpRangeFile(item.url))
                archives[item.url] = archive
            with archive.open(item.zip_member) as src, partial.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1 << 20)
        else:
            with _request(item.url) as src, partial.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1 << 20)
        partial.replace(item.target)


def describe(planned: list[PlannedFile]) -> str:
    """Human-readable plan: one line per file plus the total size."""
    lines = []
    total = 0
    for item in planned:
        size = item.size_bytes or 0
        total += size
        source = f"{item.url} [{item.zip_member}]" if item.zip_member else item.url
        lines.append(f"{size / 1e6:9.3f} MB  {item.target}  <- {source}")
    lines.append(f"total: {total / 1e6:.2f} MB in {len(planned)} file(s)")
    return "\n".join(lines)
