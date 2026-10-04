"""Query rewriting and conversation-aware context resolution.

Handles:
- Normalization and punctuation cleanup
- Known typos / common terminology normalization
- Conversation history coreference resolution (e.g. 'it', 'the error', 'that')
"""
import re
from typing import Dict, List, Optional


class QueryRewriter:
    """Normalizes and resolves queries for downstream search."""

    # Common search typos and colloquialisms mapping
    DEFAULT_CANONICAL_MAP: Dict[str, str] = {
        "seperate": "separate",
        "retreival": "retrieval",
        "retreive": "retrieve",
        "embeding": "embedding",
        "embedings": "embeddings",
        "vectordb": "vector database",
        "faiss": "FAISS",
        "bm25": "BM25",
        "whats": "what is",
        "hows": "how is",
    }

    def __init__(self, canonical_map: Optional[Dict[str, str]] = None):
        self.canonical_map = (
            canonical_map if canonical_map is not None else self.DEFAULT_CANONICAL_MAP
        )

    def normalize(self, query: str) -> str:
        """Strip redundant whitespace, normalize casing/punctuation."""
        if not query:
            return ""
        q = re.sub(r"\s+", " ", query.strip())
        tokens = q.split()
        normalized_tokens = []
        for t in tokens:
            low = t.lower().strip("?,.!")
            if low in self.canonical_map:
                normalized_tokens.append(self.canonical_map[low])
            else:
                normalized_tokens.append(t)
        return " ".join(normalized_tokens)

    def rewrite_with_history(
        self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Resolve pronouns ('it', 'this error', 'that') using recent chat turns.

        conversation_history: list of {"role": "user"|"assistant", "content": str}
        """
        cleaned = self.normalize(query)
        if not conversation_history:
            return cleaned

        # Detect pronouns or generic anaphora
        anaphora_pattern = re.compile(
            r"\b(it|this|that|its|these|those|the error|the issue|the problem)\b",
            re.IGNORECASE,
        )
        if not anaphora_pattern.search(cleaned):
            return cleaned

        # Scan previous turns in reverse to find prominent entities/topics
        antecedent = None
        for turn in reversed(conversation_history):
            content = turn.get("content", "")
            # Look for uppercase code/identifier patterns like CODE-42, ERR-101
            match_id = re.search(r"\b[A-Z]+-\d+\b", content)
            if match_id:
                antecedent = match_id.group(0)
                break
            # Fallback to key nouns/topics if no identifier found
            tokens = [w for w in re.findall(r"\b\w{4,}\b", content) if w.lower() not in {"what", "how", "does", "mean", "help", "with"}]
            if tokens and antecedent is None:
                antecedent = tokens[-1]

        if antecedent:
            # Replace ambiguous pronouns or append context
            rewritten = anaphora_pattern.sub(antecedent, cleaned, count=1)
            # If substitution resulted in exact repetition or wasn't cleanly applied, enrich
            if antecedent.lower() not in rewritten.lower():
                rewritten = f"{rewritten} ({antecedent})"
            return rewritten

        return cleaned
