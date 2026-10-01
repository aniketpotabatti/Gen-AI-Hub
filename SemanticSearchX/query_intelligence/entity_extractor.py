"""Entity extraction from user queries.

Extracts:
- Alphanumeric codes / identifiers (e.g., CODE-42, ERR-101)
- Version strings (e.g., v2.3, 1.0.4)
- File paths / extensions (e.g., /path/to/file.py, config.yaml)
- Exact quoted phrases
- Key domain keywords / capitalized terms
"""
import re
from typing import Dict, List, Set


class EntityExtractor:
    """Extracts structured entities, codes, and quoted phrases from queries."""

    CODE_PATTERN = re.compile(r"\b[A-Z]{2,}(?:[_-][0-9A-Z]+)+\b|\b[A-Z]+-\d+\b")
    VERSION_PATTERN = re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\b", re.IGNORECASE)
    PATH_PATTERN = re.compile(r"[/\\][\w.-]+[/\\][\w.-]+|\b\w+\.(?:py|json|yaml|yml|md|txt|cpp|h)\b")
    QUOTED_PATTERN = re.compile(r"[\"']([^\"']+)[\"']")

    def extract(self, query: str) -> Dict[str, List[str]]:
        """Return categorized entities found in the query."""
        if not query:
            return {"codes": [], "versions": [], "paths": [], "quotes": [], "all_entities": []}

        codes = list(dict.fromkeys(self.CODE_PATTERN.findall(query)))
        versions = list(dict.fromkeys(self.VERSION_PATTERN.findall(query)))
        paths = list(dict.fromkeys(self.PATH_PATTERN.findall(query)))
        quotes = list(dict.fromkeys(self.QUOTED_PATTERN.findall(query)))

        all_unique: Set[str] = set()
        for group in (codes, versions, paths, quotes):
            all_unique.update(group)

        return {
            "codes": codes,
            "versions": versions,
            "paths": paths,
            "quotes": quotes,
            "all_entities": sorted(list(all_unique)),
        }
