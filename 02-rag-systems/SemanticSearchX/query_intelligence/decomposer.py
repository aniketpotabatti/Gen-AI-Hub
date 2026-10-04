"""Query decomposition for compound, multi-part, or comparative queries."""
import re
from typing import List


class QueryDecomposer:
    """Decomposes compound or multi-topic questions into atomic sub-queries."""

    SPLIT_PATTERNS = [
        # Explicit questions: 'How does X work and what is Y?'
        r"\band\s+(?:what|how|why|when|where|can|is|does)\b",
        # Disjunctions / list questions: 'X as well as Y'
        r"\bas\s+well\s+as\b",
        # Semicolons or commas before question words
        r"[;]\s*",
        # Comparative splitters
        r"\b(?:versus|vs\.?|compared\s+to|difference\s+between)\b",
    ]

    def decompose(self, query: str) -> List[str]:
        """Split a query into distinct focused sub-queries."""
        q = (query or "").strip()
        if not q:
            return []

        # Check if query has multiple question marks
        parts = [p.strip() for p in re.split(r"\?+", q) if p.strip()]
        if len(parts) > 1:
            return [f"{p}?" if not p.endswith("?") else p for p in parts]

        # Check regex splitting patterns
        combined_pattern = "|".join(f"(?:{p})" for p in self.SPLIT_PATTERNS)
        splits = re.split(combined_pattern, q, flags=re.IGNORECASE)
        sub_queries = [s.strip(" ?,.!") for s in splits if s.strip(" ?,.!")]

        if len(sub_queries) <= 1:
            return [q]
        return sub_queries
