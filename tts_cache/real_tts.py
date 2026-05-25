"""
TTS Audio Caching System — Real TTS Engine (Google TTS)
========================================================
Uses Google's Text-to-Speech API via the gTTS library
to generate actual human-quality speech audio.
"""

import io
from gtts import gTTS

from config import TTS_DEFAULT_LANG


def synthesize(
    text: str,
    voice_id: str = "default",
    speed: float = 1.0,
    pitch: float = 1.0,
    lang: str = TTS_DEFAULT_LANG,
    **kwargs,
) -> bytes:
    """Synthesize text to speech using Google TTS.

    Args:
        text: Text to convert to speech.
        voice_id: Voice identifier (maps to language/tld variant).
        speed: Speed multiplier (slow=True if speed < 0.8).
        pitch: Pitch adjustment (not directly supported by gTTS, reserved for future).
        lang: Language code (e.g., 'en', 'es', 'fr').

    Returns:
        MP3 audio bytes.
    """
    # Map voice_id to gTTS tld for accent variation
    tld_map = {
        "default": "com",
        "female-1": "co.uk",   # British accent
        "male-1": "com.au",    # Australian accent
        "female-2": "co.in",   # Indian accent
        "male-2": "ca",        # Canadian accent
    }
    tld = tld_map.get(voice_id, "com")
    slow = speed < 0.8

    tts = gTTS(text=text, lang=lang, slow=slow, tld=tld)

    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()
