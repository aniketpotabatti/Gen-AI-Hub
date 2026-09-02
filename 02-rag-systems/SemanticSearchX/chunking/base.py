from typing import List

class BaseChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[str]:
        raise NotImplementedError

class RecursiveCharacterChunker(BaseChunker):
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50, separators: List[str] = None):
        super().__init__(chunk_size, chunk_overlap)
        self.separators = separators or ["\n\n", "\n", " ", ""]

    def chunk_text(self, text: str) -> List[str]:
        # Simple implementation: split by separators recursively
        final_chunks = []
        # We'll use a simple approach: split by paragraphs then split long paragraphs
        # For simplicity, we use a naive sliding window over characters.
        # In production, use langchain text splitters or similar.
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            final_chunks.append(chunk)
            start = end - self.chunk_overlap
        return final_chunks

def chunk_document(doc: str, chunker: BaseChunker) -> List[str]:
    return chunker.chunk_text(doc)