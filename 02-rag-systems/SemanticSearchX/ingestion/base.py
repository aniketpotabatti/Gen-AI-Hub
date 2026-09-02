import os
from typing import List, Dict, Any
from pathlib import Path

class Document:
    def __init__(self, content: str, metadata: Dict[str, Any] = None):
        self.content = content
        self.metadata = metadata or {}
        self.id = None  # Will be set during ingestion

    def __repr__(self):
        return f"Document(id={self.id}, length={len(self.content)})"

def load_txt(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def load_md(file_path: str) -> str:
    return load_txt(file_path)

def load_pdf(file_path: str) -> str:
    try:
        import pypdf
    except ImportError:
        raise ImportError("pypdf is required for PDF files. Install with `pip install pypdf`")
    text = ""
    with open(file_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

def load_document(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext == '.txt':
        return load_txt(file_path)
    elif ext == '.md':
        return load_md(file_path)
    elif ext == '.pdf':
        return load_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")

def ingest_directory(directory_path: str, extensions: List[str] = None) -> List[Document]:
    if extensions is None:
        extensions = ['.txt', '.md', '.pdf']
    documents = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in extensions:
                file_path = os.path.join(root, file)
                try:
                    content = load_document(file_path)
                    doc = Document(content=content, metadata={"source": file_path, "filename": file})
                    documents.append(doc)
                except Exception as e:
                    print(f"Failed to load {file_path}: {e}")
    return documents