import streamlit as st
import google.generativeai as genai
import os, re, json, base64
import requests
import yt_dlp
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="YouTube Video Summarizer & AI Assistant",
    page_icon="🎬"
)

AVAILABLE_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.0-flash"
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]
DEFAULT_MODEL = "gemini-2.5-flash"
MAX_CHARS = 35_000
DEPTH_MAP = {
    "Quick Brief (~150 words)": 150,
    "Standard Summary (~350 words)": 350,
    "Deep Dive (~700 words)": 700
}

# ── Session State Defaults ───────────────────────────────────────────────────
env_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
defaults = {
    "google_api_key": env_api_key,
    "selected_model": DEFAULT_MODEL,
    "details": None,
    "summary": None,
    "chat": [],
    "history": [],
    "transcript_filter": "",
}
for key, val in defaults.items():
    st.session_state.setdefault(key, val)

if st.session_state.google_api_key:
    try:
        genai.configure(api_key=st.session_state.google_api_key)
    except Exception:
        pass


# ── Helpers ───────────────────────────────────────────────────────────────────
def b64_img(path):
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "rb") as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    except Exception:
        return ""

def fmt_num(val):
    if val is None or val == "":
        return "—"
    try:
        return f"{int(val):,}"
    except Exception:
        return str(val)

def parse_date(raw):
    if not raw:
        return "—"
    try:
        return datetime.strptime(str(raw), "%Y%m%d").strftime("%b %d, %Y")
    except Exception:
        return str(raw)

def extract_video_id(url):
    if not url:
        return None
    patterns = [
        r"(?:v=|\/embed\/|\/v\/|\/shorts\/|youtu\.be\/)([0-9A-Za-z_-]{11})",
        r"^([0-9A-Za-z_-]{11})$"
    ]
    for p in patterns:
        match = re.search(p, url.strip())
        if match:
            return match.group(1)
    return None

def valid_yt_url(url):
    return extract_video_id(url) is not None


# ── Data Fetching ─────────────────────────────────────────────────────────────
def _fetch_oembed(video_id):
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            d = r.json()
            return {
                "id": video_id,
                "title": d.get("title") or "YouTube Video",
                "channel": d.get("author_name") or "Unknown Channel",
                "thumb": d.get("thumbnail_url") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                "date": "",
                "views": "",
                "likes": "",
                "duration": "—",
                "lang": "en",
            }
    except Exception:
        pass
    return None

