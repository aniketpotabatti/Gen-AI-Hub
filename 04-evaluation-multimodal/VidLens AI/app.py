"""
app.py — VidLens AI: Streamlit UI

Combines Gemini 2.5 video understanding with DuckDuckGo web search
into a rich, chat-based research assistant.
"""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv

from agent import VideoSearchAgent

load_dotenv()

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VidLens AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp {
        background: linear-gradient(135deg, #0a0a1a 0%, #0d1b2e 40%, #0a1628 100%);
        min-height: 100vh;
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f1e35 0%, #0a1220 100%);
        border-right: 1px solid rgba(99,179,237,0.15);
    }
    section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

    /* Hero */
    .hero-banner {
        background: linear-gradient(135deg,
            rgba(99,179,237,0.12) 0%, rgba(139,92,246,0.12) 50%, rgba(236,72,153,0.08) 100%);
        border: 1px solid rgba(99,179,237,0.25);
        border-radius: 20px;
        padding: 2rem 2.5rem;
        margin-bottom: 1.5rem;
        backdrop-filter: blur(12px);
        position: relative;
        overflow: hidden;
    }
    .hero-banner::before {
        content: '';
        position: absolute; top: -50%; left: -50%;
        width: 200%; height: 200%;
        background: radial-gradient(circle at 30% 50%, rgba(99,179,237,0.06) 0%, transparent 60%);
        animation: pulse-glow 6s ease-in-out infinite;
    }
    @keyframes pulse-glow {
        0%, 100% { opacity: 0.5; transform: scale(1); }
        50%       { opacity: 1;   transform: scale(1.05); }
    }
    .hero-title {
        font-size: 2.2rem; font-weight: 700;
        background: linear-gradient(90deg, #63b3ed, #9f7aea, #f687b3);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; margin: 0 0 0.4rem 0; line-height: 1.2;
    }
    .hero-subtitle { color: #90cdf4; font-size: 1rem; margin: 0; opacity: 0.85; }
    .badge-row { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-top: 1rem; }
    .badge {
        display: inline-flex; align-items: center; gap: 0.35rem;
        background: rgba(99,179,237,0.1); border: 1px solid rgba(99,179,237,0.3);
        border-radius: 50px; padding: 0.3rem 0.85rem;
        font-size: 0.78rem; font-weight: 500; color: #90cdf4;
    }
    .badge.green  { background: rgba(72,187,120,0.1);  border-color: rgba(72,187,120,0.3);  color: #68d391; }
    .badge.purple { background: rgba(159,122,234,0.1); border-color: rgba(159,122,234,0.3); color: #b794f4; }
    .badge.pink   { background: rgba(246,135,179,0.1); border-color: rgba(246,135,179,0.3); color: #f687b3; }

    /* Upload placeholder */
    .upload-card {
        background: rgba(15,30,55,0.7);
        border: 2px dashed rgba(99,179,237,0.3);
        border-radius: 16px; padding: 1.5rem; text-align: center;
        transition: border-color 0.3s ease; backdrop-filter: blur(8px);
    }
    .upload-card:hover { border-color: rgba(99,179,237,0.6); }

    /* Section header label */
    .section-header {
        font-size: 0.75rem; font-weight: 600; letter-spacing: 0.12em;
        text-transform: uppercase; color: #718096; margin: 1.2rem 0 0.6rem 0;
    }

    /* Info / warn / success panels */
    .info-panel, .warn-panel, .success-panel {
        border-radius: 0 10px 10px 0;
        padding: 0.75rem 1rem; margin: 0.8rem 0; font-size: 0.88rem;
    }
    .info-panel    { background: rgba(99,179,237,0.07);  border-left: 3px solid #63b3ed; color: #90cdf4; }
    .warn-panel    { background: rgba(246,173,85,0.07);  border-left: 3px solid #f6ad55; color: #fbd38d; }
    .success-panel { background: rgba(72,187,120,0.07);  border-left: 3px solid #48bb78; color: #68d391; }

    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: rgba(15,30,55,0.8) !important;
        border: 1px solid rgba(99,179,237,0.25) !important;
        border-radius: 10px !important; color: #e2e8f0 !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: rgba(99,179,237,0.6) !important;
        box-shadow: 0 0 0 3px rgba(99,179,237,0.1) !important;
    }

    /* Primary button */
    .stButton > button {
        background: linear-gradient(135deg, #4299e1, #805ad5) !important;
        color: white !important; border: none !important;
        border-radius: 10px !important; font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.25s ease !important; width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(66,153,225,0.35) !important;
    }
    .stButton > button:active { transform: translateY(0) !important; }

    /* Widget labels */
    .stSelectbox label, .stSlider label, .stToggle label, .stFileUploader label {
        color: #90cdf4 !important; font-size: 0.88rem !important; font-weight: 500 !important;
    }

    /* Hide default header */
    header[data-testid="stHeader"] { display: none; }

    /* Chat input */
    .stChatInput > div {
        background: rgba(15,30,55,0.8) !important;
        border: 1px solid rgba(99,179,237,0.3) !important;
        border-radius: 14px !important;
    }

    .stSpinner > div { color: #63b3ed !important; }

    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(99,179,237,0.25); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(99,179,237,0.45); }
    hr { border-color: rgba(99,179,237,0.1) !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state ──────────────────────────────────────────────────────────
_DEFAULTS: dict = {
    "chat_history":   [],
    "agent":          None,
    "video_uploaded": False,
    "video_file_name": None,
    "api_key_set":    False,
}
for _k, _v in _DEFAULTS.items():
    st.session_state.setdefault(_k, _v)

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align:center;padding:1rem 0 1.5rem 0;">
            <div style="font-size:2.5rem;">🎬</div>
            <div style="font-size:1.1rem;font-weight:700;
                        background:linear-gradient(90deg,#63b3ed,#9f7aea);
                        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                        background-clip:text;">
                VidLens AI
            </div>
            <div style="font-size:0.75rem;color:#718096;margin-top:0.2rem;">
                Powered by Gemini 2.5 + DuckDuckGo
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-header">🔑 Authentication</div>', unsafe_allow_html=True)
    api_key_input = st.text_input(
        "Google AI Studio API Key",
        value=os.getenv("GOOGLE_API_KEY", ""),
        type="password",
        placeholder="AIza...",
        help="Get your free key at https://aistudio.google.com/",
    )

    st.markdown('<div class="section-header">🤖 Model</div>', unsafe_allow_html=True)
    model_choice = st.selectbox(
        "Gemini Model",
        options=["gemini-2.5-flash", "gemini-2.5-pro"],
        format_func=lambda m: {
            "gemini-2.5-flash": "⚡ Gemini 2.5 Flash (Fast)",
            "gemini-2.5-pro":   "💎 Gemini 2.5 Pro (Powerful)",
        }[m],
        help="Flash is faster; Pro has stronger reasoning.",
    )

    st.markdown('<div class="section-header">🌐 Web Search</div>', unsafe_allow_html=True)
    enable_search = st.toggle("Enable DuckDuckGo Search", value=True)
    search_count  = st.slider("Results to fetch", 1, 10, 5, disabled=not enable_search)

    st.markdown("---")

    if st.button("✅ Apply Settings", key="apply_settings"):
        if not api_key_input.strip():
            st.error("Please enter a valid Google API key.")
        else:
            st.session_state.agent          = VideoSearchAgent(api_key_input.strip(), model_choice)
            st.session_state.api_key_set    = True
            st.session_state.video_uploaded = False
            st.session_state.video_file_name = None
            st.session_state.chat_history   = []
            st.success("✅ Agent initialised!")

    st.markdown("---")
    st.markdown('<div class="section-header">📊 Status</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="font-size:0.82rem;line-height:2;">
            <span style="color:#718096">Agent:</span>
            <span style="color:#68d391">{"🟢 Ready" if st.session_state.api_key_set else "🔴 Not configured"}</span><br>
            <span style="color:#718096">Video:</span>
            <span style="color:#90cdf4">{"🎬 " + st.session_state.video_file_name if st.session_state.video_uploaded else "⬜ No video"}</span><br>
            <span style="color:#718096">Search:</span>
            <span style="color:#b794f4">{"🌐 On" if enable_search else "⬜ Off"}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")
    st.markdown(
        '<div style="font-size:0.72rem;color:#4a5568;text-align:center;">'
        "Built with ❤️ using Gemini 2.5 &amp; Streamlit"
        "</div>",
        unsafe_allow_html=True,
    )

# ── Hero ───────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero-banner">
        <h1 class="hero-title">🎬 VidLens AI</h1>
        <p class="hero-subtitle">
            Upload any video, ask anything — deep visual understanding
            combined with live web research for rich, accurate answers.
        </p>
        <div class="badge-row">
            <span class="badge">🎥 MP4 · MOV · AVI</span>
            <span class="badge green">⚡ Gemini 2.5</span>
            <span class="badge purple">🌐 DuckDuckGo</span>
            <span class="badge pink">💬 Multi-turn Chat</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.api_key_set:
    st.markdown(
        '<div class="warn-panel">⚠️ <strong>Getting started:</strong> '
        "Enter your Google AI Studio API key in the sidebar and click <em>Apply Settings</em>.</div>",
        unsafe_allow_html=True,
    )
    st.stop()

# ── Layout ─────────────────────────────────────────────────────────────────
col_video, col_chat = st.columns([1, 1.6], gap="large")

# Left: video upload
with col_video:
    st.markdown('<p class="section-header">📁 Video Upload</p>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Drop your video here",
        type=["mp4", "mov", "avi", "mkv", "webm"],
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        st.video(uploaded_file)

        # Reset state when a new file is selected
        if uploaded_file.name != st.session_state.video_file_name:
            st.session_state.video_uploaded  = False
            st.session_state.video_file_name = uploaded_file.name
            st.session_state.chat_history    = []

        if st.session_state.video_uploaded:
            st.markdown(
                f'<div class="success-panel">✅ <strong>{uploaded_file.name}</strong> ready for analysis!</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="info-panel">📎 <strong>{uploaded_file.name}</strong>'
                f"<br>Size: {uploaded_file.size / 1_048_576:.1f} MB</div>",
                unsafe_allow_html=True,
            )
            if st.button("🚀 Upload & Process Video", key="upload_btn"):
                try:
                    with st.spinner("📤 Uploading & processing video…"):
                        st.session_state.agent.upload_video(
                            uploaded_file.read(), uploaded_file.name
                        )
                    st.session_state.video_uploaded = True
                    st.rerun()
                except Exception as exc:
                    st.error(f"❌ Upload failed: {exc}")
    else:
        st.markdown(
            """
            <div class="upload-card">
                <div style="font-size:2.5rem;margin-bottom:0.5rem;">🎬</div>
                <div style="color:#63b3ed;font-weight:600;margin-bottom:0.3rem;">Drop a video to get started</div>
                <div style="color:#4a5568;font-size:0.82rem;">MP4 · MOV · AVI · MKV · WebM</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<p class="section-header">💡 What you can ask</p>', unsafe_allow_html=True)
    st.markdown(
        """
        <div style="background:rgba(15,25,45,0.6);border:1px solid rgba(99,179,237,0.15);
                    border-radius:14px;padding:1rem 1.2rem;font-size:0.85rem;
                    color:#90cdf4;line-height:1.9;">
            🔍 &nbsp;Describe what's happening in the video<br>
            📊 &nbsp;Identify objects, text, or people on screen<br>
            📚 &nbsp;Compare video content with current web data<br>
            🧠 &nbsp;Summarise key moments or extract insights<br>
            🌐 &nbsp;Research topics shown in the video online<br>
            ❓ &nbsp;Ask follow-up questions in multi-turn chat
        </div>
        """,
        unsafe_allow_html=True,
    )

# Right: chat
with col_chat:
    st.markdown('<p class="section-header">💬 Chat with your Video</p>', unsafe_allow_html=True)

    with st.container(height=480):
        if not st.session_state.chat_history:
            st.markdown(
                """
                <div style="text-align:center;padding:3rem 1rem;color:#4a5568;">
                    <div style="font-size:2rem;margin-bottom:0.5rem;">🤖</div>
                    <div style="font-size:0.9rem;">
                        Upload a video and start asking questions.<br>
                        <span style="color:#2d3748;">
                        I analyse the video and search the web to enrich my answers.
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for turn in st.session_state.chat_history:
                if turn["role"] == "user":
                    with st.chat_message("user"):
                        st.markdown(turn["content"])
                else:
                    with st.chat_message("assistant"):
                        st.markdown(turn["content"])

    if not st.session_state.video_uploaded:
        st.markdown(
            '<div class="info-panel">ℹ️ Upload and process a video to start chatting.</div>',
            unsafe_allow_html=True,
        )
    else:
        user_input = st.chat_input("Ask anything about the video…")

        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            try:
                with st.spinner("🧠 Thinking…"):
                    chunks = list(
                        st.session_state.agent.run(
                            user_query=user_input,
                            chat_history=st.session_state.chat_history,
                            enable_web_search=enable_search,
                            search_results_count=search_count,
                        )
                    )
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": "".join(chunks)}
                )
            except Exception as exc:
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": f"❌ Error: {exc}"}
                )

            st.rerun()

        if st.session_state.chat_history:
            if st.button("🗑️ Clear Chat History", key="clear_chat"):
                st.session_state.chat_history = []
                st.rerun()
