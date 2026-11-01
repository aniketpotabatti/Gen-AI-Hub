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
            identity = self.metadata.get("source", "") + chr(0) + self.content
            self.doc_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()


# ── Loaders ──────────────────────────────────────────────────────────


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Trim headers and make blank or repeated names safe to analyze."""
    seen: dict[str, int] = {}
    columns = []
    for index, raw_name in enumerate(df.columns, start=1):
        name = str(raw_name).strip() or f"column_{index}"
        count = seen.get(name, 0)
        seen[name] = count + 1
        columns.append(name if count == 0 else f"{name}_{count + 1}")
    df.columns = columns
    return df


def _read_csv(source_factory) -> pd.DataFrame:
    """Read path or byte input with one common encoding fallback."""
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            return _normalize_columns(pd.read_csv(source_factory(), encoding=encoding, low_memory=False))
        except UnicodeDecodeError as exc:
            last_error = exc
        except pd.errors.EmptyDataError:
            return pd.DataFrame()
    if last_error:
        raise last_error
    return _normalize_columns(pd.read_csv(source_factory(), low_memory=False))


def load_csv(file_path: str | Path) -> pd.DataFrame:
    """Load a CSV file into a pandas DataFrame."""
    path = Path(file_path)
    return _read_csv(lambda: path)


def load_csv_from_bytes(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Load CSV bytes into a pandas DataFrame."""
    import io
    return _read_csv(lambda: io.BytesIO(file_bytes))


def _extract_pdf(reader, filename: str) -> Document:
    """Extract readable text and metadata from a PDF reader."""
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
    return Document(
        content="\n\n".join(pages),
        metadata={"source": filename, "source_type": "pdf", "num_pages": len(reader.pages)},
    )


def load_pdf(file_path: str | Path) -> Document:
    """Extract all text from a PDF file."""
    path = Path(file_path)
    document = _extract_pdf(PdfReader(str(path)), path.name)
    document.metadata["file_path"] = str(path.absolute())
    return document


def load_pdf_from_bytes(file_bytes: bytes, filename: str) -> Document:
    """Extract text from PDF bytes (for Streamlit file uploads)."""
    import io
    return _extract_pdf(PdfReader(io.BytesIO(file_bytes)), filename)


# ── Chunker ──────────────────────────────────────────────────────────


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """
    Split text into overlapping chunks.

    Uses paragraph boundaries when possible, falls back to
    sentence boundaries, then hard character splits.
    """
    if not text or not text.strip():
        return []
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")
    overlap = max(0, min(overlap, chunk_size - 1))

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