def _fetch_transcript_ytdlp(video_id):
    """Fallback transcript extractor using yt-dlp subtitle streams."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en.*", ".*"],
        "quiet": True,
        "no_warnings": True,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}}
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            subs = info.get("subtitles") or info.get("automatic_captions") or {}
            
            chosen_track = None
            for lang_code in subs:
                if lang_code.startswith("en"):
                    chosen_track = subs[lang_code]
                    break
            if not chosen_track and subs:
                chosen_track = list(subs.values())[0]

            if not chosen_track:
                return ""

            sub_url = None
            for fmt in chosen_track:
                if fmt.get("ext") == "json3":
                    sub_url = fmt.get("url")
                    break
                elif fmt.get("ext") in ("vtt", "ttml"):
                    sub_url = fmt.get("url")

            if not sub_url and chosen_track:
                sub_url = chosen_track[0].get("url")

            if not sub_url:
                return ""

            r = requests.get(sub_url, timeout=15)
            if r.status_code != 200:
                return ""

            if "json3" in sub_url or "json" in r.headers.get("content-type", ""):
                try:
                    data = r.json()
                    lines = []
                    for event in data.get("events", []):
                        for seg in event.get("segs", []):
                            t = seg.get("utf8", "").strip()
                            if t and t != "\n":
                                lines.append(t)
                    return re.sub(r"\s+", " ", " ".join(lines)).strip()
                except Exception:
                    pass
            # Clean VTT/TTML text if fallback
            clean = re.sub(r"<[^>]+>", "", r.text)
            clean = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}", "", clean)
            clean = re.sub(r"WEBVTT|Kind:|Language:", "", clean)
            return re.sub(r"\s+", " ", clean).strip()
    except Exception:
        return ""


@st.cache_data(ttl=3600, show_spinner=False)
def get_video(url):
    video_id = extract_video_id(url)
    if not video_id:
        st.error("Invalid YouTube URL provided.")
        return None

    video_url = f"https://www.youtube.com/watch?v={video_id}"
    info = {}
    error_msg = None

    # Step 1: Video Metadata via yt-dlp
    try:
        ydl_opts = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "referer": "https://www.youtube.com/",
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "web"],
                }
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False) or {}
    except Exception as e:
        error_msg = str(e)

    if not info:
        oembed = _fetch_oembed(video_id)
        if oembed:
            data = oembed
        else:
            st.error(f"Could not fetch video details from YouTube. {error_msg or ''}")
            return None
    else:
        dur = info.get("duration_string")
        if not dur and info.get("duration"):
            m, s = divmod(int(info.get("duration")), 60)
            h, m = divmod(m, 60)
            dur = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
        
        data = {
            "id": video_id,
            "title": info.get("title") or "YouTube Video",
            "channel": info.get("channel") or info.get("uploader") or "Unknown Channel",
            "thumb": info.get("thumbnail") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            "date": info.get("upload_date") or "",
            "views": info.get("view_count") or "",
            "likes": info.get("like_count") or "",
            "duration": dur or "—",
            "lang": info.get("language") or "en",
        }

    # Step 2: Robust Multi-tier Transcript Fetching
    transcript, lang = "", data.get("lang") or "en"

    # Tier 1: youtube_transcript_api with dict safe access
    try:
        tl = YouTubeTranscriptApi.list_transcripts(video_id)
        preferred = ["en", "en-US", "en-GB"] + [t.language_code for t in tl]
        t = tl.find_transcript(preferred)
        lang = t.language_code
        raw_items = t.fetch()
        
        # Correctly handle list of dict objects returned by fetch()
        lines = []
        for item in raw_items:
            if isinstance(item, dict):
                text_str = item.get("text", "")
            else:
                text_str = getattr(item, "text", "")
            if text_str:
                lines.append(text_str)
        transcript = " ".join(lines).strip()
    except Exception:
        pass

    # Tier 2: Fallback to yt-dlp transcript fetcher if Tier 1 returned empty
    if not transcript:
        transcript = _fetch_transcript_ytdlp(video_id)

    if len(transcript) > MAX_CHARS:
        transcript = transcript[:MAX_CHARS] + "\n\n[Transcript truncated due to length limits]"

    data["lang"] = lang
    data["transcript"] = transcript if transcript else "No transcript available for this video."
    data["has_transcript"] = bool(transcript)
    return data


# ── AI Logic ──────────────────────────────────────────────────────────────────
def summarize_video(d, word_target=350, model_name=DEFAULT_MODEL):
    if not st.session_state.google_api_key:
        st.error("⚠️ Please enter your Google API Key in the sidebar.")
        return ""

    if not d.get("has_transcript"):
        return ("⚠️ **Transcript Unavailable**: YouTube did not return a transcript for this video. "
                "The video might not have captions or auto-generated subtitles enabled.")

    genai.configure(api_key=st.session_state.google_api_key)
    prompt = f"""You are an expert content analyzer. Provide a thorough, elegant, and well-structured summary of the following YouTube video.

Title: {d['title']}
Channel: {d['channel']}
Duration: {d['duration']}

Transcript:
{d['transcript']}

Formatting Instructions:
- Target approximately ~{word_target} words overall.
- Format strictly in clean Markdown with appropriate emojis for section headers.
- Use clear bullet points and bold highlights for key technical terms or important concepts.

Structure your response with these exact section headings:
### 📌 Executive Summary
(2-3 high-impact sentences summarizing the core message)

### 💡 Key Takeaways
(4-6 crisp bullet points highlighting main insights or lessons)

### 🗂 Detailed Breakdown
(Structured paragraphs or sub-topics covering the full narrative flow of the video)

