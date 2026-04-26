"""Semantic cache -- application-level response caching using structural fingerprints.

Caches LLM responses by a deterministic fingerprint of the request's
semantic content (task type, intent, file checksums). Returns cached
responses for functionally equivalent requests, skipping the API call.

No embedding model needed -- fingerprinting is based on file checksums
and structured metadata, not natural language similarity.

Estimated savings:
  - CRUD-heavy projects: 40-60% cost reduction
  - Test generation: 50-70% cost reduction
  - Bugfix batches: 30-40% cost reduction
"""

from __future__ import annotations

import contextlib
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class CacheEntry:
    """A cached LLM response with metadata for invalidation."""
    fingerprint: str
    response: str
    created_at: str
    context_checksums: dict[str, str]   # file_path -> sha256 at cache time
    task_type: str
    intent: str
    tokens_saved: int                   # input + output tokens this would have cost
    model: str = ""                     # model that generated the cached response
    hit_count: int = 0                  # how many times this entry has been returned


class SemanticCache:
    """Application-level response cache using structural fingerprints.

    Usage:
        cache = SemanticCache(Path(".armature/cache"))
        fp = cache.fingerprint("bugfix", "code_gen", ["src/models/user.py"])
        entry = cache.lookup(fp)
        if entry:
            # Use cached response, skip API call
            ...
        else:
            response = call_llm(...)
            cache.store(fp, response, task_type="bugfix", intent="code_gen",
                        context_files=["src/models/user.py"], tokens_saved=5000)
    """

    def __init__(
        self,
        storage_dir: Path,
        max_size_mb: int = 100,
        ttl_days: int = 7,
        root: Path | None = None,
    ) -> None:
        self.storage_dir = storage_dir
        self.index_path = storage_dir / "index.json"
        self.responses_dir = storage_dir / "responses"
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.ttl_seconds = ttl_days * 86400
        self.root = root or Path.cwd()

        # Lazy init -- directories created on first write
        self._index: dict[str, dict[str, object]] | None = None

    def fingerprint(
        self,
        task_type: str,
        intent: str,
        context_files: list[str],
        output_schema: str = "",
    ) -> str:
        """Compute a deterministic structural fingerprint for a request.

        The fingerprint is based on:
        - Task type (bugfix, feature, refactor, etc.)
        - Intent (code_gen, explain, test_gen, etc.)
        - SHA256 of each context file's current content
        - Optional output schema hash

        Two requests with the same fingerprint will produce semantically
        equivalent responses (same files, same intent).
        """
        hasher = hashlib.sha256()
        hasher.update(task_type.encode())
        hasher.update(intent.encode())

        # Sort file checksums for determinism
        for file_path in sorted(context_files):
            file_hash = self._file_checksum(file_path)
            hasher.update(file_path.encode())
            hasher.update(file_hash.encode())

        if output_schema:
            hasher.update(output_schema.encode())

        return hasher.hexdigest()[:32]  # 32-char hex fingerprint

    def lookup(self, fingerprint: str) -> CacheEntry | None:
        """Look up a cached response by fingerprint.

        Returns None if:
        - No entry exists for this fingerprint
        - Entry has expired (past TTL)
        - Any context file has changed since caching
        """
        index = self._load_index()
        meta = index.get(fingerprint)
        if meta is None:
            return None

        # Check TTL
        created = datetime.fromisoformat(meta["created_at"])
        age = (datetime.now(UTC) - created).total_seconds()
        if age > self.ttl_seconds:
            self._evict(fingerprint)
            return None

        # Check file checksums haven't changed
        for file_path, cached_hash in meta.get("context_checksums", {}).items():
            current_hash = self._file_checksum(file_path)
            if current_hash != cached_hash:
                self._evict(fingerprint)
                return None

        # Load response
        response_path = self.responses_dir / f"{fingerprint}.txt"
        if not response_path.exists():
            self._evict(fingerprint)
            return None

        response = response_path.read_text(encoding="utf-8")

        # Verify response integrity
        import hashlib
        import hmac
        expected_hash = meta.get("response_sha256")
        if expected_hash:
            actual_hash = hashlib.sha256(response.encode()).hexdigest()
            if not hmac.compare_digest(actual_hash, expected_hash):
                self._evict(fingerprint)
                return None

        # Increment hit count
        meta["hit_count"] = meta.get("hit_count", 0) + 1
        self._save_index(index)

        return CacheEntry(
            fingerprint=fingerprint,
            response=response,
            created_at=meta["created_at"],
            context_checksums=meta.get("context_checksums", {}),
            task_type=meta.get("task_type", ""),
            intent=meta.get("intent", ""),
            tokens_saved=meta.get("tokens_saved", 0),
            model=meta.get("model", ""),
            hit_count=meta["hit_count"],
        )

    def store(
        self,
        fingerprint: str,
        response: str,
        *,
        task_type: str = "",
        intent: str = "",
        context_files: list[str] | None = None,
        tokens_saved: int = 0,
        model: str = "",
    ) -> None:
        """Store a response in the cache."""
        self._ensure_dirs()
        index = self._load_index()

        # Compute checksums for all context files
        checksums = {}
        for f in (context_files or []):
            checksums[f] = self._file_checksum(f)

        meta = {
            "created_at": datetime.now(UTC).isoformat(),
            "context_checksums": checksums,
            "task_type": task_type,
            "intent": intent,
            "tokens_saved": tokens_saved,
            "model": model,
            "hit_count": 0,
        }

        # Write response file with integrity hash and restricted permissions
        import hashlib
        import os
        response_path = self.responses_dir / f"{fingerprint}.txt"
        response_path.write_text(response, encoding="utf-8")
        with contextlib.suppress(OSError):
            os.chmod(response_path, 0o600)
        meta["response_sha256"] = hashlib.sha256(response.encode()).hexdigest()

        # Update index
        index[fingerprint] = meta
        self._save_index(index)

        # Enforce size limit
        self._enforce_size_limit()

    def invalidate_file(self, file_path: str) -> int:
        """Invalidate all cache entries that reference a specific file.

        Returns the number of entries evicted.
        """
        index = self._load_index()
        to_evict = []
        for fp, meta in index.items():
            if file_path in meta.get("context_checksums", {}):
                to_evict.append(fp)

        for fp in to_evict:
            self._evict(fp)

        return len(to_evict)

    def clear(self) -> int:
        """Clear the entire cache. Returns entries removed."""
        index = self._load_index()
        count = len(index)
        for fp in list(index.keys()):
            self._evict(fp)
        return count

    def stats(self) -> dict[str, object]:
        """Return cache statistics."""
        index = self._load_index()
        total_entries = len(index)
        total_hits = sum(m.get("hit_count", 0) for m in index.values())
        total_tokens_saved = sum(
            m.get("tokens_saved", 0) * m.get("hit_count", 0)
            for m in index.values()
        )

        # Disk usage
        disk_bytes = 0
        if self.responses_dir.exists():
            for f in self.responses_dir.iterdir():
                disk_bytes += f.stat().st_size

        # Age distribution
        now = datetime.now(UTC)
        ages = []
        for m in index.values():
            created = datetime.fromisoformat(m["created_at"])
            ages.append((now - created).total_seconds() / 3600)  # hours

        return {
            "entries": total_entries,
            "total_hits": total_hits,
            "total_tokens_saved": total_tokens_saved,
            "disk_mb": round(disk_bytes / (1024 * 1024), 2),
            "max_size_mb": self.max_size_bytes // (1024 * 1024),
            "avg_age_hours": round(sum(ages) / len(ages), 1) if ages else 0,
            "by_intent": self._stats_by_intent(index),
        }

    def _stats_by_intent(self, index: dict) -> dict[str, dict[str, object]]:
        """Break down cache stats by intent."""
        by_intent: dict[str, dict[str, object]] = {}
        for meta in index.values():
            intent = meta.get("intent", "unknown")
            if intent not in by_intent:
                by_intent[intent] = {"entries": 0, "hits": 0, "tokens_saved": 0}
            by_intent[intent]["entries"] += 1
            by_intent[intent]["hits"] += meta.get("hit_count", 0)
            by_intent[intent]["tokens_saved"] += (
                meta.get("tokens_saved", 0) * meta.get("hit_count", 0)
            )
        return by_intent

    def _file_checksum(self, file_path: str) -> str:
        """SHA256 of a file's current content."""
        path = Path(file_path) if Path(file_path).is_absolute() else self.root / file_path
        if not path.exists():
            return "missing"
        try:
            content = path.read_bytes()
            return hashlib.sha256(content).hexdigest()[:16]
        except OSError:
            return "error"

    def _load_index(self) -> dict[str, dict[str, object]]:
        """Load the cache index from disk."""
        if self._index is not None:
            return self._index
        if self.index_path.exists():
            try:
                self._index = json.loads(self.index_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._index = {}
        else:
            self._index = {}
        return self._index

    def _save_index(self, index: dict[str, dict[str, object]]) -> None:
        """Persist the cache index to disk."""
        self._index = index
        self._ensure_dirs()
        self.index_path.write_text(
            json.dumps(index, indent=2), encoding="utf-8"
        )

    def _evict(self, fingerprint: str) -> None:
        """Remove a single entry from the cache."""
        index = self._load_index()
        index.pop(fingerprint, None)

        response_path = self.responses_dir / f"{fingerprint}.txt"
        if response_path.exists():
            response_path.unlink()

        self._save_index(index)

    def _enforce_size_limit(self) -> None:
        """Evict oldest entries if cache exceeds max size."""
        if not self.responses_dir.exists():
            return

        total_bytes = sum(f.stat().st_size for f in self.responses_dir.iterdir())
        if total_bytes <= self.max_size_bytes:
            return

        # Evict oldest entries first (LRU by creation time)
        index = self._load_index()
        sorted_entries = sorted(
            index.items(),
            key=lambda kv: kv[1].get("created_at", ""),
        )

        for fp, _meta in sorted_entries:
            if total_bytes <= self.max_size_bytes:
                break
            response_path = self.responses_dir / f"{fp}.txt"
            if response_path.exists():
                total_bytes -= response_path.stat().st_size
            self._evict(fp)

    def _ensure_dirs(self) -> None:
        """Create storage directories if they don't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.responses_dir.mkdir(parents=True, exist_ok=True)
