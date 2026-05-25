"""
TTS Audio Caching System — Unit & Integration Tests
=====================================================
"""

import os
import sys
import time
import shutil
import tempfile

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tts_cache.hash_utils import generate_cache_key
from tts_cache.cache_manager import TTSAudioCache
from tts_cache import simulated_tts


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def temp_cache_dir():
    """Create a temp directory for cache files and clean up after."""
    tmpdir = tempfile.mkdtemp(prefix="tts_cache_test_")
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def cache(temp_cache_dir):
    """Create a cache instance with small limits for testing."""
    return TTSAudioCache(
        cache_dir=temp_cache_dir,
        max_entries=5,
        max_size_mb=1,
        ttl_seconds=10,
        index_file=os.path.join(temp_cache_dir, "cache_index.json"),
    )


# ── Hash Utils Tests ─────────────────────────────────────────

class TestHashUtils:
    def test_deterministic_key(self):
        """Same input always produces the same key."""
        key1 = generate_cache_key("hello world", "default", 1.0, 1.0)
        key2 = generate_cache_key("hello world", "default", 1.0, 1.0)
        assert key1 == key2

    def test_different_text_different_key(self):
        """Different text produces different keys."""
        key1 = generate_cache_key("hello world")
        key2 = generate_cache_key("goodbye world")
        assert key1 != key2

    def test_different_voice_different_key(self):
        """Different voice_id produces different keys."""
        key1 = generate_cache_key("hello", voice_id="default")
        key2 = generate_cache_key("hello", voice_id="female-1")
        assert key1 != key2

    def test_different_speed_different_key(self):
        """Different speed produces different keys."""
        key1 = generate_cache_key("hello", speed=1.0)
        key2 = generate_cache_key("hello", speed=1.5)
        assert key1 != key2

    def test_different_pitch_different_key(self):
        """Different pitch produces different keys."""
        key1 = generate_cache_key("hello", pitch=1.0)
        key2 = generate_cache_key("hello", pitch=0.8)
        assert key1 != key2

    def test_whitespace_normalization(self):
        """Extra whitespace is collapsed before hashing."""
        key1 = generate_cache_key("hello   world")
        key2 = generate_cache_key("hello world")
        assert key1 == key2

    def test_case_normalization(self):
        """Text is lowered before hashing."""
        key1 = generate_cache_key("Hello World")
        key2 = generate_cache_key("hello world")
        assert key1 == key2

    def test_key_is_sha256_hex(self):
        """Key should be a 64-char hex string."""
        key = generate_cache_key("test")
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)


# ── Cache Manager Tests ──────────────────────────────────────