### 🎯 Who Should Watch
(1-2 sentences identifying the target audience)
"""
    try:
        model = genai.GenerativeModel(model_name)
        res = model.generate_content(prompt)
        return res.text
    except Exception as e:
        return f"❌ Error generating summary: {str(e)}"

def ask_qa(question, d, history, model_name=DEFAULT_MODEL):
    if not st.session_state.google_api_key:
        return "⚠️ Please configure your Google API Key in the sidebar."

    if not d.get("has_transcript"):
        return "⚠️ I cannot answer questions accurately because no transcript was found for this video."

    genai.configure(api_key=st.session_state.google_api_key)
    sys_instruction = (
        f"You are a video Q&A assistant analyzing '{d['title']}' by {d['channel']}.\n"
        f"Answer questions strictly and accurately based on the video transcript below. "
        f"If the answer is not contained in the transcript, state clearly that it is not covered in the video.\n\n"
        f"Transcript:\n{d['transcript']}"
    )

    try:
        model = genai.GenerativeModel(model_name, system_instruction=sys_instruction)
        formatted_hist = []
        for m in history:
            formatted_hist.append({"role": m["role"], "parts": [m["content"]]})
        chat = model.start_chat(history=formatted_hist)
        resp = chat.send_message(question)
        return resp.text
    except Exception as e:
        return f"❌ Error retrieving answer: {str(e)}"


# ── Export Helpers ────────────────────────────────────────────────────────────
def to_markdown(d, s):
    return f"""# {d['title']}

- **Channel:** {d['channel']}
- **Published:** {parse_date(d['date'])}
- **Views:** {fmt_num(d['views'])} | **Likes:** {fmt_num(d['likes'])}
- **Duration:** {d['duration']}
- **Video Link:** https://youtu.be/{d['id']}

---

{s}

