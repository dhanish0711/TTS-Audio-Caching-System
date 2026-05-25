"""
TTS Audio Caching System — Enhanced Cache Manager
===================================================
Thread-safe LRU + TTL cache with:
- File-based audio storage with optional gzip compression
- Persistent index (survives server restarts)
- Fuzzy text matching (AI-powered near-miss cache hits)
- Request history tracking for analytics
"""

from __future__ import annotations

import gzip
import json
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Optional, Tuple

from config import (
    CACHE_DIR, CACHE_MAX_ENTRIES, CACHE_MAX_SIZE_MB, CACHE_TTL_SECONDS,
    CACHE_INDEX_FILE, CACHE_COMPRESSION, FUZZY_MATCH_ENABLED,
    FUZZY_MATCH_THRESHOLD, REQUEST_HISTORY_MAX,
)
from tts_cache.hash_utils import generate_cache_key
from tts_cache.models import CacheEntry, CacheStats, RequestRecord
from tts_cache.smart_cache import fuzzy_find_match


class TTSAudioCache:
    """Thread-safe TTS audio cache with LRU eviction, TTL expiry,
    gzip compression, persistent index, fuzzy matching,
    and request analytics.
    """

    def __init__(
        self,
        cache_dir: str = CACHE_DIR,
        max_entries: int = CACHE_MAX_ENTRIES,
        max_size_mb: int = CACHE_MAX_SIZE_MB,
        ttl_seconds: int = CACHE_TTL_SECONDS,
        index_file: str = CACHE_INDEX_FILE,
        compression: bool = CACHE_COMPRESSION,
        fuzzy_match: bool = FUZZY_MATCH_ENABLED,
        fuzzy_threshold: float = FUZZY_MATCH_THRESHOLD,
    ):
        self._cache_dir = cache_dir
        self._max_entries = max_entries
        self._max_size_bytes = max_size_mb * 1024 * 1024
        self._ttl_seconds = ttl_seconds
        self._index_file = index_file
        self._compression = compression
        self._fuzzy_match = fuzzy_match
        self._fuzzy_threshold = fuzzy_threshold

        # OrderedDict for LRU ordering
        self._index: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()

        # Statistics
        self._total_requests = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._fuzzy_hits = 0
        self._total_hit_latency_ms = 0.0
        self._total_miss_latency_ms = 0.0

        # Request history for analytics
        self._request_history: list[RequestRecord] = []
        self._history_max = REQUEST_HISTORY_MAX

        # Ensure cache directory exists
        os.makedirs(self._cache_dir, exist_ok=True)

        # Load persistent index if it exists
        self._load_index()

    # ── Public API ────────────────────────────────────────────

    def get(
        self,
        text: str,
        voice_id: str = "default",
        speed: float = 1.0,
        pitch: float = 1.0,
    ) -> Optional[Tuple[bytes, str, bool, float]]:
        """Look up cached audio for the given text + voice config.

        Returns:
            Tuple of (audio_bytes, cache_key, is_fuzzy_match, similarity_score) if found,
            or None if cache miss.
        """
        key = generate_cache_key(text, voice_id, speed, pitch)
        start = time.perf_counter()

        with self._lock:
            self._total_requests += 1

            # Exact match
            result = self._try_get_entry(key)
            if result is not None:
                elapsed = (time.perf_counter() - start) * 1000
                self._total_hit_latency_ms += elapsed
                self._cache_hits += 1
                return result[0], result[1], False, 1.0

            # Fuzzy match (AI-powered)
            if self._fuzzy_match and len(self._index) > 0:
                cached_texts = {
                    k: entry.text for k, entry in self._index.items()
                    if entry.voice_id == voice_id
                    and abs(entry.speed - speed) < 0.01
                    and abs(entry.pitch - pitch) < 0.01
                }
                fuzzy_result = fuzzy_find_match(text, cached_texts, self._fuzzy_threshold)
                if fuzzy_result is not None:
                    fuzzy_key, _ratio = fuzzy_result
                    result = self._try_get_entry(fuzzy_key)
                    if result is not None:
                        elapsed = (time.perf_counter() - start) * 1000
                        self._total_hit_latency_ms += elapsed
                        self._cache_hits += 1
                        self._fuzzy_hits += 1
                        return result[0], fuzzy_key, True, _ratio

            self._cache_misses += 1
            return None

    def _try_get_entry(self, key: str) -> Optional[Tuple[bytes, str]]:
        """Try to retrieve a cache entry by key.
        Must be called while holding self._lock.
        """
        entry = self._index.get(key)
        if entry is None:
            return None

        # Check TTL
        age = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
        if age > entry.ttl_seconds:
            self._remove_entry(key)
            return None

        # Check file exists
        if not os.path.isfile(entry.file_path):
            self._remove_entry(key)
            return None

        # Update LRU + stats
        self._index.move_to_end(key)
        entry.last_accessed_at = datetime.now(timezone.utc)
        entry.access_count += 1

        # Read and decompress
        audio_data = self._read_audio(entry.file_path)
        return audio_data, key

    def put(
        self,
        text: str,
        voice_id: str,
        speed: float,
        pitch: float,
        audio_data: bytes,
    ) -> str:
        """Store synthesized audio in the cache."""
        key = generate_cache_key(text, voice_id, speed, pitch)
        ext = ".mp3.gz" if self._compression else ".mp3"
        file_path = os.path.join(self._cache_dir, f"{key}{ext}")

        with self._lock:
            if key in self._index:
                self._remove_entry(key)

            # Write (compressed or raw)
            stored_data = self._write_audio(file_path, audio_data)

            self._evict_if_needed(len(stored_data))

            now = datetime.now(timezone.utc)
            entry = CacheEntry(
                cache_key=key,
                text=text,
                voice_id=voice_id,
                speed=speed,
                pitch=pitch,
                file_path=file_path,
                file_size_bytes=len(stored_data),
                original_size_bytes=len(audio_data),
                created_at=now,
                last_accessed_at=now,
                access_count=0,
                ttl_seconds=self._ttl_seconds,
                compressed=self._compression,
            )
            self._index[key] = entry
            self._save_index()

        return key

    def invalidate(self, key: str) -> bool:
        """Remove a specific entry."""
        with self._lock:
            if key in self._index:
                self._remove_entry(key)
                self._save_index()
                return True
            return False

    def clear(self) -> int:
        """Remove all entries."""
        with self._lock:
            count = len(self._index)
            keys = list(self._index.keys())
            for key in keys:
                self._remove_entry(key)
            self._save_index()
            return count

    def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        with self._lock:
            now = datetime.now(timezone.utc)
            expired_keys = []
            for key, entry in self._index.items():
                age = (now - entry.created_at).total_seconds()
                if age > entry.ttl_seconds:
                    expired_keys.append(key)

            for key in expired_keys:
                self._remove_entry(key)

            if expired_keys:
                self._save_index()

            return len(expired_keys)

    def get_stats(self) -> CacheStats:
        """Return aggregate cache statistics."""
        with self._lock:
            total_size = sum(e.file_size_bytes for e in self._index.values())
            original_size = sum(e.original_size_bytes for e in self._index.values())
            entries = list(self._index.values())

            oldest = min((e.created_at for e in entries), default=None)
            newest = max((e.created_at for e in entries), default=None)

            hit_rate = 0.0
            if self._total_requests > 0:
                hit_rate = (self._cache_hits / self._total_requests) * 100

            avg_hit = 0.0
            if self._cache_hits > 0:
                avg_hit = self._total_hit_latency_ms / self._cache_hits

            avg_miss = 0.0
            if self._cache_misses > 0:
                avg_miss = self._total_miss_latency_ms / self._cache_misses

            compression_ratio = 0.0
            if original_size > 0:
                compression_ratio = round((1 - total_size / original_size) * 100, 1)

            return CacheStats(
                total_entries=len(self._index),
                total_size_bytes=total_size,
                total_size_mb=round(total_size / (1024 * 1024), 2),
                max_entries=self._max_entries,
                max_size_mb=self._max_size_bytes // (1024 * 1024),
                total_requests=self._total_requests,
                cache_hits=self._cache_hits,
                cache_misses=self._cache_misses,
                fuzzy_hits=self._fuzzy_hits,
                hit_rate_percent=round(hit_rate, 1),
                avg_hit_latency_ms=round(avg_hit, 2),
                avg_miss_latency_ms=round(avg_miss, 2),
                compression_ratio=compression_ratio,
                compression_enabled=self._compression,
                fuzzy_match_enabled=self._fuzzy_match,
                oldest_entry=oldest,
                newest_entry=newest,
            )

    def get_entries(self) -> list[CacheEntry]:
        """Return all cache entries (most recent first)."""
        with self._lock:
            return list(reversed(self._index.values()))

    def record_miss_latency(self, latency_ms: float) -> None:
        """Record the latency of a cache-miss."""
        with self._lock:
            self._total_miss_latency_ms += latency_ms

    def add_request_record(self, record: RequestRecord) -> None:
        """Add a request to the analytics history."""
        with self._lock:
            self._request_history.append(record)
            if len(self._request_history) > self._history_max:
                self._request_history = self._request_history[-self._history_max:]

    def get_request_history(self) -> list[RequestRecord]:
        """Get the request history for analytics."""
        with self._lock:
            return list(self._request_history)

    # ── Compression / IO ──────────────────────────────────────

    def _write_audio(self, file_path: str, audio_data: bytes) -> bytes:
        """Write audio to disk, optionally compressed."""
        if self._compression:
            compressed = gzip.compress(audio_data, compresslevel=6)
            with open(file_path, "wb") as f:
                f.write(compressed)
            return compressed
        else:
            with open(file_path, "wb") as f:
                f.write(audio_data)
            return audio_data

    def _read_audio(self, file_path: str) -> bytes:
        """Read audio from disk, decompressing if needed."""
        with open(file_path, "rb") as f:
            data = f.read()

        if file_path.endswith(".gz"):
            return gzip.decompress(data)
        return data

    # ── Persistent Index ──────────────────────────────────────

    def _save_index(self) -> None:
        """Save the cache index to a JSON file for persistence."""
        try:
            data = {}
            for key, entry in self._index.items():
                data[key] = entry.model_dump(mode="json")

            with open(self._index_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception:
            pass  # Non-critical: cache still works in-memory

    def _load_index(self) -> None:
        """Load the cache index from disk if it exists."""
        if not os.path.isfile(self._index_file):
            return

        try:
            with open(self._index_file, "r") as f:
                data = json.load(f)

            for key, entry_data in data.items():
                # Verify the audio file still exists
                file_path = entry_data.get("file_path", "")
                if os.path.isfile(file_path):
                    entry = CacheEntry(**entry_data)
                    # Check TTL
                    age = (datetime.now(timezone.utc) - entry.created_at).total_seconds()
                    if age <= entry.ttl_seconds:
                        self._index[key] = entry

        except Exception:
            pass  # Start fresh if index is corrupted

    # ── Internal ──────────────────────────────────────────────

    def _remove_entry(self, key: str) -> None:
        """Remove an entry from the index and delete its file."""
        entry = self._index.pop(key, None)
        if entry and os.path.isfile(entry.file_path):
            try:
                os.remove(entry.file_path)
            except OSError:
                pass

    def _evict_if_needed(self, incoming_size: int) -> None:
        """Evict LRU entries until we can fit the incoming item."""
        while len(self._index) >= self._max_entries:
            oldest_key = next(iter(self._index))
            self._remove_entry(oldest_key)

        current_size = sum(e.file_size_bytes for e in self._index.values())
        while current_size + incoming_size > self._max_size_bytes and self._index:
            oldest_key = next(iter(self._index))
            entry = self._index[oldest_key]
            current_size -= entry.file_size_bytes
            self._remove_entry(oldest_key)

    @property
    def total_entries(self) -> int:
        with self._lock:
            return len(self._index)

    def get_recommendations(self) -> list[dict]:
        """Generate smart recommendations for pre-caching.
        Recommends prompts from standard warmup list, predicted next steps,
        or frequently missed queries that aren't yet cached.
        """
        with self._lock:
            from tts_cache.smart_cache import WARMUP_PROMPTS, get_predictions
            
            recommendations = []
            cached_texts_normalized = {self._normalize_text(entry.text) for entry in self._index.values()}
            
            # 1. Check recent request history for cache misses
            miss_counts = {}
            for record in reversed(self._request_history):
                if not record.cache_hit:
                    norm = self._normalize_text(record.text)
                    miss_counts[norm] = miss_counts.get(norm, 0) + 1
            
            # Recommend frequent misses first (if not currently cached)
            for text_norm, count in sorted(miss_counts.items(), key=lambda x: x[1], reverse=True):
                # Find matching text from history records
                original_text = next((r.text for r in self._request_history if self._normalize_text(r.text) == text_norm), None)
                if original_text and text_norm not in cached_texts_normalized:
                    recommendations.append({
                        "text": original_text,
                        "reason": f"Frequent cache miss (requested {count}x)",
                        "cached": False
                    })
                    if len(recommendations) >= 3:
                        break

            # 2. Check next steps in standard flow based on the most recent request
            if self._request_history:
                last_req = self._request_history[-1]
                preds = get_predictions(last_req.text)
                for pred in preds:
                    if len(recommendations) >= 5:
                        break
                    pred_norm = self._normalize_text(pred)
                    is_cached = pred_norm in cached_texts_normalized
                    recommendations.append({
                        "text": pred,
                        "reason": "Next in interview flow",
                        "cached": is_cached
                    })

            # 3. Add core warmup prompts that are not yet cached
            for wp in WARMUP_PROMPTS:
                if len(recommendations) >= 6:
                    break
                wp_norm = self._normalize_text(wp)
                if wp_norm not in cached_texts_normalized:
                    # Avoid duplicates
                    if not any(r["text"].lower() == wp.lower() for r in recommendations):
                        recommendations.append({
                            "text": wp,
                            "reason": "Popular interview question",
                            "cached": False
                        })

            return recommendations

    def _normalize_text(self, text: str) -> str:
        """Helper to normalize text for comparison."""
        import re
        return re.sub(r"\s+", " ", text.strip().lower()).rstrip(".!?")
