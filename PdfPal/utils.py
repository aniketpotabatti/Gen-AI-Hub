import os
import fitz
import requests
import streamlit as st
from bs4 import BeautifulSoup
from langchain.text_splitter import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from embeddings import HuggingFaceAPIEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()
hf_api_key = os.getenv("HUGGINGFACE_API_KEY")

# Configuration
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
FAISS_PATH = "faiss_index"
CHUNK_SIZE = 5000
CHUNK_OVERLAP = 500

# --- Helper Functions ---B
def clean_text(text: str) -> str:
    """Removes empty lines and normalizes whitespace."""
    if not text:
        return ""
    return " ".join([line.strip() for line in text.splitlines() if line.strip()])

def extract_pdf_text(uploaded_files) -> str:
    """Extracts and cleans text from uploaded PDF files."""
    text_content = ""
    if not uploaded_files:
        return text_content
        
    progress_bar = st.progress(0)
    for i, pdf_file in enumerate(uploaded_files):
        try:
            # Read PDF stream
            with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
                for page in doc:
                    text_content += page.get_text() + "\n"
        except Exception as e:
            st.error(f"Error reading {pdf_file.name}: {e}")
        finally:
            pdf_file.seek(0) # Reset pointer
        progress_bar.progress((i + 1) / len(uploaded_files))
    
    progress_bar.empty()
    return clean_text(text_content)

def extract_url_text(urls) -> str:
    """Fetches and cleans text from a list of URLs."""
    text_content = ""
    headers = {'User-Agent': 'PdfPal/1.0'}
    
    for url in urls:
        if not url.startswith(('http://', 'https://')):
            continue
            
        try:
            resp = requests.get(url, timeout=10, headers=headers)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            # Limit text length to avoid overloading
            if len(soup.get_text()) < 50000:
                text_content += soup.get_text(separator="\n").strip() + "\n"
        except Exception as e:
            st.error(f"Failed to fetch {url}: {e}")
    
    return clean_text(text_content)

def process_content(uploaded_pdfs, urls):
    """Processes PDFs and URLs, creates vector store."""
    raw_text = extract_pdf_text(uploaded_pdfs) + extract_url_text(urls)
    
    if not raw_text.strip():
        st.warning("No content extracted.")
        return
    
    # Split text
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = splitter.split_text(raw_text)
    
    if not chunks:
        st.warning("No chunks created.")
        return
    
    # Create vector store
    try:
        embeddings = HuggingFaceAPIEmbeddings(model=EMBEDDING_MODEL, api_key=hf_api_key)
        os.makedirs(FAISS_PATH, exist_ok=True)
        
        index_file = os.path.join(FAISS_PATH, "index.faiss")
        if os.path.exists(index_file) and os.path.getsize(index_file) > 0:
            db = FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
            db.add_texts(chunks)
            db.save_local(FAISS_PATH)
        else:
            db = FAISS.from_texts(chunks, embedding=embeddings)
            db.save_local(FAISS_PATH)
    except Exception as e:
        st.error(f"Failed to create vector store: {e}")