---
*Generated by YouTube Video Summarizer*
"""

def to_csv(d, s):
    clean_summary = s.replace('"', '""').replace('\n', ' ')
    lines = [
        '"Property","Value"',
        f'"Title","{d["title"]}"',
        f'"Channel","{d["channel"]}"',
        f'"Published","{parse_date(d["date"])}"',
        f'"Views","{fmt_num(d["views"])}"',
        f'"Likes","{fmt_num(d["likes"])}"',
        f'"Duration","{d["duration"]}"',
        f'"URL","https://youtu.be/{d["id"]}"',
        f'"Summary","{clean_summary}"'
    ]
    return "\n".join(lines)

def to_json(d, s):
    data = {
        "metadata": {
            "id": d["id"],
            "title": d["title"],
            "channel": d["channel"],
            "published_date": parse_date(d["date"]),
            "views": d["views"],
            "likes": d["likes"],
            "duration": d["duration"],
            "url": f"https://youtu.be/{d['id']}"
        },
        "summary": s,
        "transcript_preview": d["transcript"][:500] if d.get("transcript") else ""
    }
    return json.dumps(data, indent=2)

def to_txt(d, s):
    return f"TITLE: {d['title']}\nCHANNEL: {d['channel']}\nURL: https://youtu.be/{d['id']}\n\nSUMMARY:\n{s}\n"


# ── Modern Styling System (CSS) ───────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background-color: #0b0c10 !important;
    color: #e2e8f0 !important;
}

[data-testid="stHeader"] { background: transparent !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #12141a !important;
    border-right: 1px solid #1e222d !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #f1f5f9 !important;
    font-weight: 700 !important;
}

#MainMenu, footer { visibility: hidden; }
.block-container {
    max-width: 960px !important;
    padding-top: 2rem !important;
    padding-bottom: 3rem !important;
}

/* Header */
.app-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 2rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid #1e222d;
}
.app-logo-img {
    width: 48px;
    height: 48px;
    object-fit: contain;
    border-radius: 12px;
}
.app-header-title {
    font-size: 1.85rem;
    font-weight: 800;
    background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em;
    margin: 0;
}
.app-header-subtitle {
    color: #94a3b8;
    font-size: 0.92rem;
    margin-top: 2px;
}

/* Form Container */
div[data-testid="stForm"] {
    background: #161821 !important;
    border: 1px solid #262a36 !important;
    border-radius: 16px !important;
    padding: 24px !important;
    box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5) !important;
}
div[data-testid="stForm"] > div { border: none !important; }

div[data-baseweb="input"] {
    background-color: #0d0e12 !important;
    border: 1px solid #2a2f3d !important;
    border-radius: 10px !important;
    color: #f8fafc !important;
    transition: all 0.2s ease;
}
div[data-baseweb="input"]:focus-within {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2) !important;
}
div[data-baseweb="input"] input {
    color: #f8fafc !important;
    font-size: 0.95rem !important;
}

div[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 12px 24px !important;
    box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4) !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(79, 70, 229, 0.5) !important;
}

/* Video Metadata Card */
.video-card {
    display: flex;
    gap: 20px;
    background: #161821;
    border: 1px solid #242836;
    border-radius: 16px;
    padding: 20px;
    margin: 1.8rem 0;
    align-items: center;
}
@media (max-width: 640px) {
    .video-card { flex-direction: column; align-items: flex-start; }
}
.video-thumb-container {
    flex: 0 0 240px;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
.video-thumb-container img {
    width: 100%;
    height: auto;
    display: block;
    object-fit: cover;
}
.video-details { flex: 1; min-width: 0; }
.video-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #f8fafc;
    line-height: 1.4;
    margin-bottom: 12px;
}
.video-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}
.badge-pill {
    background: #0d0e12;
    border: 1px solid #262a38;
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 0.8rem;
    color: #94a3b8;
    display: flex;
    align-items: center;
    gap: 6px;
}
.badge-pill strong { color: #e2e8f0; font-weight: 600; }
.badge-pill a { color: #818cf8; text-decoration: none; font-weight: 600; }
.badge-pill a:hover { text-decoration: underline; }

/* Content Box */
.summary-container {
    background: #161821;
    border: 1px solid #242836;
    border-radius: 16px;
    padding: 28px;
    margin-top: 1rem;
    line-height: 1.75;
}
.summary-container h3 {
    color: #818cf8 !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    margin-top: 1.5rem !important;
    margin-bottom: 0.75rem !important;
    border-bottom: 1px solid #222634;
    padding-bottom: 6px;
}
.summary-container h3:first-child { margin-top: 0 !important; }
.summary-container p, .summary-container li {
    color: #cbd5e1 !important;
    font-size: 0.95rem !important;
}
.summary-container strong { color: #f1f5f9 !important; }

/* History Card */
.history-card {
    background: #0e1014;
    border: 1px solid #1e222e;
    border-radius: 10px;
    padding: 10px 12px;
    margin-bottom: 8px;
    transition: all 0.15s ease;
}
.history-card:hover { border-color: #6366f1; }
.history-title { font-size: 0.82rem; font-weight: 600; color: #e2e8f0; line-height: 1.3; }
.history-meta { font-size: 0.73rem; color: #64748b; margin-top: 4px; }

/* Transcript box */
.transcript-box {
    background: #0d0e12;
    border: 1px solid #222634;
    border-radius: 12px;
    padding: 18px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #cbd5e1;
    max-height: 420px;
    overflow-y: auto;
    white-space: pre-wrap;
    line-height: 1.6;
}

/* Quick prompt chips */
.chip-btn {
    display: inline-block;
    background: #1e2230;
    border: 1px solid #2d3346;
    color: #a5b4fc;
    border-radius: 20px;
    padding: 6px 14px;
    font-size: 0.8rem;
    font-weight: 500;
    margin: 4px;
    cursor: pointer;
    transition: all 0.2s ease;
}
.chip-btn:hover {
    background: #6366f1;
    color: #ffffff;
    border-color: #6366f1;
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: #0b0c10; }
::-webkit-scrollbar-thumb { background: #262a38; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #3b4156; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Configurations")
    
    # API Key Input
    api_key_val = st.text_input(
        "Google Gemini API Key",
        type="password",
        value=st.session_state.google_api_key,
        placeholder="AIzaSy...",
        help="Obtain a free API key from Google AI Studio (aistudio.google.com)"
    )
    if api_key_val != st.session_state.google_api_key:
        st.session_state.google_api_key = api_key_val
        st.rerun()

    if st.session_state.google_api_key:
        st.caption("🟢 **API Key Configured**")
    else:
        st.caption("🔴 **API Key Required** for Summaries & Q&A")

    # Model Selection
    model_choice = st.selectbox(
        "Gemini Model",
        options=AVAILABLE_MODELS,
        index=AVAILABLE_MODELS.index(st.session_state.selected_model) if st.session_state.selected_model in AVAILABLE_MODELS else 0
    )
    st.session_state.selected_model = model_choice

    st.markdown("---")
    st.markdown("### 📜 Video History")
    
    if not st.session_state.history:
        st.caption("No processed videos yet. Enter a YouTube link to get started.")
    else:
        for idx, entry in enumerate(reversed(st.session_state.history)):
            vd = entry["video_details"]
            st.markdown(
                f'<div class="history-card">'
                f'<div class="history-title">{vd["title"][:55]}...</div>'
                f'<div class="history-meta">📺 {vd["channel"]} • {vd["duration"]}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Load", key=f"hist_load_{idx}", use_container_width=True):
                    st.session_state.details = vd
                    st.session_state.summary = entry["summary"]
                    st.session_state.chat = []
                    st.rerun()
            with col2:
                if st.button("Delete", key=f"hist_del_{idx}", use_container_width=True):
                    st.session_state.history = [h for h in st.session_state.history if h["video_details"]["id"] != vd["id"]]
                    if st.session_state.details and st.session_state.details.get("id") == vd["id"]:
                        st.session_state.details = None
                        st.session_state.summary = None
                    st.rerun()

        st.markdown("---")
        if st.button("Clear All History", use_container_width=True):
            st.session_state.history = []
            st.session_state.details = None
            st.session_state.summary = None
            st.session_state.chat = []
            st.rerun()


# ── Main Header ───────────────────────────────────────────────────────────────
logo_b64 = b64_img("youtube.png")
logo_html = f'<img src="{logo_b64}" class="app-logo-img" />' if logo_b64 else '🎬'

st.markdown(f"""
<div class="app-header">
    {logo_html}
    <div>
        <h1 class="app-header-title">YouTube Video Summarizer</h1>
        <div class="app-header-subtitle">Transform long YouTube videos into concise structured summaries & interactive AI chats instantly.</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Input Form ────────────────────────────────────────────────────────────────
