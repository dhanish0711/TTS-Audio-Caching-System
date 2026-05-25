"""
TTS Audio Caching System — Enhanced FastAPI Routes
====================================================
REST API endpoints with real TTS, cache warming,
analytics, and fuzzy matching support.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, Response

from config import TTS_ENGINE
from tts_cache.cache_manager import TTSAudioCache
from tts_cache.hash_utils import generate_cache_key
from tts_cache.models import TTSRequest, TTSResponse, CacheStats, RequestRecord
from tts_cache.smart_cache import WARMUP_PROMPTS

# ── Shared cache instance ─────────────────────────────────────
cache = TTSAudioCache()

router = APIRouter(prefix="/api")


def _get_tts_engine():
    """Get the configured TTS engine module."""
    if TTS_ENGINE == "gtts":
        from tts_cache import real_tts
        return real_tts
    else:
        from tts_cache import simulated_tts
        return simulated_tts


# ── TTS Synthesis ─────────────────────────────────────────────

def _predictive_warmup_task(predicted_texts: list[str], voice_id: str, speed: float, pitch: float):
    """Background task to pre-cache predicted sequential questions."""
    tts_engine = _get_tts_engine()
    for text in predicted_texts:
        try:
            # Check cache entries to avoid repeating work
            cached_keys = {entry.cache_key for entry in cache.get_entries()}
            pred_key = generate_cache_key(text, voice_id, speed, pitch)
            if pred_key not in cached_keys:
                print(f"[Predictive Cache] Generating background audio for: '{text}'")
                audio_data = tts_engine.synthesize(
                    text=text,
                    voice_id=voice_id,
                    speed=speed,
                    pitch=pitch,
                )
                cache.put(
                    text=text,
                    voice_id=voice_id,
                    speed=speed,
                    pitch=pitch,
                    audio_data=audio_data,
                )
        except Exception as e:
            print(f"[Predictive Cache] Failed to warm prompt '{text}': {e}")


@router.post("/tts/synthesize", response_model=TTSResponse)
async def synthesize(request: TTSRequest, background_tasks: BackgroundTasks):
    """Synthesize text to audio with cache-first strategy, fuzzy matching, and predictive caching."""
    start = time.perf_counter()

    # 1. Try cache (includes fuzzy matching)
    result = cache.get(request.text, request.voice_id, request.speed, request.pitch)

    # Calculate predictions for predictive caching
    from tts_cache.smart_cache import get_predictions
    predicted_prompts = get_predictions(request.text)
    triggered = []

    # Detect which predicted prompts need background warming
    if predicted_prompts:
        cached_keys = {entry.cache_key for entry in cache.get_entries()}
        for pred in predicted_prompts:
            pred_key = generate_cache_key(pred, request.voice_id, request.speed, request.pitch)
            if pred_key not in cached_keys:
                triggered.append(pred)

    if result is not None:
        _audio_data, cache_key, is_fuzzy, similarity = result
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Record analytics
        cache.add_request_record(RequestRecord(
            timestamp=datetime.now(timezone.utc),
            text=request.text,
            cache_hit=True,
            fuzzy_match=is_fuzzy,
            similarity_score=similarity,
            latency_ms=round(elapsed_ms, 2),
            cache_key=cache_key,
        ))

        # Run background warming if predicted queries exist
        if triggered:
            background_tasks.add_task(_predictive_warmup_task, triggered, request.voice_id, request.speed, request.pitch)

        return TTSResponse(
            audio_url=f"/api/cache/audio/{cache_key}",
            cache_hit=True,
            fuzzy_match=is_fuzzy,
            similarity_score=similarity,
            latency_ms=round(elapsed_ms, 2),
            cache_key=cache_key,
            text=request.text,
            predictive_cache_triggered=triggered,
        )

    # 2. Cache miss — synthesize with real or simulated TTS
    tts_engine = _get_tts_engine()
    audio_data = tts_engine.synthesize(
        text=request.text,
        voice_id=request.voice_id,
        speed=request.speed,
        pitch=request.pitch,
    )

    # 3. Store in cache
    cache_key = cache.put(
        text=request.text,
        voice_id=request.voice_id,
        speed=request.speed,
        pitch=request.pitch,
        audio_data=audio_data,
    )

    elapsed_ms = (time.perf_counter() - start) * 1000
    cache.record_miss_latency(elapsed_ms)

    # Record analytics
    cache.add_request_record(RequestRecord(
        timestamp=datetime.now(timezone.utc),
        text=request.text,
        cache_hit=False,
        fuzzy_match=False,
        similarity_score=1.0,
        latency_ms=round(elapsed_ms, 2),
        cache_key=cache_key,
    ))

    # Run background warming if predicted queries exist
    if triggered:
        background_tasks.add_task(_predictive_warmup_task, triggered, request.voice_id, request.speed, request.pitch)

    return TTSResponse(
        audio_url=f"/api/cache/audio/{cache_key}",
        cache_hit=False,
        fuzzy_match=False,
        similarity_score=1.0,
        latency_ms=round(elapsed_ms, 2),
        cache_key=cache_key,
        text=request.text,
        predictive_cache_triggered=triggered,
    )


# ── Audio File Serving ────────────────────────────────────────

@router.get("/cache/audio/{cache_key}")
async def get_audio(cache_key: str):
    """Serve a cached audio file (decompressed on-the-fly)."""
    import os
    import gzip
    from config import CACHE_DIR

    # Try compressed first, then raw
    for ext in [".mp3.gz", ".mp3", ".wav.gz", ".wav"]:
        file_path = os.path.join(CACHE_DIR, f"{cache_key}{ext}")
        if os.path.isfile(file_path):
            if file_path.endswith(".gz"):
                with open(file_path, "rb") as f:
                    data = gzip.decompress(f.read())
                media = "audio/mpeg" if ".mp3" in ext else "audio/wav"
                return Response(content=data, media_type=media)
            else:
                media = "audio/mpeg" if ext == ".mp3" else "audio/wav"
                return FileResponse(file_path, media_type=media, filename=f"{cache_key}{ext}")

    raise HTTPException(status_code=404, detail="Audio file not found")


# ── Cache Statistics ──────────────────────────────────────────

@router.get("/cache/stats", response_model=CacheStats)
async def get_stats():
    """Return aggregate cache statistics."""
    return cache.get_stats()


# ── Cache Entries ─────────────────────────────────────────────

@router.get("/cache/entries")
async def get_entries():
    """List all cached entries with metadata."""
    entries = cache.get_entries()
    return [entry.model_dump(mode="json") for entry in entries]


# ── Request History (Analytics) ───────────────────────────────

@router.get("/cache/history")
async def get_history():
    """Get request history for analytics charts."""
    history = cache.get_request_history()
    return [record.model_dump(mode="json") for record in history]


# ── Cache Warming ─────────────────────────────────────────────

@router.post("/cache/warmup")
async def warmup_cache():
    """Pre-cache common interview prompts using the TTS engine."""
    tts_engine = _get_tts_engine()
    warmed = 0
    skipped = 0

    for prompt in WARMUP_PROMPTS:
        # Check if already cached
        result = cache.get(prompt, "default", 1.0, 1.0)
        if result is not None:
            skipped += 1
            continue

        try:
            audio_data = tts_engine.synthesize(text=prompt)
            cache.put(
                text=prompt,
                voice_id="default",
                speed=1.0,
                pitch=1.0,
                audio_data=audio_data,
            )
            warmed += 1
        except Exception as e:
            pass  # Skip failed prompts

    return {
        "status": "complete",
        "prompts_warmed": warmed,
        "prompts_skipped": skipped,
        "total_prompts": len(WARMUP_PROMPTS),
    }

@router.get("/cache/warmup/prompts")
async def get_warmup_prompts():
    """Return the list of prompts available for cache warming."""
    return {"prompts": WARMUP_PROMPTS}


# ── Cache Invalidation ────────────────────────────────────────

@router.delete("/cache/entry/{cache_key}")
async def invalidate_entry(cache_key: str):
    """Remove a specific entry from the cache."""
    removed = cache.invalidate(cache_key)
    if not removed:
        raise HTTPException(status_code=404, detail="Cache entry not found")
    return {"status": "removed", "cache_key": cache_key}


@router.delete("/cache/clear")
async def clear_cache():
    """Remove all entries from the cache."""
    count = cache.clear()
    return {"status": "cleared", "entries_removed": count}


@router.post("/cache/cleanup")
async def cleanup_expired():
    """Remove expired entries from the cache."""
    count = cache.cleanup_expired()
    return {"status": "cleanup_complete", "entries_removed": count}


@router.get("/cache/recommendations")
async def get_cache_recommendations():
    """Fetch smart prompts recommendations."""
    return cache.get_recommendations()
