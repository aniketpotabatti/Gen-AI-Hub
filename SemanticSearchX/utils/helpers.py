import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

def ensure_dir(directory: str):
    Path(directory).mkdir(parents=True, exist_ok=True)

def get_device():
    try:
        import torch
        return "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        return "cpu"

def tokenize(text: str) -> List[str]:
    """Lowercased word tokenizer shared by BM25 and the reranker fallback."""
    if not text:
        return []
    return re.findall(r"\w+", text.lower())

def matches_metadata(meta: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
    """Exact-match metadata filtering; empty/None filters match everything."""
    if not filters:
        return True
    return all(meta.get(key) == value for key, value in filters.items())