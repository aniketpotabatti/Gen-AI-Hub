"""
PdfPal Configuration Module
Centralized constants and model parameters.
"""

# Vector Store & Embedding Settings
FAISS_PATH = "faiss_index"
CHUNK_SIZE = 5000
CHUNK_OVERLAP = 500
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# LLM Execution Defaults
DEFAULT_TEMPERATURE = 0.3

# Provider & Up-to-Date Model Registry
PROVIDER_MODELS = {
    "Groq": [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama-3.2-3b-preview",
        "llama-3.2-1b-preview",
        "deepseek-r1-distill-llama-70b",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
    ],
    "OpenAI": [
        "gpt-4o",
        "gpt-4o-mini",
        "o3-mini",
        "gpt-4-turbo",
    ],
    "Google Gemini": [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ],
    "Anthropic": [
        "claude-3-5-sonnet-latest",
        "claude-3-5-haiku-latest",
        "claude-3-opus-latest",
    ],
    "Mistral AI": [
        "mistral-large-latest",
        "open-mistral-nemo",
        "codestral-latest",
    ],
}

# RAG System Prompt Template
PROMPT_TEMPLATE = """
Answer the question using the provided context. Format your answer in a single readable column.

Context:
{context}

Question:
{question}

Answer:
"""
