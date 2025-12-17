from __future__ import annotations

import re
from typing import Dict

POSITIVE_WORDS = {"good", "great", "excellent", "happy", "love", "awesome", "cool", "profit"}
NEGATIVE_WORDS = {"bad", "terrible", "sad", "angry", "hate", "awful", "loss", "problem"}

WORD_RE = re.compile(r"\b\w+\b", re.UNICODE)


def analyze_text(text: str) -> Dict[str, float | str | int]:
    tokens = WORD_RE.findall(text.lower())
    word_count = len(tokens)
    char_count = len(text)

    if not tokens:
        sentiment_score = 0.0
    else:
        positive_hits = sum(token in POSITIVE_WORDS for token in tokens)
        negative_hits = sum(token in NEGATIVE_WORDS for token in tokens)
        sentiment_score = (positive_hits - negative_hits) / max(word_count, 1)

    if sentiment_score > 0.1:
        sentiment = "positive"
    elif sentiment_score < -0.1:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "word_count": word_count,
        "char_count": char_count,
        "sentiment": sentiment,
        "sentiment_score": round(float(sentiment_score), 4),
    }
