from typing import List, Union
import fitz
import requests
import streamlit as st
from bs4 import BeautifulSoup
from config import CHUNK_OVERLAP, CHUNK_SIZE

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter


def clean_text(text: str) -> str:
    """Removes empty lines and normalizes whitespace."""
    if not text:
        return ""
    return " ".join([line.strip() for line in text.splitlines() if line.strip()])


def extract_pdf_text(uploaded_files: List) -> str:
    """Extracts and cleans text from a list of uploaded PDF streams."""
    if not uploaded_files:
        return ""

    text_content = []
    progress_bar = st.progress(0)

    for i, pdf_file in enumerate(uploaded_files):
        try:
            with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
                for page in doc:
                    text = page.get_text()
                    if text:
                        text_content.append(text)
        except Exception as e:
            st.error(f"Error reading {getattr(pdf_file, 'name', 'PDF')}: {e}")
        finally:
            pdf_file.seek(0)  # Reset stream pointer for future reads

        progress_bar.progress((i + 1) / len(uploaded_files))

    progress_bar.empty()
    return clean_text("\n".join(text_content))


def extract_url_text(urls: List[str]) -> str:
    """Fetches and cleans text from a list of web page URLs."""
    if not urls:
        return ""

    text_content = []
    headers = {"User-Agent": "PdfPal/2.0 (+https://github.com)"}

    for url in urls:
        if not url.startswith(("http://", "https://")):
            continue

        try:
            resp = requests.get(url, timeout=10, headers=headers)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            raw_page_text = soup.get_text(separator="\n").strip()

            # Limit text length per URL to prevent extreme memory overhead
            if len(raw_page_text) < 50000:
                text_content.append(raw_page_text)
        except Exception as e:
            st.error(f"Failed to fetch content from {url}: {e}")

    return clean_text("\n".join(text_content))


def process_content(uploaded_pdfs: List, urls: List[str], custom_hf_api_key: Union[str, None] = None):
    """Processes input documents & URLs, splits text, and updates vector store."""
    from llm import save_or_update_vector_store

    raw_text = extract_pdf_text(uploaded_pdfs) + "\n" + extract_url_text(urls)

    if not raw_text.strip():
        st.warning("No readable text could be extracted from the provided sources.")
        return

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_text(raw_text)

    if not chunks:
        st.warning("Failed to create text chunks from extracted content.")
        return

    save_or_update_vector_store(chunks, custom_hf_api_key=custom_hf_api_key)
