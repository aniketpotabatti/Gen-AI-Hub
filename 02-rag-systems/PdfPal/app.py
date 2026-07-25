"""
Author: @aniketpotabatti
Project: PdfPal
Created: 2024-01-15
"""

import os
import shutil
import streamlit as st
from config import PROVIDER_MODELS
from llm import generate_answer
from utils import process_content


def init_session_state():
    """Initializes Streamlit session state variables."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def render_sidebar():
    """Renders sidebar controls, API configuration, and document upload forms."""
    with st.sidebar:
        st.title("PdfPal Controls")

        # API & Model Settings
        with st.expander("⚙️ API & Model Settings", expanded=True):
            selected_provider = st.selectbox(
                "Select Provider",
                options=list(PROVIDER_MODELS.keys()),
                index=0,
                key="provider_select",
            )

            selected_model = st.selectbox(
                "Select Model",
                options=PROVIDER_MODELS[selected_provider],
                index=0,
                key="model_select",
            )

            provider_api_key = st.text_input(
                f"{selected_provider} API Key",
                type="password",
                help=f"Enter your {selected_provider} API key. If blank, the environment variable will be used.",
                key="provider_api_key",
            )

            hf_api_key = st.text_input(
                "Hugging Face API Key (Embeddings)",
                type="password",
                help="Optional HF API key for embeddings. If blank, environment variable will be used.",
                key="hf_api_key",
            )

        st.divider()

        # Document Processing Section
        st.subheader("📁 Documents & Sources")
        uploaded_pdfs = st.file_uploader("Upload PDFs", accept_multiple_files=True, type="pdf")
        url_text = st.text_area("Enter URLs (one per line)")

        if st.button("Process Documents", use_container_width=True):
            urls = [u.strip() for u in url_text.split("\n") if u.strip()]
            if uploaded_pdfs or urls:
                with st.spinner("Extracting content and indexing vector store..."):
                    process_content(uploaded_pdfs, urls, custom_hf_api_key=hf_api_key)
            else:
                st.warning("Please upload PDFs or enter URLs first.")

        st.divider()

        if st.button("Clear Chat & Data", use_container_width=True):
            st.session_state.chat_history = []
            if os.path.exists("faiss_index"):
                shutil.rmtree("faiss_index")
            st.rerun()

    return selected_provider, selected_model, provider_api_key, hf_api_key


def render_header(provider: str, model: str):
    """Renders top fixed application header with provider badge."""
    st.markdown(
        f"""
    <div style="position: fixed; top: 0; left: 0; right: 0; z-index: 100; background-color: #1A1A1A; height: 80px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); display: flex; flex-direction: column; align-items: center; justify-content: center;">
        <h1 style="font-size: 2.2rem; font-weight: 700; margin: 0; line-height: 1; color: white;">PdfPal</h1>
        <p style="font-style: italic; font-size: 0.85rem; color: #0DB2BF; margin: 4px 0 0 0;">powered by {provider} ({model})</p>
    </div>
    <div style="height: 90px;"></div>
    """,
        unsafe_allow_html=True,
    )


def render_chat_history():
    """Renders historical chat messages using Streamlit native components."""
    for role, message in st.session_state.chat_history:
        with st.chat_message(role):
            st.markdown(message)


def handle_chat_input(provider: str, model: str, provider_api_key: str, hf_api_key: str):
    """Handles user query submission, RAG invocation, and UI state updates."""
    if user_input := st.chat_input("Ask about your documents..."):
        # Append User Question
        st.session_state.chat_history.append(("user", user_input))

        # Generate & Append Assistant Answer
        with st.spinner(f"Generating response via {provider}..."):
            response = generate_answer(
                question=user_input,
                provider=provider,
                model_name=model,
                provider_api_key=provider_api_key,
                hf_api_key=hf_api_key,
            )

        if response:
            st.session_state.chat_history.append(("assistant", response))
            st.rerun()


def main():
    """Main application entry point."""
    st.set_page_config(page_title="PdfPal", page_icon="📃", layout="centered")
    init_session_state()

    provider, model, provider_key, hf_key = render_sidebar()
    render_header(provider, model)
    render_chat_history()
    handle_chat_input(provider, model, provider_key, hf_key)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Critical Error: {e}")
        st.stop()
