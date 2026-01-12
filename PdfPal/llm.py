import os
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from embeddings import HuggingFaceAPIEmbeddings
from langchain_community.vectorstores import FAISS

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

def load_vector_store():
    """Loads cached vector store."""
    if not os.path.exists(FAISS_PATH):
        return None
    try:
        embeddings = HuggingFaceAPIEmbeddings(model=EMBEDDING_MODEL, api_key=hf_api_key)
        return FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        st.error(f"Failed to load vector store: {e}")
        return None

def generate_answer(question: str) -> str:
    """Generates answer using RAG."""
    try:
        db = load_vector_store()
        if not db:
            st.warning("No documents processed yet.")
            return None
        
        prompt = PromptTemplate(template=PROMPT_TEMPLATE, input_variables=["context", "question"])
        model = ChatGroq(model=LLM_MODEL, temperature=LLM_TEMPERATURE, api_key=groq_api_key)
        chain = prompt | model | StrOutputParser()
        
        docs = db.similarity_search(question, k=2)
        context = "\n\n".join(doc.page_content for doc in docs) if docs else "No relevant context"
        
        # Limit context size
        if len(context) > 8000:
            context = context[:8000] + "..."
        
        return chain.invoke({"context": context, "question": question})
    except Exception as e:
        st.error(f"Generation error: {e}")
        return None