with st.form("summarize_form", clear_on_submit=False):
    col_input, col_depth = st.columns([3, 1.5])
    with col_input:
        url_input = st.text_input(
            "YouTube Video URL",
            placeholder="https://www.youtube.com/watch?v=...",
            label_visibility="collapsed"
        )
    with col_depth:
        depth_label = st.selectbox(
            "Summary Length",
            options=list(DEPTH_MAP.keys()),
            index=1,
            label_visibility="collapsed"
        )

    submit_btn = st.form_submit_button("⚡ Summarize Video", use_container_width=True)

if submit_btn:
    url_clean = url_input.strip()
    if not st.session_state.google_api_key:
        st.error("⚠️ Please enter your Google Gemini API Key in the sidebar before proceeding.")
    elif not url_clean:
        st.warning("Please paste a valid YouTube video URL first.")
    elif not valid_yt_url(url_clean):
        st.error("That URL does not appear to be a valid YouTube link. (Supported: watch?v=, youtu.be, shorts)")
    else:
        with st.spinner("Fetching video details and transcript..."):
            vdata = get_video(url_clean)

        if vdata:
            with st.spinner(f"Generating AI summary using {st.session_state.selected_model}..."):
                summary_text = summarize_video(
                    vdata,
                    word_target=DEPTH_MAP[depth_label],
                    model_name=st.session_state.selected_model
                )

            st.session_state.details = vdata
            st.session_state.summary = summary_text
            st.session_state.chat = []

            # Save to history if unique
            if not any(h["video_details"]["id"] == vdata["id"] for h in st.session_state.history):
                st.session_state.history.append({
                    "video_details": vdata,
                    "summary": summary_text
                })
            st.rerun()


# ── Results & Tabs ────────────────────────────────────────────────────────────
v_details = st.session_state.details
v_summary = st.session_state.summary

