"""
TTS Audio Caching System — Configuration
==========================================
Central configuration for cache behaviour, server settings,
TTS engine selection, and analytics.
"""

import os

# ── Cache Settings ────────────────────────────────────────────
CACHE_MAX_ENTRIES: int = 1000          # Max number of cached audio entries
CACHE_MAX_SIZE_MB: int = 500           # Max total cache size in megabytes
CACHE_TTL_SECONDS: int = 3600          # Time-to-live per entry (1 hour)
CACHE_DIR: str = os.path.join(os.path.dirname(__file__), "cache_store")
CACHE_INDEX_FILE: str = os.path.join(os.path.dirname(__file__), "cache_store", "cache_index.json")
CACHE_COMPRESSION: bool = True         # Enable gzip compression for stored audio

# ── TTS Engine ────────────────────────────────────────────────
TTS_ENGINE: str = "gtts"               # "gtts" for Google TTS, "simulated" for sine-wave demo
TTS_SIMULATED_DELAY: float = 2.0       # Seconds of artificial delay (simulated engine only)
TTS_SAMPLE_RATE: int = 22050           # WAV sample rate for simulated engine
TTS_AUDIO_DURATION: float = 1.5        # Generated tone duration (simulated engine only)
TTS_DEFAULT_LANG: str = "en"           # Default language for gTTS

# ── AI / Smart Features ──────────────────────────────────────
FUZZY_MATCH_ENABLED: bool = True       # Enable fuzzy text matching for near-miss cache hits
FUZZY_MATCH_THRESHOLD: float = 0.85    # Similarity ratio threshold (0.0 - 1.0)

# ── Analytics ─────────────────────────────────────────────────
REQUEST_HISTORY_MAX: int = 200         # Max number of requests to track in history
ANALYTICS_ENABLED: bool = True         # Enable request analytics tracking

# ── Server Settings ───────────────────────────────────────────
SERVER_HOST: str = "0.0.0.0"
SERVER_PORT: int = 8007
