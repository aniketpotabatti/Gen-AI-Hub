"""
Document processor — handles PDF and CSV loading + text chunking.
One file replaces the old 6-file ingestion/processing system.
"""

import hashlib
from pathlib import Path
from dataclasses import dataclass, field

import pandas as pd
from pypdf import PdfReader


@dataclass
class Document:
    """A processed document with its text and metadata."""

    content: str
    metadata: dict = field(default_factory=dict)
    doc_id: str = ""

    def __post_init__(self):
        if not self.doc_id:
            self.doc_id = hashlib.md5(self.content[:500].encode()).hexdigest()


# ── Loaders ──────────────────────────────────────────────────────────


def load_pdf(file_path: str | Path) -> Document:
    """Extract all text from a PDF file."""
    path = Path(file_path)
    reader = PdfReader(str(path))

    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)

    full_text = "\n\n".join(pages)
    return Document(
        content=full_text,
        metadata={
            "source": path.name,
            "source_type": "pdf",
            "num_pages": len(reader.pages),
            "file_path": str(path.absolute()),
        },
    )


def load_pdf_from_bytes(file_bytes: bytes, filename: str) -> Document:
    """Extract text from PDF bytes (for Streamlit file uploads)."""
    import io

    reader = PdfReader(io.BytesIO(file_bytes))

    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)

    full_text = "\n\n".join(pages)
    return Document(
        content=full_text,
        metadata={
            "source": filename,
            "source_type": "pdf",
            "num_pages": len(reader.pages),
        },
    )


def load_csv(file_path: str | Path) -> pd.DataFrame:
    """Load a CSV file into a pandas DataFrame."""
    last_error: Exception | None = None
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(file_path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        except pd.errors.EmptyDataError:
            return pd.DataFrame()
    if last_error:
        raise last_error
    return pd.read_csv(file_path)


def load_csv_from_bytes(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Load CSV from bytes (for Streamlit file uploads)."""
    import io

    last_error: Exception | None = None
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(file_bytes), encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        except pd.errors.EmptyDataError:
            return pd.DataFrame()
    if last_error:
        raise last_error
    return pd.read_csv(io.BytesIO(file_bytes))


# ── Chunker ──────────────────────────────────────────────────────────


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks.

    Uses paragraph boundaries when possible, falls back to
    sentence boundaries, then hard character splits.
    """
    if not text or not text.strip():
        return []

    # Split by paragraphs first
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # If adding this paragraph exceeds chunk_size, save current and start new
        if len(current_chunk) + len(para) + 2 > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Keep overlap from end of current chunk
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + "\n\n" + para
            else:
                current_chunk = para
        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Handle case where a single paragraph is longer than chunk_size
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= chunk_size:
            final_chunks.append(chunk)
        else:
            # Hard split at chunk_size with overlap
            for i in range(0, len(chunk), chunk_size - overlap):
                sub = chunk[i : i + chunk_size]
                if sub.strip():
                    final_chunks.append(sub.strip())

    return final_chunks


def document_to_chunks(doc: Document, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """
    Convert a Document into a list of chunk dicts ready for vector storage.

    Returns:
        List of dicts with 'text', 'metadata', and 'id' keys.
    """
    text_chunks = chunk_text(doc.content, chunk_size, overlap)
    result = []

    for i, chunk in enumerate(text_chunks):
        chunk_meta = {**doc.metadata, "chunk_index": i, "total_chunks": len(text_chunks)}
        chunk_id = f"{doc.doc_id}_chunk_{i}"
        result.append({"id": chunk_id, "text": chunk, "metadata": chunk_meta})

    return result
