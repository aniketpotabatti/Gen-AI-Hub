import os
import shutil
import base64
import streamlit as st
from pathlib import Path
from config import PROVIDER_MODELS
from llm import generate_answer
from utils import process_content

LOGO_PATH = Path(__file__).parent / "assets" / "pdfpal logo.png"

st.set_page_config(
    page_title="Pdfpal - Chat with PDFs and Files",
    page_icon=str(LOGO_PATH),
    layout="wide"
)

def init_session_state():
    """Initializes Streamlit session state variables."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def render_sidebar():
    """Renders sidebar controls, API configuration, and document upload forms."""
    with st.sidebar:
        st.title("Controls")

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
    logo_path = os.path.join("assets", "pdfpal logo.png")

    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            encoded_logo = base64.b64encode(f.read()).decode("utf-8")
        logo_html = f'<img src="data:image/png;base64,{encoded_logo}" style="height: 38px; width: 38px; margin-right: 12px; vertical-align: middle; object-fit: contain; filter: drop-shadow(0 2px 8px rgba(13, 178, 191, 0.5));">'
    else:
        logo_html = ""

logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
st.markdown(
        f"""
        <style>
        /* Streamlit native header bar styling */
        header[data-testid="stHeader"] {{
            background-color: transparent !important;
            z-index: 10000 !important;
            height: 3.5rem !important;
        }}
        header[data-testid="stHeader"]::before {{
            content: "";
            position: absolute;
            left: 41%;
            top: 38%;
            transform: translate(-50%, -50%);
            width: 500px;
            height: 100%;
            background: url("data:image/png;base64,{logo_b64}") center / contain no-repeat;
            filter:drop-shadow(0 0 14px rgb(197, 236, 198, 0.75));
            z-index: 1000;
            pointer-events: none;
        }}
        </style>
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
    st.set_page_config(page_title="PdfPal", page_icon="assets/pdfpal logo.png", layout="centered")
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
