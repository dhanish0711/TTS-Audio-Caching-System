"""
TTS Audio Caching System — Simulated TTS Engine
=================================================
Generates a short WAV sine-wave tone to simulate real TTS output.
An artificial delay makes cache-hit vs cache-miss latency obvious.
"""

import io
import math
import struct
import time
from typing import Optional

from config import TTS_SIMULATED_DELAY, TTS_SAMPLE_RATE, TTS_AUDIO_DURATION


def _generate_sine_wave(
    frequency: float = 440.0,
    duration: float = TTS_AUDIO_DURATION,
    sample_rate: int = TTS_SAMPLE_RATE,
    amplitude: float = 0.5,
) -> bytes:
    """Generate a mono 16-bit PCM WAV file in memory.

    Args:
        frequency: Tone frequency in Hz.
        duration: Duration in seconds.
        sample_rate: Samples per second.
        amplitude: Volume (0.0 – 1.0).

    Returns:
        Raw WAV file bytes.
    """
    num_samples = int(sample_rate * duration)
    max_val = 32767  # 16-bit signed max

    # Generate PCM samples
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = int(amplitude * max_val * math.sin(2 * math.pi * frequency * t))
        samples.append(struct.pack("<h", value))

    pcm_data = b"".join(samples)

    # Build WAV header
    buf = io.BytesIO()
    data_size = len(pcm_data)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8

    # RIFF header
    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_size))
    buf.write(b"WAVE")
    # fmt sub-chunk
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))              # Sub-chunk size
    buf.write(struct.pack("<H", 1))               # PCM format
    buf.write(struct.pack("<H", num_channels))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", byte_rate))
    buf.write(struct.pack("<H", block_align))
    buf.write(struct.pack("<H", bits_per_sample))
    # data sub-chunk
    buf.write(b"data")
    buf.write(struct.pack("<I", data_size))
    buf.write(pcm_data)

    return buf.getvalue()


def synthesize(
    text: str,
    voice_id: str = "default",
    speed: float = 1.0,
    pitch: float = 1.0,
    delay: Optional[float] = None,
) -> bytes:
    """Simulate TTS synthesis.

    Generates a sine-wave tone whose frequency varies slightly based on
    the text hash, so different texts produce slightly different tones.
    Includes an artificial delay to mimic real TTS engine latency.

    Args:
        text: Input text (affects output tone frequency slightly).
        voice_id: Voice identifier (unused in simulation).
        speed: Speed multiplier (affects tone duration).
        pitch: Pitch multiplier (scales frequency).
        delay: Override simulated delay (defaults to config value).

    Returns:
        WAV file bytes.
    """
    # Artificial delay to simulate real TTS processing
    actual_delay = delay if delay is not None else TTS_SIMULATED_DELAY
    time.sleep(actual_delay)

    # Vary frequency based on text content for some variety
    text_hash = sum(ord(c) for c in text) % 200
    base_freq = 300 + text_hash  # 300–500 Hz range
    frequency = base_freq * pitch
    duration = TTS_AUDIO_DURATION / speed

    return _generate_sine_wave(frequency=frequency, duration=duration)
