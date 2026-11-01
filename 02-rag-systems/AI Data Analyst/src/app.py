"""
AI Data Analyst — Streamlit Dashboard
Main entry point: streamlit run src/app.py
"""

import hashlib
import sys
from pathlib import Path

# Ensure project root is in sys.path (needed for Streamlit)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd

from src.utils.config import settings
from src.engine.ai_analyst import AIAnalyst
from src.engine.vector_store import VectorStore
from src.engine.doc_processor import (
    load_pdf_from_bytes,
    load_csv_from_bytes,
    document_to_chunks,
)
from src.viz.chart_generator import generate_chart, auto_chart


# ── Page Config ──────────────────────────────────────────────────

st.set_page_config(
    page_title="AI Data Analyst",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session State Init ───────────────────────────────────────────

def init_session():
    """Initialize all session state variables."""
    defaults = {
        "chat_history": [],
        "df": None,
        "df_name": None,
        "datasets": {},
        "combined_df": None,
        "active_dataset_id": None,
        "upload_version": 0,
        "uploaded_docs": [],
        "processed_pdf_hashes": set(),
        "insights": [],
        "api_key": None,
        "pending_prompt": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Migrate data already loaded in a single-file session.
    if st.session_state.df is not None and st.session_state.df_name and not st.session_state.datasets:
        legacy_id = "legacy:" + st.session_state.df_name
        st.session_state.datasets[legacy_id] = {
            "name": st.session_state.df_name, "frame": st.session_state.df
        }
        st.session_state.active_dataset_id = legacy_id


init_session()

# Check for queued chip actions
queued_prompt = None
if st.session_state.pending_prompt:
    queued_prompt = st.session_state.pending_prompt
    st.session_state.pending_prompt = None


# ── Custom CSS ────────────────────────────────────────────────────

st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --primary:       #2DD4BF;
        --primary-dim:   rgba(45, 212, 191, 0.15);
        --primary-glow:  rgba(45, 212, 191, 0.22);
        --bg:            #07111F;
        --sidebar-bg:    #091524;
        --surface:       #0E1B2E;
        --surface2:      #122438;
        --border:        #1E3450;
        --border-light:  #2a4a6a;
        --text:          #E8EEF7;
        --text-muted:    #7D96B0;
        --text-dim:      #4D6480;
    }

    /* ── Global ── */
    .stApp {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
        background: linear-gradient(160deg, #0b1e35 0%, #07111F 45%, #050e1a 100%) !important;
        color: var(--text) !important;
    }

    header[data-testid="stHeader"] {
        background: transparent !important;
    }

    section[data-testid="stMain"] .block-container {
        max-width: 980px;
        padding-top: 2.5rem;
        padding-bottom: 6rem;
        padding-left: 2rem;
        padding-right: 2rem;
        transition: max-width 0.3s ease, padding-left 0.3s ease, padding-right 0.3s ease;
    }

    /* Main content spreads full-width when sidebar is closed */
    section[data-testid="stSidebar"][aria-expanded="false"] ~ section[data-testid="stMain"] .block-container,
    section[data-testid="stSidebar"][data-collapsed="true"] ~ section[data-testid="stMain"] .block-container {
        max-width: 100% !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        width: 270px !important;
        min-width: 270px !important;
        background: var(--sidebar-bg) !important;
        border-right: 1px solid var(--border) !important;
        transition: width 0.3s ease, min-width 0.3s ease, border-right 0.3s ease !important;
    }

    /* Sidebar collapsed — shrink to zero width and remove border */
    section[data-testid="stSidebar"][aria-expanded="false"],
    section[data-testid="stSidebar"][data-collapsed="true"] {
        width: 0 !important;
        min-width: 0 !important;
        border-right: none !important;
    }

    /* ── Sidebar Toggle Arrow ── */
    /* Cleanly position the collapse/expand button at the left edge */
    button[data-testid="stSidebarCollapseButton"] {
        position: fixed !important;
        top: 1rem !important;
        left: 0.75rem !important;
        z-index: 1000 !important;
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text) !important;
        width: 2.5rem !important;
        height: 2.5rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 0.875rem !important;
        font-weight: 700 !important;
        line-height: 1 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35) !important;
    }

    button[data-testid="stSidebarCollapseButton"]:hover {
        background: var(--primary) !important;
        color: #07111F !important;
        border-color: var(--primary) !important;
        transform: translateY(-1px) !important;
    }

    section[data-testid="stSidebar"] > div {
        padding: 1.5rem 1rem !important;
    }

    /* + New Chat button */
    .new-chat-btn-container button {
        background: var(--primary) !important;
        color: #07111F !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 9999px !important;
        box-shadow: 0 2px 12px rgba(45, 212, 191, 0.3) !important;
        transition: all 0.2s ease !important;
        margin-bottom: 1.25rem !important;
        letter-spacing: 0.01em !important;
    }

    .new-chat-btn-container button:hover {
        filter: brightness(1.1) !important;
        box-shadow: 0 4px 18px rgba(45, 212, 191, 0.45) !important;
        transform: translateY(-1px) !important;
    }

    /* Section labels */
    .sidebar-section-header {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        color: var(--text-dim);
        text-transform: uppercase;
        margin: 1.25rem 0 0.4rem 0;
    }

    .sidebar-history-empty {
        font-size: 0.82rem;
        color: var(--text-dim);
        padding: 0.15rem 0 0.75rem 0;
    }

    /* Sidebar text inputs */
    .sidebar-section-title{
        font-size: 1.2rem;
        font-weight: 800;
        letter-spacing: 0.1em;
        color: var(--text-light);
        text-transform: uppercase;
        text-align: center;
        margin: 0 0 0.5rem 0;
    }

    section[data-testid="stSidebar"] .stTextInput input {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        color: var(--text) !important;
        font-size: 0.88rem !important;
    }

    section[data-testid="stSidebar"] .stTextInput input:focus {
        border-color: #ffffff !important;
        box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.25) !important;
    }

    /* Sidebar action buttons */
    section[data-testid="stSidebar"] .stButton > button {
        background: transparent !important;
        border: 1px solid var(--border) !important;
        color: var(--text-muted) !important;
        border-radius: 8px !important;
        font-size: 0.84rem !important;
        transition: all 0.2s !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        border-color: var(--primary) !important;
        color: var(--primary) !important;
        background: var(--primary-dim) !important;
    }

    /* ── Hero section ── */
    .hero-section {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 1.5rem 0 1rem 0;
    }

    /* ── Chips ── */
    .chip-btn button {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-muted) !important;
        font-size: 0.84rem !important;
        font-weight: 500 !important;
        border-radius: 9999px !important;
        padding: 0.45rem 1rem !important;
        transition: all 0.18s ease !important;
    }

    .chip-btn button:hover {
        background: var(--primary-dim) !important;
        border-color: var(--primary) !important;
        color: var(--primary) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Chat messages ── */
    div[data-testid="stChatMessage"] {
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 14px !important;
        padding: 1rem 1.25rem !important;
        margin-bottom: 0.85rem !important;
    }

    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
        background: var(--surface2) !important;
        border-color: var(--border-light) !important;
    }

    /* ── Chat Input Pill ──
       Streamlit renders: stBottom > div > form > [stChatInput textarea] + [button]
       The <form> is the true flex container for both elements.
    ── */
    div[data-testid="stBottom"] {
        background: transparent !important;
    }

    div[data-testid="stBottom"] > div {
        background: linear-gradient(to top, #161a1e 70%, transparent) !important;
        padding: 1rem 0 1.5rem 0 !important;
    }

    /* The form wraps BOTH the textarea div AND the send button */
    div[data-testid="stBottom"] form {
        display: flex !important;
        align-items: center !important;
        background: #14253B !important;
        border: 1.5px solid var(--border) !important;
        border-radius: 9999px !important;
        overflow: hidden !important;
        padding: 5px 8px 5px 20px !important;
        gap: 8px !important;
        box-shadow: 0 4px 28px rgba(0, 0, 0, 0.4), 0 0 0 0 var(--primary-glow) !important;
        transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    }

    div[data-testid="stBottom"] form:focus-within {
        border-color: var(--primary) !important;
        box-shadow: 0 4px 28px rgba(0, 0, 0, 0.4), 0 0 0 3px var(--primary-dim) !important;
    }

    /* Strip stChatInput's own box */
    div[data-testid="stChatInput"] {
        flex: 1 !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }

    div[data-testid="stChatInput"] > div {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        border-radius: 0 !important;
        padding: 0 !important;
    }

    div[data-testid="stChatInput"] textarea {
        background: transparent !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        color: var(--text) !important;
        padding: 0.55rem 0 !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 0.95rem !important;
        resize: none !important;
        line-height: 1.5 !important;
    }

    div[data-testid="stChatInput"] textarea::placeholder {
        color: var(--text-dim) !important;
    }

    /* Send button inside the pill */
    div[data-testid="stBottom"] form button {
        flex-shrink: 0 !important;
        width: 36px !important;
        height: 36px !important;
        min-width: 36px !important;
        min-height: 36px !important;
        border-radius: 50% !important;
        background: var(--primary) !important;
        border: none !important;
        color: #07111F !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 2px 8px rgba(45, 212, 191, 0.35) !important;
        transition: all 0.18s ease !important;
        cursor: pointer !important;
    }

    div[data-testid="stBottom"] form button:hover {
        background: #38e8d0 !important;
        box-shadow: 0 4px 14px rgba(45, 212, 191, 0.5) !important;
        transform: scale(1.05) !important;
    }

    /* ── Stat cards ── */
    .stat-card-clean {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 12px 10px;
        text-align: center;
        margin-bottom: 0.5rem;
    }

    .stat-card-clean .val {
        font-size: 1.4rem;
        font-weight: 700;
        color: var(--primary);
    }

    .stat-card-clean .lbl {
        font-size: 0.7rem;
        color: var(--text-muted);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 2px;
    }

    /* ── Source badges ── */
    .source-badge-pill {
        display: inline-block;
        background: var(--primary-dim);
        border: 1px solid rgba(45, 212, 191, 0.3);
        border-radius: 9999px;
        padding: 3px 10px;
        font-size: 0.75rem;
        color: var(--primary);
        margin: 2px 4px 2px 0;
    }

    /* Product UI refinement */
    :root {
        --primary: #43D6C4;
        --primary-dim: rgba(67, 214, 196, 0.12);
        --primary-glow: rgba(67, 214, 196, 0.18);
        --bg: #081321;
        --sidebar-bg: #0A1727;
        --surface: #101F32;
        --surface2: #152840;
        --border: #263C55;
        --border-light: #36516D;
        --text: #F1F5FA;
        --text-muted: #A7B8CB;
        --text-dim: #8296AD;
    }

    .stApp {
        background: radial-gradient(ellipse at 50% 0%, #12243A 0%, #081321 58%, #07111D 100%) !important;
    }

    section[data-testid="stMain"] .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 7rem;
        padding-left: clamp(1rem, 3vw, 2.5rem);
        padding-right: clamp(1rem, 3vw, 2.5rem);
    }

    section[data-testid="stSidebar"] {
        width: 292px !important;
        min-width: 292px !important;
        background: linear-gradient(180deg, #0C1A2B 0%, #091523 100%) !important;
        border-right-color: #20364F !important;
    }

    section[data-testid="stSidebar"] > div {
        padding: 1.35rem 1.1rem 1.5rem !important;
    }

    .sidebar-section-title {
        color: #F3F7FC;
        font-size: 1rem;
        letter-spacing: .045em;
        line-height: 1.35;
        text-align: left;
        padding: .2rem 0 .35rem;
        margin-bottom: .7rem;
    }

    .sidebar-section-header {
        color: #91A8C0;
        font-size: .67rem;
        letter-spacing: .12em;
        margin: 1.35rem 0 .55rem;
    }

    .sidebar-history-empty,
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #A0B2C6 !important;
        line-height: 1.5;
    }

    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background: #102137 !important;
        border-color: #2A415B !important;
        border-radius: 12px !important;
    }

    section[data-testid="stSidebar"] .stTextInput input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px var(--primary-dim) !important;
    }

    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        padding: .8rem !important;
        transition: border-color .18s ease, background .18s ease;
    }

    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #4A6A89 !important;
        background: #132740 !important;
    }

    .new-chat-btn-container button {
        border-radius: 10px !important;
        min-height: 2.65rem;
        box-shadow: 0 5px 18px rgba(45, 212, 191, .16) !important;
    }

    section[data-testid="stSidebar"] .stButton > button {
        min-height: 2.45rem;
        border-color: #2A415B !important;
        color: #C1D0DF !important;
        background: rgba(16, 31, 50, .55) !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        color: #72E6D6 !important;
        border-color: #43AFA6 !important;
        background: rgba(67, 214, 196, .09) !important;
    }

    .stat-card-clean {
        min-height: 76px;
        padding: 12px 8px;
        background: linear-gradient(145deg, #12243A, #0E1D30);
        border-color: #2A415B;
        border-radius: 12px;
    }

    .stat-card-clean .val {
        font-size: 1.3rem;
        line-height: 1.25;
    }

    .stat-card-clean .lbl {
        color: #A2B4C8;
        letter-spacing: .08em;
    }

    .source-badge-pill {
        display: inline-flex;
        align-items: center;
        max-width: 100%;
        background: rgba(67, 214, 196, .09);
        border-color: rgba(67, 214, 196, .24);
        color: #8BE7DC;
        overflow-wrap: anywhere;
    }

    /* Keep the welcome view compact and guide attention toward the next action. */
    section[data-testid="stMain"] .block-container:has(.chip-btn) [data-testid="stImage"] {
        max-width: 460px;
        margin: 0 auto;
    }

    section[data-testid="stMain"] .block-container:has(.chip-btn) [data-testid="stImage"] img {
        max-height: 310px;
        object-fit: contain;
    }

    .chip-btn button {
        min-height: 3.1rem;
        white-space: normal;
        border-radius: 12px !important;
        border-color: #2B425D !important;
        background: linear-gradient(145deg, #12243A, #0E1C2E) !important;
        color: #DDE7F1 !important;
        box-shadow: 0 5px 18px rgba(0, 0, 0, .12);
    }

    .chip-btn button:hover {
        color: #8BE7DC !important;
        border-color: #3B8B88 !important;
        background: linear-gradient(145deg, #142D42, #10263A) !important;
    }

    div[data-testid="stExpander"] {
        background: rgba(16, 31, 50, .68);
        border: 1px solid #263C55;
        border-radius: 14px;
        overflow: hidden;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid #263C55;
        border-radius: 12px;
        overflow: hidden;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 16px !important;
        padding: 1rem 1.2rem !important;
        border-color: #263C55 !important;
        background: rgba(16, 31, 50, .9) !important;
    }

    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
        background: rgba(21, 40, 64, .88) !important;
        border-color: #36516D !important;
    }

    div[data-testid="stBottom"] > div {
        background: linear-gradient(to top, #081321 68%, transparent) !important;
    }

    div[data-testid="stBottom"] form {
        background: #12243A !important;
        border-color: #2D4561 !important;
        box-shadow: 0 10px 32px rgba(0, 0, 0, .28) !important;
    }

    div[data-testid="stBottom"] form:focus-within {
        border-color: var(--primary) !important;
        box-shadow: 0 10px 32px rgba(0, 0, 0, .28), 0 0 0 3px var(--primary-dim) !important;
    }

    @media (max-width: 760px) {
        section[data-testid="stMain"] .block-container {
            padding-top: 1.25rem;
            padding-bottom: 6rem;
        }

        section[data-testid="stSidebar"] {
            width: min(88vw, 310px) !important;
            min-width: min(88vw, 310px) !important;
        }

        section[data-testid="stMain"] .block-container:has(.chip-btn) [data-testid="stImage"] img {
            max-height: 230px;
        }

        div[data-testid="stChatMessage"] {
            padding: .85rem !important;
        }
    }

    /* Follow-up polish: distinct composer dock and fully rounded controls. */
    div[data-testid="stBottom"] > div {
        background: linear-gradient(to top, rgba(164, 176, 190, .15) 0%, rgba(164, 176, 190, .12) 72%, transparent 100%) !important;
        border-top: 1px solid rgba(190, 202, 216, .12);
        backdrop-filter: blur(10px);
        padding-top: 1.15rem !important;
        padding-bottom: 1.4rem !important;
    }

    div[data-testid="stBottom"] form {
        outline: .5rem solid rgba(255, 255, 255, .96) !important;
        outline-offset: 0;
        border-radius: 9999px !important;
    }

    div[data-testid="stBottom"] form:focus-within {
        outline-color: #FFFFFF !important;
    }

    div[data-testid="stButton"] button,
    section[data-testid="stSidebar"] .stButton > button,
    .new-chat-btn-container button,
    .chip-btn button {
        border-radius: 9999px !important;
    }

    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        border-radius: 18px !important;
    }

    @media (max-width: 760px) {
        div[data-testid="stBottom"] form {
            outline-width: .35rem !important;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)



# ── Lazy-loaded singletons ───────────────────────────────────────
@st.cache_resource
def get_vector_store(api_key):
    return VectorStore(api_key=api_key)


@st.cache_resource
def get_analyst(api_key):
    return AIAnalyst(api_key=api_key, vector_store=get_vector_store(api_key))


# ── Left Sidebar (App Controls & Native Functionalities) ─────────

with st.sidebar:

    st.markdown('<div class="sidebar-section-title">🔎 AI Data Analyst</div>', unsafe_allow_html=True)

    # + New Chat Button
    st.markdown('<div class="new-chat-btn-container">', unsafe_allow_html=True)
    if st.button("+ New Chat", use_container_width=True, key="new_chat_btn"):
        st.session_state.chat_history = []
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # API Key Configuration
    st.markdown('<div class="sidebar-section-header">API KEY</div>', unsafe_allow_html=True)
    api_key_input = st.text_input(
        "Gemini API key",
        type="password",
        placeholder="AIza...",
        help="Paste your Gemini API key here.",
        key="api_key_input",
        label_visibility="collapsed",
    )
    if api_key_input:
        st.session_state.api_key = api_key_input.strip()
    elif "api_key" in st.session_state:
        del st.session_state.api_key

    api_key = st.session_state.get("api_key", "")
    if api_key:
        st.caption("✅ API key active")
    else:
        st.caption("⚠️ API key not configured")

    # File Upload Section
    st.markdown('<div class="sidebar-section-header">UPLOAD DATA</div>', unsafe_allow_html=True)
    uploaded_files = st.file_uploader(
        "Drop CSV or PDF files here",
        type=["csv", "pdf"],
        accept_multiple_files=True,
        help="Upload multiple CSV datasets or PDF documents together.",
        key=f"file_uploader_{st.session_state.upload_version}",
        label_visibility="collapsed",
    )

    new_csv_loaded = False
    for uploaded_file in uploaded_files or []:
        file_bytes, file_name = uploaded_file.getvalue(), uploaded_file.name
        fingerprint = hashlib.sha256(file_name.encode("utf-8") + b"\\0" + file_bytes).hexdigest()
        if file_name.lower().endswith(".csv"):
            if fingerprint not in st.session_state.datasets:
                try:
                    with st.spinner(f"Loading {file_name}..."):
                        frame = load_csv_from_bytes(file_bytes, file_name)
                    if frame.empty or not len(frame.columns):
                        st.warning(f"{file_name} has no usable rows or columns.")
                        continue
                    st.session_state.datasets[fingerprint] = {"name": file_name, "frame": frame}
                    st.session_state.combined_df = None
                    new_csv_loaded = True
                    st.success(f"Loaded {file_name}: {len(frame):,} rows × {len(frame.columns)} columns")
                    if frame.isna().all(axis=None):
                        st.warning(f"{file_name} contains only missing values.")
                except Exception as exc:
                    st.error(f"Could not read {file_name}: {type(exc).__name__}: {exc}")
            continue

        if not file_name.lower().endswith(".pdf") or fingerprint in st.session_state.processed_pdf_hashes:
            continue
        if not api_key:
            st.warning(f"Enter your API key to index {file_name}.")
            continue
        try:
            with st.spinner(f"Indexing {file_name}..."):
                document = load_pdf_from_bytes(file_bytes, file_name)
                chunks = document_to_chunks(document, settings.chunk_size, settings.chunk_overlap)
                if not chunks:
                    st.warning(f"{file_name} has no extractable text.")
                    st.session_state.processed_pdf_hashes.add(fingerprint)
                    continue
                count = get_vector_store(api_key).add_documents(chunks)
                st.session_state.uploaded_docs.append(file_name)
                st.session_state.processed_pdf_hashes.add(fingerprint)
            st.success(f"Indexed {file_name}: {count:,} text chunks")
        except Exception as exc:
            st.error(f"Could not process {file_name}: {type(exc).__name__}: {exc}")

    dataset_ids = list(st.session_state.datasets)
    if dataset_ids:
        if len(dataset_ids) > 1:
            options = ["__all__", *dataset_ids]
            if new_csv_loaded or st.session_state.active_dataset_id not in options:
                st.session_state.active_dataset_id = "__all__"
                if "dataset_selector" in st.session_state:
                    del st.session_state["dataset_selector"]

            def dataset_label(dataset_id):
                if dataset_id == "__all__":
                    return f"All datasets ({len(dataset_ids)})"
                return st.session_state.datasets[dataset_id]["name"]

            selected_id = st.selectbox(
                "Dataset to analyze",
                options,
                index=options.index(st.session_state.active_dataset_id),
                format_func=dataset_label,
                key="dataset_selector",
            )
            st.session_state.active_dataset_id = selected_id
            if selected_id == "__all__":
                if st.session_state.combined_df is None:
                    frames = []
                    for dataset_id in dataset_ids:
                        item = st.session_state.datasets[dataset_id]
                        frame = item["frame"].copy()
                        source_col = "_source_file"
                        while source_col in frame.columns:
                            source_col = "_" + source_col
                        frame[source_col] = item["name"]
                        frames.append(frame)
                    st.session_state.combined_df = pd.concat(frames, ignore_index=True, sort=False)
                st.session_state.df = st.session_state.combined_df
                st.session_state.df_name = "All uploaded datasets"
            else:
                item = st.session_state.datasets[selected_id]
                st.session_state.df, st.session_state.df_name = item["frame"], item["name"]
        else:
            selected_id = dataset_ids[0]
            st.session_state.active_dataset_id = selected_id
            item = st.session_state.datasets[selected_id]
            st.session_state.df, st.session_state.df_name = item["frame"], item["name"]
    else:
        st.session_state.df = None
        st.session_state.df_name = None

    st.markdown('<div class="sidebar-section-header">DATA STATUS</div>', unsafe_allow_html=True)
    status_col1, status_col2 = st.columns(2)
    with status_col1:
        st.markdown(
            f'<div class="stat-card-clean"><div class="val">{len(st.session_state.datasets)}</div>'
            '<div class="lbl">CSV files</div></div>', unsafe_allow_html=True,
        )
    with status_col2:
        st.markdown(
            f'<div class="stat-card-clean"><div class="val">{len(st.session_state.uploaded_docs)}</div>'
            '<div class="lbl">PDF files</div></div>', unsafe_allow_html=True,
        )
    if api_key:
        stats = get_vector_store(api_key).get_stats()
        st.caption(f"{stats['document_count']:,} PDF text chunks indexed")
    elif st.session_state.uploaded_docs:
        st.caption("Enter your API key to index more PDFs.")

    # Show every active source file.
    for dataset_item in st.session_state.datasets.values():
        st.markdown(
            f'<span class="source-badge-pill">{dataset_item["name"][:30]}</span>',
            unsafe_allow_html=True,
        )
    for doc_name in st.session_state.uploaded_docs:
        st.markdown(
            f'<span class="source-badge-pill">{doc_name[:30]}</span>',
            unsafe_allow_html=True,
        )


    # HISTORY Section
    st.markdown('<div class="sidebar-section-header">HISTORY</div>', unsafe_allow_html=True)
    if not st.session_state.chat_history:
        st.markdown('<div class="sidebar-history-empty">No chats yet</div>', unsafe_allow_html=True)
    else:
        user_queries = [m["content"] for m in st.session_state.chat_history if m["role"] == "user"]
        for q in reversed(user_queries[-3:]):
            display_q = q[:22] + ("..." if len(q) > 22 else "")
            st.caption(f"💬 {display_q}")


    # Actions
    st.markdown('<div class="sidebar-section-header">ACTIONS</div>', unsafe_allow_html=True)
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    with c_btn2:
        if st.button("Reset Data", use_container_width=True):
            if api_key:
                try:
                    vs = get_vector_store(api_key)
                    vs.delete_collection()
                except Exception:
                    pass
            st.session_state.df = None
            st.session_state.df_name = None
            st.session_state.datasets = {}
            st.session_state.combined_df = None
            st.session_state.active_dataset_id = None
            st.session_state.upload_version += 1
            st.session_state.uploaded_docs = []
            st.session_state.processed_pdf_hashes = set()
            st.session_state.chat_history = []
            st.session_state.insights = []
            st.cache_resource.clear()
            st.rerun()


# ── Main Content Area ────────────────────────────────────────────
if not st.session_state.chat_history:
    logo_path = Path(__file__).resolve().parent / "assets" / "AI Data Analyst logo.png"

    # Centered hero using Streamlit's native horizontal_alignment
    with st.container():
        # Logo — centered via columns
        _, logo_col, _ = st.columns([1, 2, 1])
        with logo_col:
            if logo_path.exists():
                st.image(str(logo_path), use_container_width=True)

        # Tagline — centered HTML
        st.markdown(
            '<p style="text-align:center; font-size:1.05rem; font-weight:500; '
            'color:#8E9DB5; letter-spacing:0.08em; margin: 0.5rem 0 2rem 0;">'
            'Think · Create · Explore</p>',
            unsafe_allow_html=True,
        )

        # Quick Action Suggestion Chips — three equal columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown('<div class="chip-btn">', unsafe_allow_html=True)
            if st.button("📖 Explain My Data", key="chip_explain", use_container_width=True):
                st.session_state.pending_prompt = "Explain the key patterns, trends, and insights in my uploaded data in simple, plain-language terms."
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="chip-btn">', unsafe_allow_html=True)
            if st.button("💻 Write Analysis Code", key="chip_code", use_container_width=True):
                st.session_state.pending_prompt = "Write clean, executable Python/pandas code to analyze my dataset and compute key metrics."
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with col3:
            st.markdown('<div class="chip-btn">', unsafe_allow_html=True)
            if st.button("📊 Create a Visualization", key="chip_design", use_container_width=True):
                st.session_state.pending_prompt = "Recommend the best chart types for my data and create a visualization that reveals the key distributions."
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# Collapsible dataset preview if CSV is loaded
if st.session_state.df is not None:
    df = st.session_state.df
    with st.expander(f"📊 Dataset Loaded: {st.session_state.df_name} ({df.shape[0]:,} rows × {df.shape[1]} cols)", expanded=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Rows", f"{df.shape[0]:,}")
        with c2:
            st.metric("Columns", f"{df.shape[1]}")
        with c3:
            st.metric("Numeric", f"{df.select_dtypes(include='number').shape[1]}")
        with c4:
            st.metric("Missing cells", f"{int(df.isnull().sum().sum()):,}")
        with c5:
            st.metric("Duplicate rows", f"{int(df.duplicated().sum()):,}")

        overview_chart = auto_chart(df, title=st.session_state.df_name)
        if overview_chart:
            st.plotly_chart(overview_chart, use_container_width=True, theme=None, config={"displaylogo": False})

        st.dataframe(df.head(50), use_container_width=True, height=280)

# Conversation Stream
for i, msg in enumerate(st.session_state.chat_history):
    avatar = "🧑🏻‍🦱" if msg["role"] == "user" else "🤖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

        if msg.get("chart"):
            st.plotly_chart(msg["chart"], use_container_width=True, theme=None, key=f"chat_chart_{i}")

        if msg.get("sources"):
            with st.expander("Sources", icon="📎"):
                for src in msg["sources"]:
                    st.markdown(
                        f'<span class="source-badge-pill">📄 {src["source"]} (score: {src["score"]:.2f})</span>',
                        unsafe_allow_html=True,
                    )

        if msg.get("code"):
            with st.expander("Generated Python code", icon="💻"):
                st.code(msg["code"], language="python")

# Chat Input Handler (Rounded bar)
user_input = st.chat_input("Ask anything...")

if queued_prompt and not user_input:
    user_input = queued_prompt

if user_input:
    api_key = st.session_state.get("api_key", "")
    if not api_key:
        st.warning("Please enter your Gemini API key in the left sidebar to start chatting.")
    else:
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # Ask analyst
        analyst = get_analyst(api_key=api_key)
        with st.spinner("Thinking..."):
            try:
                result = analyst.ask(
                    question=user_input,
                    df=st.session_state.df,
                    chat_history=st.session_state.chat_history,
                )
            except Exception as exc:
                result = {
                    "answer": (
                        "I hit an unexpected error while processing your request.\n\n"
                        f"`{type(exc).__name__}: {exc}`"
                    ),
                    "sources": [],
                    "code": "",
                    "result": None,
                    "chart_suggestion": None,
                }

        # Generate chart if suggested
        chart = None
        if result.get("chart_suggestion"):
            chart = generate_chart(
                result=result.get("result"),
                chart_suggestion=result["chart_suggestion"],
                df=st.session_state.df,
            )

        # Append assistant message
        response_msg = {
            "role": "assistant",
            "content": result["answer"],
            "chart": chart,
            "sources": result.get("sources", []),
            "code": result.get("code", ""),
        }
        st.session_state.chat_history.append(response_msg)

        # Save insight if notable
        if chart or (result.get("result") is not None):
            st.session_state.insights.append(
                {
                    "question": user_input,
                    "answer": result["answer"],
                    "chart": chart,
                    "code": result.get("code", ""),
                }
            )

        st.rerun()