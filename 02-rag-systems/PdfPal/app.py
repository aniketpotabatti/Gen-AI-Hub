"""
Author: @aniketpotabatti
Project: PdfPal
Created: 2024-01-15
"""
import os
import shutil
import base64
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
                help=f"Enter your {selected_provider} API key. If blank, environment variable will be used.",
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


def render_header():
    """fixed header"""
    logo_path = os.path.join("assets", "logo_transparent.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join("assets", "logo.png")

    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            encoded_logo = base64.b64encode(f.read()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{encoded_logo}" style="height: 44px; width: 44px; margin-right: 12px; vertical-align: middle; object-fit: contain; filter: drop-shadow(0 2px 8px rgba(13, 178, 191, 0.5));">'
    else:
        logo_html = ""

    st.markdown(
        f"""
        <style>
        /* Pad main block container so chat messages start below fixed header */
        .block-container {{
            padding-top: 6.5rem !important;
            padding-bottom: 5rem !important;
        }}

        /* 100% Stationary Fixed Top Header Bar */
        .pdfpal-stationary-header {{
            position: fixed;
            top: 3.5rem;
            left: 0;
            right: 0;
            height:70px;
            background-color: #1A1A1A !important;
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        }}

        .pdfpal-title {{
            font-size: 2.6rem;
            font-weight: 800;
            color: #FFFFFF;
            margin: ;
            display: inline-block;
            vertical-align: middle;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #FFFFFF 65%, #0DB2BF 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        </style>

        <div class="pdfpal-stationary-header">
            {logo_html}
            <h1 class="pdfpal-title">PdfPal</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_chat_history():
    """Renders historical chat messages using Streamlit native components with custom avatars."""
    for role, message in st.session_state.chat_history:
        avatar = "👤" if role == "user" else "🤖"
        with st.chat_message(role, avatar=avatar):
            st.markdown(message)


def handle_chat_input(provider: str, model: str, provider_api_key: str, hf_api_key: str):
    """Handles user query submission, RAG invocation, and UI state updates."""
    if user_input := st.chat_input("Ask about your documents..."):
        # Append & display User Question instantly
        st.session_state.chat_history.append(("user", user_input))

        # Generate & Append Assistant Answer
        with st.spinner(f"Thinking via {provider}..."):
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
    logo_file = "assets/logo_transparent.png" if os.path.exists("assets/logo_transparent.png") else "assets/logo.png"
    st.set_page_config(page_title="PdfPal", page_icon=logo_file if os.path.exists(logo_file) else "📄", layout="centered")
    init_session_state()

    provider, model, provider_key, hf_key = render_sidebar()
    render_header()
    render_chat_history()
    handle_chat_input(provider, model, provider_key, hf_key)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"Critical Error: {e}")
        st.stop()
