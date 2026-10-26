"""Disk cache: miss writes, hit skips recompute, version bump invalidates."""

from pathlib import Path

from tabgen.core.cache import CACHE_DIR_NAME, StageCache


def _make_audio(tmp_path: Path) -> Path:
    audio = tmp_path / "song.wav"
    audio.write_bytes(b"fake-audio-bytes")
    return audio


def test_miss_computes_and_writes_next_to_input(tmp_path):
    audio = _make_audio(tmp_path)
    cache = StageCache(audio)

    result = cache.get_or_compute("separation", "v1", lambda: {"answer": 42})

    assert result == {"answer": 42}
    cache_dir = tmp_path / CACHE_DIR_NAME
    assert cache_dir.is_dir()
    assert list(cache_dir.glob("separation-*-v1.json"))


def test_second_call_hits_without_recompute(tmp_path):
    audio = _make_audio(tmp_path)
    cache = StageCache(audio)
    calls = {"count": 0}

    def compute():
        calls["count"] += 1
        return {"answer": 42}

    first = cache.get_or_compute("separation", "v1", compute)
    second = cache.get_or_compute("separation", "v1", compute)

    assert first == second == {"answer": 42}
    assert calls["count"] == 1

    # A fresh instance (new process) also hits the on-disk entry.
    assert StageCache(audio).get_or_compute("separation", "v1", compute) == first
    assert calls["count"] == 1


def test_version_bump_invalidates(tmp_path):
    audio = _make_audio(tmp_path)
    cache = StageCache(audio)
    calls = {"count": 0}

    def compute():
        calls["count"] += 1
        return {"version_seen": calls["count"]}

    cache.get_or_compute("separation", "v1", compute)
    bumped = cache.get_or_compute("separation", "v2", compute)

    assert calls["count"] == 2
    assert bumped == {"version_seen": 2}
    assert cache.get("separation", "v1") == {"version_seen": 1}


def test_changed_input_bytes_invalidate(tmp_path):
    audio = _make_audio(tmp_path)
    StageCache(audio).put("analysis", "v1", {"tempo": 120})

    audio.write_bytes(b"different-audio-bytes")
    assert StageCache(audio).get("analysis", "v1") is None


def test_stages_do_not_collide(tmp_path):
    audio = _make_audio(tmp_path)
    cache = StageCache(audio)
    cache.put("separation", "v1", {"stage": "separation"})
    cache.put("analysis", "v1", {"stage": "analysis"})

    assert cache.get("separation", "v1") == {"stage": "separation"}
    assert cache.get("analysis", "v1") == {"stage": "analysis"}
