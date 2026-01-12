import os
from typing import List

# Fix OpenMP conflicts
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import fitz
import numpy as np
import requests
import streamlit as st
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.embeddings import Embeddings
from langchain_core.prompts import PromptTemplate

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
hf_api_key = os.getenv("HUGGINGFACE_API_KEY")

# Configuration
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "llama-3.1-8b-instant"
LLM_TEMPERATURE = 0.3
FAISS_PATH = "faiss_index"
CHUNK_SIZE = 5000
CHUNK_OVERLAP = 500

# Prompt template for LLM
PROMPT_TEMPLATE = """
Answer the question using the provided context. Format your answer in a single readable column.

Context:
{context}

Question:
{question}

Answer:
"""

class HuggingFaceAPIEmbeddings(Embeddings):
    """Custom embeddings wrapper with retry logic"""
    
    def __init__(self, model: str, api_key: str):
        self.model = model
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                self._client = InferenceClient(model=self.model, token=self.api_key)
                return self._client
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Hugging Face API: {e}")
        return self._client

    def _flatten_to_floats(self, embedding) -> List[float]:
        """Convert embedding to flat list of floats"""
        try:
            # Handle numpy arrays explicitly
            if isinstance(embedding, np.ndarray):
                return [float(x) for x in embedding.flatten()]
            
            # Handle list of lists
            if isinstance(embedding, list):
                # Check if it's a nested list
                if len(embedding) > 0 and isinstance(embedding[0], list):
                    return [float(value) for chunk in embedding for value in chunk]
                # Single list
                return [float(x) for x in embedding]
            
            # Handle single value
            return [float(embedding)]
        except (ValueError, TypeError) as e:
            st.error(f"Error flattening embedding: {e}")
            return []

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        vectors = []
        for text in texts:
            try:
                embedding = self.client.feature_extraction(text)
                vectors.append(self._flatten_to_floats(embedding))
            except Exception as e:
                st.error(f"Embedding failed: {e}")
                vectors.append([])
        return vectors

    def embed_query(self, text: str) -> List[float]:
        try:
            embedding = self.client.feature_extraction(text)
            return self._flatten_to_floats(embedding)
        except Exception as e:
            st.error(f"Embedding failed: {e}")
            return []
