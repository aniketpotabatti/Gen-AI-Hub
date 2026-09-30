"""Rule-based query classifier.

Categories (plan Phase 4):
- identifier: error codes, IDs, versions, paths, exact strings in quotes
- comparison: X vs Y / difference / compare / better / pros and cons
- version: version/change queries (v1.2, changelog, what's new, diff, upgrade)
- evidence: evidence queries (prove, cite, source, statistics, how many)
- conceptual: everything else -> semantic retrieval
"""
import re
from typing import Dict, List

_PATTERNS: Dict[str, List[str]] = {
    "identifier": [
        r"\b[A-Z]+-\d+\b",          # CODE-42, ERR-17
        r"\bERR(OR)?\s*\d+\b",
        r"\bv\d+\.\d+",             # v2.3
        r"\b[0-9a-f]{7,40}\b",      # commit hashes
        r"[\"'][^\"']+[\"']",       # quoted exact strings
        r"\b[A-Z]{2,}[_-]\w+",      # CONST_NAME, PREFIX-id
        r"\b\w+\.\w+\(\)",          # function calls
        r"/[\w./-]+",               # file paths
    ],
    "comparison": [
        r"\bvs\.?\b", r"\bversus\b", r"\bcompar",
        r"\bdifference between\b", r"\bbetter\b",
        r"\bpros and cons\b", r"\btrade[- ]?off",
    ],
    "version": [
        r"\bchangelog\b", r"\bwhat'?s new\b", r"\bmigrat",
        r"\bupgrad", r"\bbreaking change\b", r"\bdiff\b",
        r"\bversion\b", r"\brelease\b",
    ],
    "evidence": [
        r"\bprove\b", r"\bproof\b", r"\bcite\b", r"\bcitation\b",
        r"\bsource\b", r"\bstatistic", r"\bhow many\b",
        r"\bevidence\b", r"\bstudy\b", r"\bpaper\b",
    ],
}

_COMPILED = {k: [re.compile(p, re.IGNORECASE) for p in v]
             for k, v in _PATTERNS.items()}

# Priority when several categories match: most specific first.
_PRIORITY = ["identifier", "comparison", "version", "evidence"]


def classify(query: str) -> Dict[str, object]:
    """Return {category, confidence, signals} for a query string."""
    q = (query or "").strip()
    if not q:
        return {"category": "conceptual", "confidence": 0.0, "signals": []}
    hits: Dict[str, List[str]] = {}
    for cat, patterns in _COMPILED.items():
        matched = [p.pattern for p in patterns if p.search(q)]
        if matched:
            hits[cat] = matched
    if not hits:
        # Short keyword queries lean lexical; longer ones semantic.
        if len(q.split()) <= 3:
            return {"category": "identifier", "confidence": 0.35,
                    "signals": ["short-keyword-query"]}
        return {"category": "conceptual", "confidence": 0.5, "signals": []}
    for cat in _PRIORITY:
        if cat in hits:
            conf = min(0.6 + 0.1 * len(hits[cat]), 0.95)
            return {"category": cat, "confidence": conf, "signals": hits[cat]}
    return {"category": "conceptual", "confidence": 0.5, "signals": []}