if v_details and v_summary:
    # Metadata Overview Header Card
    thumb_img = f'<div class="video-thumb-container"><img src="{v_details["thumb"]}" /></div>' if v_details.get("thumb") else ""
    yt_link = f'https://youtu.be/{v_details["id"]}'
    
    badges_html = "".join([
        f'<div class="badge-pill">📺 <strong>{v_details["channel"]}</strong></div>',
        f'<div class="badge-pill">🕒 <strong>{v_details["duration"]}</strong></div>',
        f'<div class="badge-pill">👁 <strong>{fmt_num(v_details["views"])}</strong> views</div>',
        f'<div class="badge-pill">❤️ <strong>{fmt_num(v_details["likes"])}</strong> likes</div>',
        f'<div class="badge-pill">📅 {parse_date(v_details["date"])}</div>',
        f'<div class="badge-pill">🔗 <a href="{yt_link}" target="_blank">Open on YouTube ↗</a></div>'
    ])

    st.markdown(
        f'<div class="video-card">'
        f'{thumb_img}'
        f'<div class="video-details">'
        f'<div class="video-title">{v_details["title"]}</div>'
        f'<div class="video-badges">{badges_html}</div>'
        f'</div></div>',
        unsafe_allow_html=True
    )

    # Main Tabbed Interface
    tab_summary, tab_chat, tab_transcript, tab_export = st.tabs([
        "📊 Summary",
        "💬 Q&A Chatbot",
        "📜 Full Transcript",
        "📥 Export Options"
    ])

    # ── Tab 1: Summary
    with tab_summary:
        st.markdown(f'<div class="summary-container">{v_summary}</div>', unsafe_allow_html=True)

    # ── Tab 2: Q&A Chatbot
    with tab_chat:
        st.markdown("#### 💬 Ask Questions About This Video")
        st.caption("Answers are dynamically synthesized from the transcript context.")

        # Display Existing Chat Messages
        for msg in st.session_state.chat:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Chat Input
        if question_prompt := st.chat_input("Ask a question about the video contents..."):
            st.session_state.chat.append({"role": "user", "content": question_prompt})
            with st.chat_message("user"):
                st.markdown(question_prompt)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing transcript..."):
                    answer_text = ask_qa(
                        question_prompt,
                        v_details,
                        st.session_state.chat[:-1],
                        model_name=st.session_state.selected_model
                    )
                st.markdown(answer_text)

            st.session_state.chat.append({"role": "model", "content": answer_text})

        if st.session_state.chat:
            if st.button("🗑️ Clear Chat History", key="clear_chat_btn"):
                st.session_state.chat = []
                st.rerun()

    # ── Tab 3: Full Transcript
    with tab_transcript:
        st.markdown("#### 📜 Video Transcript")
        if not v_details.get("has_transcript"):
            st.warning("No transcript was found for this video.")
        else:
            t_text = v_details.get("transcript", "")
            words_count = len(t_text.split())
            chars_count = len(t_text)

            st.caption(f"Total Words: **{words_count:,}** | Total Characters: **{chars_count:,}**")
            
            # Search Filter
            search_query = st.text_input("🔍 Filter transcript", placeholder="Type keywords to search...", key="transcript_search")
            if search_query:
                filtered_lines = [line for line in t_text.split("\n") if search_query.lower() in line.lower()]
                displayed_text = "\n".join(filtered_lines) if filtered_lines else f"No matches found for '{search_query}'."
            else:
                displayed_text = t_text

            st.markdown(f'<div class="transcript-box">{displayed_text}</div>', unsafe_allow_html=True)

    # ── Tab 4: Export Options
    with tab_export:
        st.markdown("#### 📥 Download & Export Summary")
        st.caption("Choose your preferred format to export video metadata and summary.")

        exp_col1, exp_col2, exp_col3, exp_col4 = st.columns(4)
        
        with exp_col1:
            st.download_button(
                "📄 Download Markdown",
                data=to_markdown(v_details, v_summary),
                file_name=f"summary_{v_details['id']}.md",
                mime="text/markdown",
                use_container_width=True
            )
        with exp_col2:
            st.download_button(
                "📊 Download CSV",
                data=to_csv(v_details, v_summary),
                file_name=f"summary_{v_details['id']}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with exp_col3:
            st.download_button(
                "🌐 Download JSON",
                data=to_json(v_details, v_summary),
                file_name=f"summary_{v_details['id']}.json",
                mime="application/json",
                use_container_width=True
            )
        with exp_col4:
            st.download_button(
                "📝 Download Text",
                data=to_txt(v_details, v_summary),
                file_name=f"summary_{v_details['id']}.txt",
                mime="text/plain",
                use_container_width=True
            )
