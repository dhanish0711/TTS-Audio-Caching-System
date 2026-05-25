"""
TTS Audio Caching System — AI-Powered Smart Features
======================================================
Fuzzy text matching, cache warming predictions, and
intelligent cache management.
"""

from __future__ import annotations

import difflib
from typing import Optional, Tuple

from config import FUZZY_MATCH_THRESHOLD


def fuzzy_find_match(
    query_text: str,
    cached_texts: dict[str, str],
    threshold: float = FUZZY_MATCH_THRESHOLD,
) -> Optional[Tuple[str, float]]:
    """Find the closest matching cached text using fuzzy string matching.

    Uses SequenceMatcher for intelligent similarity scoring that
    considers word order, insertions, and deletions.

    Args:
        query_text: The new text to find a match for.
        cached_texts: Dict mapping cache_key -> original text.
        threshold: Minimum similarity ratio to accept (0.0 - 1.0).

    Returns:
        Tuple of (cache_key, similarity_ratio) if match found, else None.
    """
    normalized_query = _normalize(query_text)
    best_key = None
    best_ratio = 0.0

    for key, text in cached_texts.items():
        normalized_cached = _normalize(text)
        ratio = difflib.SequenceMatcher(
            None, normalized_query, normalized_cached
        ).ratio()

        if ratio > best_ratio:
            best_ratio = ratio
            best_key = key

    if best_key and best_ratio >= threshold:
        return best_key, best_ratio

    return None


def _normalize(text: str) -> str:
    """Normalize text for comparison."""
    import re
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    # Remove trailing punctuation variations
    text = re.sub(r"[.!?]+$", "", text)
    return text


# Common interview prompts for cache warming
WARMUP_PROMPTS = [
    "Tell me about yourself.",
    "What are your strengths?",
    "What are your weaknesses?",
    "Why should we hire you?",
    "Where do you see yourself in five years?",
    "Why do you want to work here?",
    "Tell me about a challenging situation you faced.",
    "What is your greatest achievement?",
    "Do you have any questions for us?",
    "Describe your ideal work environment.",
    "How do you handle stress and pressure?",
    "What motivates you?",
    "Tell me about your experience with teamwork.",
    "How do you prioritize your tasks?",
    "What are your salary expectations?",
]

# Sequential flow mapping representing typical interview dialog states
INTERVIEW_FLOW = {
    "tell me about yourself": [
        "what are your strengths?",
        "why do you want to work here?"
    ],
    "what are your strengths?": [
        "what are your weaknesses?",
        "what is your greatest achievement?"
    ],
    "what are your weaknesses?": [
        "describe your ideal work environment.",
        "how do you handle stress and pressure?"
    ],
    "why should we hire you?": [
        "where do you see yourself in five years?",
        "what motivates you?"
    ],
    "why do you want to work here?": [
        "where do you see yourself in five years?",
        "do you have any questions for us?"
    ],
    "do you have any questions for us?": [
        "what are your salary expectations?"
    ]
}

def get_predictions(text: str) -> list[str]:
    """Predict the next 1-2 most likely questions based on the current prompt.
    Uses fuzzy string matching to map the input query to a state in INTERVIEW_FLOW.
    """
    normalized_input = _normalize(text)
    best_key = None
    best_ratio = 0.0

    # Match normalized text against key states in the flow
    for key in INTERVIEW_FLOW.keys():
        ratio = difflib.SequenceMatcher(None, normalized_input, key).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_key = key

    # If the closest state matches with >= 80% similarity, return its predictions
    if best_key and best_ratio >= 0.8:
        # Resolve predicted lowercase prompts back to their title-case equivalents
        predictions_lower = INTERVIEW_FLOW[best_key]
        resolved = []
        for pred in predictions_lower:
            for wp in WARMUP_PROMPTS:
                if _normalize(wp) == pred:
                    resolved.append(wp)
                    break
            else:
                # Fallback to Title case if not in WARMUP_PROMPTS
                resolved.append(pred.capitalize())
        return resolved

    return []

