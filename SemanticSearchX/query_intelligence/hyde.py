"""Hypothetical Document Embeddings (HyDE) generator.

Generates a pseudo-document / answer snippet from a query without requiring
an external LLM service, using template-driven synthesis or an optional callable generator.
The hypothetical document can then be embedded to bridge the query-to-document vocabulary gap.
"""
from typing import Callable, Optional


class HyDEGenerator:
    """Generates synthetic hypothetical answer documents to improve dense retrieval."""

    def __init__(self, generator_fn: Optional[Callable[[str], str]] = None):
        self.generator_fn = generator_fn

    def generate(self, query: str) -> str:
        """Create a hypothetical document addressing the query."""
        q = (query or "").strip()
        if not q:
            return ""

        if self.generator_fn is not None:
            try:
                res = self.generator_fn(q)
                if res and res.strip():
                    return res.strip()
            except Exception:
                pass  # Fallback to heuristic expansion

        # Heuristic / template-based pseudo-document generation
        clean = q.rstrip("?").strip()
        low = clean.lower()

        if low.startswith("what is") or low.startswith("what are"):
            topic = clean[7:].strip()
            return f"{topic} refers to a core method or concept in information systems that operates by processing inputs and producing structured outputs."

        if low.startswith("how to") or low.startswith("how do") or low.startswith("how does"):
            topic = clean[6:].strip()
            return f"To accomplish {topic}, the system initializes the required components, executes the processing steps sequentially, and returns the computed result."

        if low.startswith("why"):
            topic = clean[3:].strip()
            return f"The reason {topic} occurs is due to structural constraints, performance trade-offs, and configuration settings in the underlying environment."

        # Generic factual document template
        return f"This technical document provides detailed guidance and reference material regarding {clean}. It outlines definitions, operational parameters, and error resolution."
