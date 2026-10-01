"""Query difficulty and ambiguity estimation.

Provides a heuristic score between 0.0 (very easy/specific) and 1.0 (very difficult/ambiguous).
Factors considered:
- Query length (extremely short queries are underspecified; very long queries are noisy)
- Entity specificity (presence of exact identifiers lowers difficulty)
- Vagueness / stopwords ratio
- Presence of multiple topics or complex conjunctions
"""
import re
from typing import Dict, Any


VAGUE_TERMS = {
    "something", "anything", "stuff", "thing", "things", "what", "how",
    "why", "help", "issue", "problem", "tell", "explain", "info", "information"
}


def estimate_query_difficulty(query: str) -> Dict[str, Any]:
    """Estimate the retrieval difficulty and provide actionable reasoning."""
    q = (query or "").strip()
    if not q:
        return {"score": 1.0, "level": "hard", "reasons": ["empty_query"]}

    words = re.findall(r"\b\w+\b", q)
    num_words = len(words)
    reasons = []
    score = 0.5  # Baseline neutral difficulty

    # Factor 1: Length extremes
    if num_words <= 2:
        score += 0.25
        reasons.append("too_short_underspecified")
    elif num_words >= 15:
        score += 0.2
        reasons.append("verbose_complex_syntax")
    else:
        score -= 0.1

    # Factor 2: Presence of explicit identifiers or codes (dramatically lowers ambiguity)
    has_code = bool(re.search(r"\b[A-Z]+-\d+\b|\b[A-Z]{2,}_\w+\b", q))
    has_quotes = bool(re.search(r"[\"'][^\"']+[\"']", q))
    if has_code or has_quotes:
        score -= 0.3
        reasons.append("has_exact_identifier_or_quote")

    # Factor 3: Vagueness & stopword density
    low_words = [w.lower() for w in words]
    vague_count = sum(1 for w in low_words if w in VAGUE_TERMS)
    vague_ratio = vague_count / max(1, num_words)
    if vague_ratio >= 0.5:
        score += 0.2
        reasons.append("high_vague_term_ratio")

    # Factor 4: Conjunctions and multi-part queries
    if bool(re.search(r"\b(and|or|vs|versus|also|except)\b", q, re.IGNORECASE)):
        score += 0.1
        reasons.append("multi_part_or_conjunction")

    # Clamp score to [0.0, 1.0]
    score = max(0.0, min(1.0, round(score, 2)))

    if score <= 0.35:
        level = "easy"
    elif score <= 0.65:
        level = "medium"
    else:
        level = "hard"

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
    }
