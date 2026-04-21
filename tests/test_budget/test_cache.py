"""Tests for budget/cache.py -- semantic response caching."""

from __future__ import annotations

from pathlib import Path

import pytest

from armature.budget.cache import SemanticCache


@pytest.fixture
def cache(tmp_path: Path) -> SemanticCache:
    return SemanticCache(
        storage_dir=tmp_path / "cache",
        max_size_mb=10,
        ttl_days=7,
        root=tmp_path,
    )


@pytest.fixture
def sample_file(tmp_path: Path) -> Path:
    f = tmp_path / "sample.py"
    f.write_text("def hello(): return 'world'\n", encoding="utf-8")
    return f


class TestFingerprint:
    """Tests for structural fingerprinting."""

    def test_deterministic(self, cache: SemanticCache, sample_file: Path):
        fp1 = cache.fingerprint("bugfix", "code_gen", [str(sample_file)])
        fp2 = cache.fingerprint("bugfix", "code_gen", [str(sample_file)])
        assert fp1 == fp2

    def test_different_intent_different_fp(self, cache: SemanticCache, sample_file: Path):
        fp1 = cache.fingerprint("bugfix", "code_gen", [str(sample_file)])
        fp2 = cache.fingerprint("bugfix", "test_gen", [str(sample_file)])
        assert fp1 != fp2

    def test_different_task_type_different_fp(self, cache: SemanticCache, sample_file: Path):
        fp1 = cache.fingerprint("bugfix", "code_gen", [str(sample_file)])
        fp2 = cache.fingerprint("feature", "code_gen", [str(sample_file)])
        assert fp1 != fp2

    def test_file_content_matters(self, cache: SemanticCache, tmp_path: Path):
        f = tmp_path / "changing.py"
        f.write_text("v1", encoding="utf-8")
        fp1 = cache.fingerprint("bugfix", "code_gen", [str(f)])
        f.write_text("v2", encoding="utf-8")
        fp2 = cache.fingerprint("bugfix", "code_gen", [str(f)])
        assert fp1 != fp2

    def test_length_is_32(self, cache: SemanticCache, sample_file: Path):
        fp = cache.fingerprint("bugfix", "code_gen", [str(sample_file)])
        assert len(fp) == 32


class TestStoreAndLookup:
    """Tests for cache store/lookup lifecycle."""

    def test_store_and_retrieve(self, cache: SemanticCache, sample_file: Path):
        fp = cache.fingerprint("bugfix", "code_gen", [str(sample_file)])
        cache.store(fp, "cached response", task_type="bugfix", intent="code_gen",
                    context_files=[str(sample_file)], tokens_saved=5000)
        entry = cache.lookup(fp)
        assert entry is not None
        assert entry.response == "cached response"
        assert entry.tokens_saved == 5000

    def test_lookup_miss(self, cache: SemanticCache):
        result = cache.lookup("nonexistent_fingerprint_hash")
        assert result is None

    def test_hit_count_increments(self, cache: SemanticCache, sample_file: Path):
        fp = cache.fingerprint("bugfix", "code_gen", [str(sample_file)])
        cache.store(fp, "response", context_files=[str(sample_file)], tokens_saved=1000)
        cache.lookup(fp)
        entry = cache.lookup(fp)
        assert entry is not None
        assert entry.hit_count == 2

    def test_invalidated_on_file_change(self, cache: SemanticCache, tmp_path: Path):
        f = tmp_path / "changing.py"
        f.write_text("v1", encoding="utf-8")
        fp = cache.fingerprint("bugfix", "code_gen", [str(f)])
        cache.store(fp, "response", context_files=[str(f)], tokens_saved=1000)
        # Change the file
        f.write_text("v2", encoding="utf-8")
        entry = cache.lookup(fp)
        assert entry is None  # invalidated

    def test_invalidate_file(self, cache: SemanticCache, sample_file: Path):
        fp = cache.fingerprint("bugfix", "code_gen", [str(sample_file)])
        cache.store(fp, "response", context_files=[str(sample_file)], tokens_saved=1000)
        evicted = cache.invalidate_file(str(sample_file))
        assert evicted == 1
        assert cache.lookup(fp) is None

    def test_clear(self, cache: SemanticCache, sample_file: Path):
        fp = cache.fingerprint("bugfix", "code_gen", [str(sample_file)])
        cache.store(fp, "response", tokens_saved=1000)
        count = cache.clear()
        assert count == 1


class TestStats:
    """Tests for cache statistics."""

    def test_empty_stats(self, cache: SemanticCache):
        stats = cache.stats()
        assert stats["entries"] == 0
        assert stats["total_hits"] == 0

    def test_stats_after_usage(self, cache: SemanticCache, sample_file: Path):
        fp = cache.fingerprint("bugfix", "code_gen", [str(sample_file)])
        cache.store(fp, "response", intent="code_gen", tokens_saved=5000)
        cache.lookup(fp)
        cache.lookup(fp)
        stats = cache.stats()
        assert stats["entries"] == 1
        assert stats["total_hits"] == 2
        assert stats["total_tokens_saved"] == 10000  # 5000 * 2 hits
        assert "code_gen" in stats["by_intent"]
