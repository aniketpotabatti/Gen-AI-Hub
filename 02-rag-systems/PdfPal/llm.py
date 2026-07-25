import os
from typing import List, Union
import streamlit as st
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from config import (
    DEFAULT_TEMPERATURE,
    EMBEDDING_MODEL,
    FAISS_PATH,
    PROMPT_TEMPLATE,
    PROVIDER_MODELS,
)
from embeddings import HuggingFaceAPIEmbeddings

load_dotenv()


def _get_api_key(user_key: Union[str, None], env_vars: List[str], provider_name: str) -> str:
    """Helper to resolve API key from user input or environment variables."""
    if user_key and user_key.strip():
        return user_key.strip()
    for var in env_vars:
        val = os.getenv(var)
        if val and val.strip():
            return val.strip()
    raise ValueError(
        f"{provider_name} API Key is missing. Please enter it in the sidebar or set {env_vars[0]} in your environment."
    )


def _create_groq_llm(model_name: str, temperature: float, key: str):
    from langchain_groq import ChatGroq
    return ChatGroq(model=model_name, temperature=temperature, api_key=key)


def _create_openai_llm(model_name: str, temperature: float, key: str):
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model=model_name, temperature=temperature, api_key=key)


def _create_gemini_llm(model_name: str, temperature: float, key: str):
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(model=model_name, temperature=temperature, google_api_key=key)


def _create_anthropic_llm(model_name: str, temperature: float, key: str):
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(model=model_name, temperature=temperature, api_key=key)


def _create_mistral_llm(model_name: str, temperature: float, key: str):
    from langchain_mistralai import ChatMistralAI
    return ChatMistralAI(model=model_name, temperature=temperature, api_key=key)


# Provider Builder Dispatcher Strategy Map
PROVIDER_BUILDERS = {
    "Groq": (_create_groq_llm, ["GROQ_API_KEY"]),
    "OpenAI": (_create_openai_llm, ["OPENAI_API_KEY"]),
    "Google Gemini": (_create_gemini_llm, ["GEMINI_API_KEY", "GOOGLE_API_KEY"]),
    "Anthropic": (_create_anthropic_llm, ["ANTHROPIC_API_KEY"]),
    "Mistral AI": (_create_mistral_llm, ["MISTRAL_API_KEY"]),
}


def get_llm(provider: str, model_name: str, api_key: Union[str, None] = None, temperature: float = DEFAULT_TEMPERATURE):
    """Factory function to instantiate LLM based on selected provider strategy."""
    if provider not in PROVIDER_BUILDERS:
        raise ValueError(f"Unsupported LLM Provider: '{provider}'")

    builder_func, env_vars = PROVIDER_BUILDERS[provider]
    effective_key = _get_api_key(api_key, env_vars, provider)
    return builder_func(model_name, temperature, effective_key)


def _get_embeddings_instance(custom_hf_api_key: Union[str, None] = None) -> HuggingFaceAPIEmbeddings:
    """Helper to instantiate HuggingFaceAPIEmbeddings with resolved API key."""
    key = custom_hf_api_key.strip() if (custom_hf_api_key and custom_hf_api_key.strip()) else os.getenv("HUGGINGFACE_API_KEY")
    return HuggingFaceAPIEmbeddings(model=EMBEDDING_MODEL, api_key=key)


def load_vector_store(custom_hf_api_key: Union[str, None] = None) -> Union[FAISS, None]:
    """Loads cached FAISS vector store if present."""
    if not os.path.exists(FAISS_PATH):
        return None
    try:
        embeddings = _get_embeddings_instance(custom_hf_api_key)
        return FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
    except Exception as e:
        st.error(f"Failed to load vector store: {e}")
        return None


def save_or_update_vector_store(chunks: List[str], custom_hf_api_key: Union[str, None] = None):
    """Creates a new FAISS vector store or appends new text chunks to existing index."""
    try:
        embeddings = _get_embeddings_instance(custom_hf_api_key)
        os.makedirs(FAISS_PATH, exist_ok=True)
        index_file = os.path.join(FAISS_PATH, "index.faiss")

        if os.path.exists(index_file) and os.path.getsize(index_file) > 0:
            db = FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)
            db.add_texts(chunks)
            db.save_local(FAISS_PATH)
        else:
            db = FAISS.from_texts(chunks, embedding=embeddings)
            db.save_local(FAISS_PATH)

        st.success("Vector store index saved successfully!")
    except Exception as e:
        st.error(f"Failed to save vector store: {e}")


def generate_answer(
    question: str,
    provider: str = "Groq",
    model_name: str = "llama-3.3-70b-versatile",
    provider_api_key: Union[str, None] = None,
    hf_api_key: Union[str, None] = None,
) -> Union[str, None]:
    """Executes RAG pipeline to generate answer from loaded vector store."""
    try:
        db = load_vector_store(custom_hf_api_key=hf_api_key)
        if not db:
            st.warning("No processed documents found. Please upload a PDF or enter a URL first.")
            return None

        prompt = PromptTemplate(template=PROMPT_TEMPLATE, input_variables=["context", "question"])
        model = get_llm(provider=provider, model_name=model_name, api_key=provider_api_key)
        chain = prompt | model | StrOutputParser()

        docs = db.similarity_search(question, k=2)
        context = "\n\n".join(doc.page_content for doc in docs) if docs else "No relevant context"

        # Truncate context to prevent context window overflow
        if len(context) > 8000:
            context = context[:8000] + "..."

        return chain.invoke({"context": context, "question": question})
    except Exception as e:
        st.error(f"Generation error: {e}")
        return None