class TestCacheManager:
    def test_put_and_get(self, cache):
        """Put audio, then get it back."""
        audio = b"fake-audio-data-12345"
        key = cache.put("hello", "default", 1.0, 1.0, audio)

        result = cache.get("hello", "default", 1.0, 1.0)
        assert result is not None
        returned_audio, returned_key, is_fuzzy, similarity = result
        assert returned_audio == audio
        assert returned_key == key
        assert is_fuzzy is False
        assert similarity == 1.0

    def test_cache_miss(self, cache):
        """Get on empty cache returns None."""
        result = cache.get("nonexistent", "default", 1.0, 1.0)
        assert result is None

    def test_cache_hit_same_audio(self, cache):
        """Cache returns exact same audio bytes."""
        audio = b"\x00\x01\x02\x03" * 100
        cache.put("test", "default", 1.0, 1.0, audio)

        result = cache.get("test", "default", 1.0, 1.0)
        assert result is not None
        assert result[0] == audio

    def test_access_count_increments(self, cache):
        """Access count should increment on each get."""
        cache.put("test", "default", 1.0, 1.0, b"data")

        cache.get("test", "default", 1.0, 1.0)
        cache.get("test", "default", 1.0, 1.0)
        cache.get("test", "default", 1.0, 1.0)

        entries = cache.get_entries()
        assert len(entries) == 1
        assert entries[0].access_count == 3

    def test_invalidate(self, cache):
        """Invalidating an entry removes it."""
        key = cache.put("test", "default", 1.0, 1.0, b"data")

        assert cache.invalidate(key) is True
        assert cache.get("test", "default", 1.0, 1.0) is None
        assert cache.total_entries == 0

    def test_invalidate_nonexistent(self, cache):
        """Invalidating a non-existent key returns False."""
        assert cache.invalidate("fake-key") is False

    def test_clear(self, cache):
        """Clear removes all entries."""
        for i in range(3):
            cache.put(f"text-{i}", "default", 1.0, 1.0, b"data")

        assert cache.total_entries == 3
        count = cache.clear()
        assert count == 3
        assert cache.total_entries == 0

    def test_lru_eviction(self, cache):
        """When max_entries is exceeded, the least recently used is evicted."""
        # max_entries = 5, so adding 6 should evict the first
        keys = []
        for i in range(6):
            key = cache.put(f"text-{i}", "default", 1.0, 1.0, f"data-{i}".encode())
            keys.append(key)

        assert cache.total_entries == 5
        # First entry should be evicted
        assert cache.get("text-0", "default", 1.0, 1.0) is None
        # Last entry should still be there
        assert cache.get("text-5", "default", 1.0, 1.0) is not None

    def test_ttl_expiration(self, temp_cache_dir):
        """Expired entries should not be returned."""
        cache = TTSAudioCache(
            cache_dir=temp_cache_dir,
            max_entries=10,
            max_size_mb=1,
            ttl_seconds=1,  # 1 second TTL
        )

        cache.put("expiring", "default", 1.0, 1.0, b"data")
        assert cache.get("expiring", "default", 1.0, 1.0) is not None

        time.sleep(1.5)  # Wait for TTL to expire

        assert cache.get("expiring", "default", 1.0, 1.0) is None

    def test_cleanup_expired(self, temp_cache_dir):
        """cleanup_expired removes all expired entries."""
        cache = TTSAudioCache(
            cache_dir=temp_cache_dir,
            max_entries=10,
            max_size_mb=1,
            ttl_seconds=1,
        )

        for i in range(3):
            cache.put(f"text-{i}", "default", 1.0, 1.0, b"data")

        time.sleep(1.5)
        removed = cache.cleanup_expired()
        assert removed == 3
        assert cache.total_entries == 0

    def test_stats(self, cache):
        """Stats should accurately reflect cache state."""
        cache.put("test", "default", 1.0, 1.0, b"hello-world")
        cache.get("test", "default", 1.0, 1.0)  # hit
        cache.get("missing", "default", 1.0, 1.0)  # miss

        stats = cache.get_stats()
        assert stats.total_entries == 1
        assert stats.cache_hits == 1
        assert stats.cache_misses == 1
        assert stats.total_requests == 2
        assert stats.hit_rate_percent == 50.0

    def test_file_persistence(self, cache, temp_cache_dir):
        """Audio files should be written to disk."""
        cache.put("persist", "default", 1.0, 1.0, b"audio-bytes")

        # Config compression defaults to True, checking for .mp3.gz or .mp3
        mp3_files = [f for f in os.listdir(temp_cache_dir) if f.endswith(".mp3") or f.endswith(".mp3.gz")]
        assert len(mp3_files) == 1


# ── Simulated TTS Tests ──────────────────────────────────────

class TestSimulatedTTS:
    def test_generates_wav(self):
        """Simulated TTS should produce valid WAV bytes."""
        audio = simulated_tts.synthesize("hello", delay=0)  # No delay in tests
        assert audio[:4] == b"RIFF"
        assert audio[8:12] == b"WAVE"

    def test_different_text_different_tone(self):
        """Different text should produce different audio."""
        audio1 = simulated_tts.synthesize("hello", delay=0)
        audio2 = simulated_tts.synthesize("goodbye", delay=0)
        # Audio bytes should differ (different frequencies)
        assert audio1 != audio2

    def test_delay_works(self):
        """Simulated delay should actually pause."""
        start = time.perf_counter()
        simulated_tts.synthesize("hello", delay=0.5)
        elapsed = time.perf_counter() - start
        assert elapsed >= 0.4  # Allow small variance


