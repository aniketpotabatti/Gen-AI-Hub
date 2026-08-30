"""
AI Data Analyst — Streamlit Dashboard
Main entry point: streamlit run src/app.py
"""

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
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────

st.markdown(
    """
<style>
    /* ── Global ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    :root {
        --ink: #f8fafc;
        --muted: #94a3b8;
        --line: #263449;
        --surface: #111c2f;
        --accent: #60a5fa;
    }

    .stApp {
        font-family: 'Inter', sans-serif;
        background: #0b1220;
        color: var(--ink);
    }

    section[data-testid="stMain"] .block-container {
        max-width: 1380px;
        padding-top: 268px;
        padding-bottom: 72px;
    }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: #0f172a;
        border-right: 1px solid #263244;
        z-index: 1000000;
    }

    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        color: #f8fafc !important;
    }

    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] label {
        color: #94a3b8;
    }

    /* Keep the supplied brand image visible while the workspace scrolls. */
    .st-key-main_app_header {
        /* Choose one: absolute | fixed | sticky | relative | static */
        position: absolute;
        top: 10px;
        z-index: 9999999;
        height: 220px;
        width: auto;
        padding: 26px 50px;
        margin: 0;
        background: linear-gradient(110deg, #12233d 0%, #0f1b2e 55%, #111c2f 100%);
        border-radius: 12px;
        backdrop-filter: blur(10px);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.14);
    }

    .st-key-main_app_header img {
        max-height: 180px;
        width: auto !important;
        object-fit: contain;
    }

    .welcome-panel {
        margin: 28px 0 24px;
        padding: 26px 30px;
        border: 1px solid #263449;
        border-radius: 12px;
        background: linear-gradient(110deg, #12233d 0%, #0f1b2e 55%, #111c2f 100%);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.14);
    }

    .welcome-kicker {
        color: #60a5fa;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }

    .welcome-title {
        margin: 6px 0 4px;
        color: #f8fafc;
        font-size: 1.7rem;
        font-weight: 700;
    }

    .welcome-copy {
        margin: 0;
        max-width: 680px;
        color: #a8b6ca;
        font-size: 0.95rem;
    }

    .chat-user {
        background: #132b4d;
        border: 1px solid #24518a;
        border-radius: 14px 14px 4px 14px;
        padding: 14px 18px;
        margin: 8px 0;
        color: #dbeafe;
    }

    .chat-ai {
        background: #111c2f;
        border: 1px solid var(--line);
        border-radius: 14px 14px 14px 4px;
        padding: 14px 18px;
        margin: 8px 0;
        color: #dbe4f0;
    }

    /* ── Stat cards ── */
    .stat-card {
        background: #111c2f;
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 3px 12px rgba(15, 23, 42, 0.04);
        transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
    }

    .stat-card:hover {
        transform: translateY(-2px);
        border-color: #3b82f6;
        box-shadow: 0 8px 22px rgba(37, 99, 235, 0.10);
    }

    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        color: #93c5fd;
    }

    .stat-label {
        font-size: 0.85rem;
        color: var(--muted);
        margin-top: 4px;
        line-height: 1.45;
        letter-spacing: 0.02em;
    }

    /* ── Source badges ── */
    .source-badge {
        display: inline-block;
        background: #132b4d;
        border: 1px solid #24518a;
        border-radius: 999px;
        padding: 4px 12px;
        font-size: 0.78rem;
        color: #93c5fd;
        margin: 2px 4px 2px 0;
    }

    /* ── Upload zone ── */
    .upload-zone {
        border: 2px dashed #315b91;
        border-radius: 10px;
        padding: 30px;
        text-align: center;
        background: #0f1b2e;
        transition: border-color 0.3s, background 0.3s;
    }

    .upload-zone:hover {
        border-color: #60a5fa;
        background: #132b4d;
    }

    /* ── Code blocks ── */
    .code-block {
        background: #172033;
        border-radius: 10px;
        padding: 12px 16px;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.85rem;
        overflow-x: auto;
    }

    /* ── Dividers ── */
    .soft-divider {
        border: none;
        height: 1px;
        background: var(--line);
        margin: 20px 0;
    }

    /* ── Streamlit overrides ── */
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 1px solid #334155;
        background: #0f1b2e;
        color: #f8fafc;
        padding: 12px 16px;
    }

    .stTextInput > div > div > input:focus {
        border-color: #60a5fa;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
    }

    .stTextInput > div > div > input::placeholder {
        color: #64748b;
        opacity: 1;
    }

    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
        color: #f8fafc;
        background: #17253a;
        border: 1px solid #334155;
    }

    div[data-testid="stFileUploader"] {
        border-radius: 12px;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 1px solid var(--line);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 7px 7px 0 0;
        padding: 10px 18px;
        color: #cbd5e1 !important;
        font-weight: 500;
    }

    .stTabs [aria-selected="true"] {
        color: #93c5fd !important;
        border-bottom-color: #2563eb !important;
    }

    /* Layout refinements. Colors are defined in .streamlit/config.toml. */
    .stApp {
        background: var(--background-color) !important;
    }

    section[data-testid="stSidebar"] {
        background: var(--background-color) !important;
        border-right-color: var(--border-color) !important;
    }

    section[data-testid="stMain"] .block-container {
        max-width: 1240px;
        padding-bottom: 56px;
    }

    .st-key-main_app_header {
        left: max(1.5rem, calc((100vw - 1240px) / 2));
        right: max(1.5rem, calc((100vw - 1240px) / 2));
        background: color-mix(in srgb, var(--secondary-background-color) 94%, var(--primary-color)) !important;
        border-color: var(--border-color) !important;
        box-shadow: 0 16px 38px rgba(0, 0, 0, 0.26);
    }

    .welcome-panel,
    .stat-card,
    .upload-zone,
    .chat-ai {
        background: var(--secondary-background-color) !important;
        border-color: var(--border-color) !important;
        box-shadow: none;
    }

    .welcome-panel {
        border-left: 3px solid var(--primary-color) !important;
    }

    .welcome-kicker,
    .stat-value,
    .source-badge {
        color: var(--primary-color) !important;
    }

    .welcome-copy,
    .stat-label {
        color: color-mix(in srgb, var(--text-color) 68%, transparent) !important;
    }

    .chat-user,
    .source-badge {
        background: color-mix(in srgb, var(--primary-color) 12%, var(--secondary-background-color)) !important;
        border-color: color-mix(in srgb, var(--primary-color) 38%, var(--border-color)) !important;
        color: var(--text-color) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        border-bottom-color: var(--border-color) !important;
    }

    .stTabs [data-baseweb="tab"] {
        color: color-mix(in srgb, var(--text-color) 62%, transparent) !important;
    }

    .stTabs [aria-selected="true"] {
        color: var(--primary-color) !important;
        border-bottom-color: var(--primary-color) !important;
    }

    .stButton > button {
        background: transparent !important;
        border-color: var(--border-color) !important;
        color: var(--text-color) !important;
    }

    .stButton > button:hover {
        border-color: var(--primary-color) !important;
        color: var(--primary-color) !important;
    }

    @media (max-width: 640px) {
        section[data-testid="stMain"] .block-container {
            padding-top: 176px;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .st-key-main_app_header {
            height: 150px;
            left: 1rem;
            right: 1rem;
        }

        .st-key-main_app_header img {
            max-height: 116px;
            max-width: 220px;
        }

        .st-key-main_app_header > div {
            padding: 0 1rem;
        }

        .app-title {
            font-size: 1rem;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)


# ── Session State Init ───────────────────────────────────────────


def init_session():
    """Initialize all session state variables."""
    defaults = {
        "chat_history": [],
        "df": None,
        "df_name": None,
        "uploaded_docs": [],
        "insights": [],
        "api_key": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_session()


# ── Lazy-loaded singletons ───────────────────────────────────────


@st.cache_resource
def get_vector_store(api_key):
    return VectorStore(api_key=api_key)


@st.cache_resource
def get_analyst(api_key):
    return AIAnalyst(api_key=api_key, vector_store=get_vector_store(api_key))


# ── Sidebar ──────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("#### :material/key: API key")
    api_key_input = st.text_input(
        "Enter your Gemini API key",
        type="password",
        placeholder="AIza...",
        help="Paste your Gemini API key here to enable chat, PDF indexing, and analysis.",
        key="api_key_input",
    )
    if api_key_input:
        st.session_state.api_key = api_key_input.strip()
    elif "api_key" in st.session_state:
        del st.session_state.api_key

    api_key = st.session_state.get("api_key", "")
    if api_key:
        st.success("API key configured")
    else:
        st.warning("API key not set")

    st.markdown('<hr class="soft-divider">', unsafe_allow_html=True)

    # ── File Upload Section
    st.markdown("#### :material/upload_file: Upload data")

    uploaded_file = st.file_uploader(
        "Drop your CSV or PDF here",
        type=["csv", "pdf"],
        help="CSV files are analyzed with pandas. PDFs are indexed for Q&A.",
        key="file_uploader",
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        file_name = uploaded_file.name

        if file_name.lower().endswith(".csv"):
            with st.spinner("Loading CSV..."):
                df = load_csv_from_bytes(file_bytes, file_name)
                st.session_state.df = df
                st.session_state.df_name = file_name
                st.success(f"✅ **{file_name}** loaded — {df.shape[0]:,} rows × {df.shape[1]} columns")

        elif file_name.lower().endswith(".pdf"):
            if not api_key:
                st.warning("Enter your API key first to index PDFs.")
            # Only process if not already uploaded
            elif file_name not in st.session_state.uploaded_docs:
                with st.spinner("Processing PDF..."):
                    doc = load_pdf_from_bytes(file_bytes, file_name)
                    chunks = document_to_chunks(doc, settings.chunk_size, settings.chunk_overlap)
                    vs = get_vector_store(api_key)
                    count = vs.add_documents(chunks)
                    st.session_state.uploaded_docs.append(file_name)
                    st.success(f"✅ **{file_name}** indexed — {count} chunks stored")
            else:
                st.info(f"📄 **{file_name}** already indexed")

    # ── Data Status
    st.markdown("#### :material/monitoring: Data status")
    if api_key:
        vs = get_vector_store(api_key)
        stats = vs.get_stats()

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f'<div class="stat-card"><div class="stat-value">{stats["document_count"]}</div>'
                f'<div class="stat-label">Doc Chunks</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            csv_status = "✅" if st.session_state.df is not None else "—"
            st.markdown(
                f'<div class="stat-card"><div class="stat-value">{csv_status}</div>'
                f'<div class="stat-label">CSV Loaded</div></div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("Enter your API key above to load document stats and enable analysis.")

    # List uploaded sources
    if st.session_state.uploaded_docs:
        st.markdown("**Indexed Documents:**")
        for doc_name in st.session_state.uploaded_docs:
            st.markdown(f'<span class="source-badge">📄 {doc_name}</span>', unsafe_allow_html=True)

    if st.session_state.df_name:
        st.markdown(f'<span class="source-badge">📊 {st.session_state.df_name}</span>', unsafe_allow_html=True)

    st.markdown('<hr class="soft-divider">', unsafe_allow_html=True)

    # ── Actions
    if st.button("Clear chat", icon=":material/delete_sweep:", width="stretch"):
        st.session_state.chat_history = []
        st.rerun()

    if st.button("Reset all data", icon=":material/restart_alt:", width="stretch"):
        if api_key:
            vs = get_vector_store(api_key)
            vs.delete_collection()
        st.session_state.df = None
        st.session_state.df_name = None
        st.session_state.uploaded_docs = []
        st.session_state.chat_history = []
        st.session_state.insights = []
        st.cache_resource.clear()
        st.rerun()


# ── Main Content ─────────────────────────────────────────────────

# Main app title

with st.container(key="main_app_header", horizontal_alignment="center"):
    st.image("src/assets/AI Data Analyst logo.png", width=400)

# ── Tabs
tab_chat, tab_data, tab_insights = st.tabs(["Chat", "Data Preview", "Saved Insights"])

# ── Tab 1: Chat ──────────────────────────────────────────────────

with tab_chat:
    # Display chat history
    for msg in st.session_state.chat_history:
        avatar = ":material/person:" if msg["role"] == "user" else ":material/auto_awesome:"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

            if msg.get("chart"):
                st.plotly_chart(msg["chart"], width="stretch", key=f"chart_{id(msg)}")

            if msg.get("sources"):
                with st.expander("Sources", icon=":material/attach_file:"):
                    for src in msg["sources"]:
                        st.markdown(
                            f'<span class="source-badge">{src["source"]} '
                            f'(score: {src["score"]:.2f})</span>',
                            unsafe_allow_html=True,
                        )

            if msg.get("code"):
                with st.expander("Generated code", icon=":material/code:"):
                    st.code(msg["code"], language="python")

    # ── Empty state
    if not st.session_state.chat_history:
        with st.container(border=True):
            st.markdown(":primary[:material/auto_awesome: **Workspace ready**]")
            st.subheader("Turn your files into clear answers.")
            st.caption("Upload a CSV or PDF from the sidebar, then explore patterns and save useful findings.")
        col1, col2, col3 = st.columns(3)
        with col1:
            with st.container(border=True):
                st.markdown(":material/description:")
                st.markdown("**Ask your documents**")
                st.caption("Upload a PDF to start a grounded conversation.")
        with col2:
            with st.container(border=True):
                st.markdown(":material/table_chart:")
                st.markdown("**Analyze a dataset**")
                st.caption("Upload a CSV for summaries, calculations, and trends.")
        with col3:
            with st.container(border=True):
                st.markdown(":material/insights:")
                st.markdown("**Save useful insights**")
                st.caption("Charts and computed findings are saved automatically.")

    # ── Chat input
    api_key = st.session_state.get("api_key", "")
    if api_key:
        question = st.chat_input("Ask anything about your data...")
    else:
        st.info("Enter your API key in the sidebar to start chatting.")
        question = None

    if question and api_key:
        # Add user message
        st.session_state.chat_history.append({"role": "user", "content": question})

        # Get AI response
        analyst = get_analyst(api_key=api_key)

        with st.spinner("🧠 Analyzing..."):
            try:
                result = analyst.ask(
                    question=question,
                    df=st.session_state.df,
                    chat_history=st.session_state.chat_history,
                )
            except Exception as exc:
                result = {
                    "answer": (
                        "I hit an unexpected runtime error while processing your question.\n\n"
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

        # Build response message
        response_msg = {
            "role": "assistant",
            "content": result["answer"],
            "chart": chart,
            "sources": result.get("sources", []),
            "code": result.get("code", ""),
        }

        st.session_state.chat_history.append(response_msg)

        # Auto-save notable insights
        if chart or (result.get("result") is not None):
            st.session_state.insights.append(
                {
                    "question": question,
                    "answer": result["answer"],
                    "chart": chart,
                    "code": result.get("code", ""),
                }
            )

        st.rerun()


# ── Tab 2: Data Preview ──────────────────────────────────────────

with tab_data:
    if st.session_state.df is not None:
        df = st.session_state.df

        st.markdown(f"### 📊 {st.session_state.df_name}")
        st.markdown(f"**{df.shape[0]:,} rows** × **{df.shape[1]} columns**")
        st.markdown('<hr class="soft-divider">', unsafe_allow_html=True)

        # Summary stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                f'<div class="stat-card"><div class="stat-value">{df.shape[0]:,}</div>'
                f'<div class="stat-label">Rows</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="stat-card"><div class="stat-value">{df.shape[1]}</div>'
                f'<div class="stat-label">Columns</div></div>',
                unsafe_allow_html=True,
            )
        with col3:
            numeric = df.select_dtypes(include="number").shape[1]
            st.markdown(
                f'<div class="stat-card"><div class="stat-value">{numeric}</div>'
                f'<div class="stat-label">Numeric</div></div>',
                unsafe_allow_html=True,
            )
        with col4:
            missing = df.isnull().sum().sum()
            st.markdown(
                f'<div class="stat-card"><div class="stat-value">{missing:,}</div>'
                f'<div class="stat-label">Missing Values</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown('<hr class="soft-divider">', unsafe_allow_html=True)

        # Auto-generated overview chart
        overview_chart = auto_chart(df, title=st.session_state.df_name or "Data Overview")
        if overview_chart:
            st.plotly_chart(overview_chart, width="stretch")

        st.markdown('<hr class="soft-divider">', unsafe_allow_html=True)

        # Data table
        st.markdown("### 📋 Data Table")
        st.dataframe(df.head(100), width="stretch", height=400)

        # Column info
        with st.expander("📐 Column Details"):
            col_info = pd.DataFrame(
                {
                    "Column": df.columns,
                    "Type": df.dtypes.astype(str).values,
                    "Non-Null": df.count().values,
                    "Null %": (df.isnull().mean() * 100).round(1).values,
                    "Unique": df.nunique().values,
                }
            )
            st.dataframe(col_info, width="stretch", hide_index=True)

    else:
        st.markdown('<div class="upload-zone">', unsafe_allow_html=True)
        st.markdown("### 📊 No CSV Loaded")
        st.markdown("Upload a CSV file from the sidebar to see your data here.")
        st.markdown("</div>", unsafe_allow_html=True)


# ── Tab 3: Saved Insights ────────────────────────────────────────

with tab_insights:
    if st.session_state.insights:
        st.markdown(f"### 💡 {len(st.session_state.insights)} Saved Insights")
        st.markdown("Insights are auto-saved when the AI generates charts or computed results.")
        st.markdown('<hr class="soft-divider">', unsafe_allow_html=True)

        for i, insight in enumerate(reversed(st.session_state.insights)):
            with st.container():
                st.markdown(f"**Q:** {insight['question']}")
                st.markdown(insight["answer"])

                if insight.get("chart"):
                    st.plotly_chart(insight["chart"], width="stretch", key=f"insight_chart_{i}")

                if insight.get("code"):
                    with st.expander("🔧 Code"):
                        st.code(insight["code"], language="python")

                st.markdown('<hr class="soft-divider">', unsafe_allow_html=True)

        if st.button("🗑️ Clear All Insights", width="stretch"):
            st.session_state.insights = []
            st.rerun()
    else:
        st.markdown('<div class="upload-zone">', unsafe_allow_html=True)
        st.markdown("### 💡 No Insights Yet")
        st.markdown("Ask questions in the Chat tab — insights with charts and results are saved automatically.")
        st.markdown("</div>", unsafe_allow_html=True)
