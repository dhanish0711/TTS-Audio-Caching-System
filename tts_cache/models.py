"""
TTS Audio Caching System — Data Models (Enhanced)
===================================================
Pydantic models for requests, responses, cache entries,
statistics, and request analytics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Request / Response ────────────────────────────────────────

class TTSRequest(BaseModel):
    """Incoming TTS synthesis request."""
    text: str = Field(..., min_length=1, description="Text to synthesize")
    voice_id: str = Field(default="default", description="Voice model identifier")
    speed: float = Field(default=1.0, ge=0.25, le=4.0, description="Playback speed")
    pitch: float = Field(default=1.0, ge=0.5, le=2.0, description="Pitch adjustment")


class TTSResponse(BaseModel):
    """Response returned after synthesis."""
    audio_url: str = Field(..., description="URL to the generated audio file")
    cache_hit: bool = Field(..., description="Whether the result was served from cache")
    fuzzy_match: bool = Field(default=False, description="Whether a fuzzy match was used")
    similarity_score: float = Field(default=1.0, description="Fuzzy matching similarity ratio (0.0 to 1.0)")
    latency_ms: float = Field(..., description="Total processing time in milliseconds")
    cache_key: str = Field(..., description="Cache key for this request")
    text: str = Field(..., description="Original text that was synthesized")
    predictive_cache_triggered: list[str] = Field(default_factory=list, description="List of prompts predicted and warmed in background")


# ── Cache Internals ───────────────────────────────────────────

class CacheEntry(BaseModel):
    """Metadata for a single cached audio item."""
    cache_key: str
    text: str
    voice_id: str
    speed: float
    pitch: float
    file_path: str
    file_size_bytes: int
    original_size_bytes: int = 0
    created_at: datetime
    last_accessed_at: datetime
    access_count: int = 0
    ttl_seconds: int
    compressed: bool = False


class CacheStats(BaseModel):
    """Aggregate cache statistics."""
    total_entries: int = 0
    total_size_bytes: int = 0
    total_size_mb: float = 0.0
    max_entries: int = 0
    max_size_mb: int = 0
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    fuzzy_hits: int = 0
    hit_rate_percent: float = 0.0
    avg_hit_latency_ms: float = 0.0
    avg_miss_latency_ms: float = 0.0
    compression_ratio: float = 0.0
    compression_enabled: bool = False
    fuzzy_match_enabled: bool = False
    oldest_entry: Optional[datetime] = None
    newest_entry: Optional[datetime] = None


# ── Analytics ─────────────────────────────────────────────────

class RequestRecord(BaseModel):
    """Record of a single TTS request for analytics."""
    timestamp: datetime
    text: str
    cache_hit: bool
    fuzzy_match: bool = False
    similarity_score: float = Field(default=1.0, description="Fuzzy matching similarity ratio (0.0 to 1.0)")
    latency_ms: float
    cache_key: str