# ── API Integration Tests ────────────────────────────────────

class TestAPI:
    @pytest.fixture(autouse=True)
    def setup_app(self, temp_cache_dir):
        """Create a fresh app + cache for each test."""
        from fastapi.testclient import TestClient
        from api.routes import router, cache as route_cache

        # Reset the cache to use temp dir
        route_cache.__init__(
            cache_dir=temp_cache_dir,
            max_entries=100,
            max_size_mb=10,
            ttl_seconds=3600,
            index_file=os.path.join(temp_cache_dir, "cache_index.json"),
        )

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)
        self.cache = route_cache

    def test_synthesize_miss_then_hit(self):
        """First call is a miss, second is a hit."""
        payload = {"text": "test phrase", "voice_id": "default", "speed": 1.0, "pitch": 1.0}

        # First call — miss
        resp1 = self.client.post("/api/tts/synthesize", json=payload)
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert data1["cache_hit"] is False

        # Second call — hit
        resp2 = self.client.post("/api/tts/synthesize", json=payload)
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["cache_hit"] is True
        assert data2["cache_key"] == data1["cache_key"]

    def test_get_stats(self):
        """Stats endpoint returns valid data."""
        resp = self.client.get("/api/cache/stats")
        assert resp.status_code == 200
        stats = resp.json()
        assert "total_entries" in stats
        assert "hit_rate_percent" in stats

    def test_get_entries_empty(self):
        """Entries endpoint returns empty list initially."""
        resp = self.client.get("/api/cache/entries")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_clear_cache(self):
        """Clear endpoint removes all entries."""
        # Add an entry first
        self.client.post("/api/tts/synthesize", json={"text": "to delete"})
        assert self.cache.total_entries == 1

        resp = self.client.delete("/api/cache/clear")
        assert resp.status_code == 200
        assert self.cache.total_entries == 0

    def test_invalidate_entry(self):
        """Delete a specific entry by key."""
        resp = self.client.post("/api/tts/synthesize", json={"text": "to invalidate"})
        key = resp.json()["cache_key"]

        del_resp = self.client.delete(f"/api/cache/entry/{key}")
        assert del_resp.status_code == 200

        assert self.cache.total_entries == 0

    def test_invalidate_nonexistent(self):
        """Deleting a nonexistent key returns 404."""
        resp = self.client.delete("/api/cache/entry/fake-key")
        assert resp.status_code == 404


# ── Smart Features Tests ─────────────────────────────────────

class TestSmartFeatures:
    def test_get_predictions(self):
        """get_predictions should return next steps in the flow."""
        from tts_cache.smart_cache import get_predictions
        
        preds = get_predictions("Tell me about yourself.")
        assert len(preds) > 0
        assert "What are your strengths?" in preds or "Why do you want to work here?" in preds

        # Fuzzy match predictive caching
        preds_fuzzy = get_predictions("could you tell me about yourself?")
        assert len(preds_fuzzy) > 0
        assert "What are your strengths?" in preds_fuzzy

    def test_get_recommendations(self, cache):
        """get_recommendations should recommend items to cache based on cache state."""
        recs = cache.get_recommendations()
        assert len(recs) > 0
        # Should recommend WARMUP_PROMPTS since cache is empty
        assert any(r["text"] == "Tell me about yourself." for r in recs)

        # Cache one, check it is marked as cached or not in recommendations
        cache.put("Tell me about yourself.", "default", 1.0, 1.0, b"audio")
        recs2 = cache.get_recommendations()
        
        # Check if the cached item is skipped or marked as cached
        for r in recs2:
            if r["text"] == "Tell me about yourself.":
                assert r["cached"] is True

