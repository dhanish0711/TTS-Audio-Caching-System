"""
TTS Audio Caching System — Hash Utilities
==========================================
Deterministic cache-key generation from text + voice parameters.
"""

import hashlib
import re


def _normalize_text(text: str) -> str:
    """Normalize text for consistent cache keying.

    - Strip leading/trailing whitespace
    - Convert to lowercase
    - Collapse multiple whitespace into a single space
    """
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def generate_cache_key(
    text: str,
    voice_id: str = "default",
    speed: float = 1.0,
    pitch: float = 1.0,
) -> str:
    """Generate a deterministic SHA-256 cache key.

    The key is derived from the normalized text combined with the voice
    configuration parameters so that different voice settings for the
    same text produce distinct cache entries.

    Args:
        text: The text to be synthesized.
        voice_id: Identifier for the voice/model to use.
        speed: Playback speed multiplier (1.0 = normal).
        pitch: Pitch adjustment multiplier (1.0 = normal).

    Returns:
        A 64-character hex SHA-256 digest.
    """
    normalized = _normalize_text(text)
    composite = f"{normalized}|{voice_id}|{speed:.4f}|{pitch:.4f}"
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()
