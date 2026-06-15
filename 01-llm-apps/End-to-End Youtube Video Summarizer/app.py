import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
import os, re, base64
import yt_dlp
from datetime import datetime
from youtube_transcript_api import YouTubeTranscriptApi

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(layout="wide", page_title="YT Summarizer", page_icon="🎬")

load_dotenv()
_api_key = os.getenv("GOOGLE_API_KEY")
if not _api_key:
    st.error("⚠️ `GOOGLE_API_KEY` missing. Add it to your `.env` file.")
    st.stop()
genai.configure(api_key=_api_key)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_CHARS = 30_000
DEPTH = {"Quick (~100 words)": 100, "Standard (~300 words)": 300, "Deep Dive (~600 words)": 600}

for k, v in {"details": None, "summary": None, "chat": [], "history": []}.items():
    st.session_state.setdefault(k, v)


# ── Helpers ───────────────────────────────────────────────────────────────────
def b64_img(path):
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"

def fmt(val):
    try: return f"{int(val):,}"
    except: return str(val) if val else "—"

def parse_date(raw):
    try: return datetime.strptime(raw, "%Y%m%d").strftime("%b %d, %Y")
    except: return raw or "—"

def valid_yt_url(url):
    return bool(re.match(r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+", url))

def md_to_html(md):
    """Convert simple markdown (### headings, - bullets, **bold**) to HTML."""
    bold = lambda t: re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", t)
    lines, out, in_ul = md.split("\n"), [], False
    for line in lines:
        line = line.strip()
        if not line:
            if in_ul: out.append("</ul>"); in_ul = False
        elif line.startswith("### "):
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(f"<h3>{bold(line[4:])}</h3>")
        elif line[:2] in ("- ", "* "):
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append(f"<li>{bold(line[2:])}</li>")
        else:
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(f"<p>{bold(line)}</p>")
    if in_ul: out.append("</ul>")
    return "\n".join(out)


# ── Data fetching (cached 1hr) ────────────────────────────────────────────────
_ytt = YouTubeTranscriptApi()

@st.cache_data(ttl=3600, show_spinner=False)
def get_video(url):
    try:
        vid = re.search(r"(?:v=|/)([0-9A-Za-z_-]{11})", url)
        if not vid: return None
        video_id = vid.group(1)

        opts = {"skip_download": True, "quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        transcript, lang = "", "en"
        try:
            tl = _ytt.list(video_id)
            preferred = ["en"] + [t.language_code for t in tl]
            t = tl.find_transcript(preferred)
            lang = t.language_code
            transcript = " ".join(s.text for s in t.fetch()).strip()
        except Exception:
            pass

        if len(transcript) > MAX_CHARS:
            transcript = transcript[:MAX_CHARS] + "\n\n[truncated]"

        return {
            "id": video_id, "lang": lang,
            "title": info.get("title", "Unknown"),
            "channel": info.get("uploader", "Unknown"),
            "thumb": info.get("thumbnail", ""),
            "date": info.get("upload_date", ""),
            "views": info.get("view_count"),
            "likes": info.get("like_count"),
            "duration": info.get("duration_string", "—"),
            "transcript": transcript or "No transcript available.",
        }
    except yt_dlp.utils.DownloadError as e:
        st.error(f"Could not fetch video: {e}"); return None
    except Exception as e:
        st.error(f"Unexpected error: {e}"); return None


# ── AI ────────────────────────────────────────────────────────────────────────
def summarize(d, words=300):
    prompt = f"""Summarize this YouTube video clearly and concisely.
Target ~{words} words for the detailed section.

Title: {d['title']} | Channel: {d['channel']}

Transcript:
{d['transcript']}

Respond in this exact markdown format:
### 🗂 Topics
(bullet points)

### 💡 Key Takeaways
(3-5 bullets)

### 📖 Summary
(~{words} word paragraph)

### 👥 Who Should Watch
(1-2 sentences)
"""
    return genai.GenerativeModel(MODEL).generate_content(prompt).text

def ask(question, d, history):
    ctx = f"Video: {d['title']} by {d['channel']}\n\nTranscript:\n{d['transcript']}"
    model = genai.GenerativeModel(MODEL, system_instruction=f"Answer based ONLY on this video transcript. Say if something isn't covered.\n\n{ctx}")
    chat = model.start_chat(history=[{"role": m["role"], "parts": [m["content"]]} for m in history])
    return chat.send_message(question).text


# ── Exports ───────────────────────────────────────────────────────────────────
def to_markdown(d, s):
    return f"# {d['title']}\n\n**Channel:** {d['channel']}  \n**Published:** {parse_date(d['date'])}  \n**Views:** {fmt(d['views'])} | **Likes:** {fmt(d['likes'])}  \n**URL:** https://youtu.be/{d['id']}\n\n---\n\n{s}\n\n---\n*YT Summarizer*"

def to_csv(d, s):
    rows = [("Title",d["title"]),("Channel",d["channel"]),("Published",parse_date(d["date"])),
            ("Views",fmt(d["views"])),("Likes",fmt(d["likes"])),("Duration",d["duration"]),
            ("URL",f"https://youtu.be/{d['id']}"),("Summary",s.replace("\n"," "))]
    return "\n".join(f'"{k}","{v}"' for k, v in rows)


# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
*, html, body { font-family: 'Inter', sans-serif !important; }

[data-testid="stAppViewContainer"] { background: #0f0f11 !important; }
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { background: #0a0a0c !important; border-right: 1px solid #1e1e24 !important; }
#MainMenu, footer, header { visibility: hidden; }

.block-container { max-width: 860px !important; padding: 2rem 1.5rem !important; }

/* Header */
.app-header { margin-bottom: 2.5rem; }
.app-logo { width: 40px; height: 40px; object-fit: contain; vertical-align: middle; margin-right: 12px; }
.app-title { font-size: 1.6rem; font-weight: 700; color: #f0f0f5; letter-spacing: -0.3px; }
.app-subtitle { color: #5c5c6e; font-size: 0.85rem; margin-top: 6px; }

/* Form */
div[data-testid="stForm"] { background: #161619 !important; border: 1px solid #222228 !important; border-radius: 14px !important; padding: 20px !important; box-shadow: none !important; }
div[data-testid="stForm"] > div { border: none !important; }
div[data-baseweb="input"] { background: #0f0f11 !important; border: 1px solid #2a2a32 !important; border-radius: 10px !important; transition: border-color 0.2s; }
div[data-baseweb="input"]:focus-within { border-color: #7c6af7 !important; box-shadow: 0 0 0 3px rgba(124,106,247,0.12) !important; }
div[data-baseweb="input"] input { color: #f0f0f5 !important; }
div[data-testid="stForm"] button { background: #7c6af7 !important; color: #fff !important; font-weight: 600 !important; font-size: 0.9rem !important; border: none !important; border-radius: 10px !important; padding: 10px 20px !important; width: 100% !important; transition: background 0.2s, transform 0.15s !important; box-shadow: 0 2px 12px rgba(124,106,247,0.25) !important; }
div[data-testid="stForm"] button:hover { background: #6b59e8 !important; transform: translateY(-1px) !important; }
div[data-testid="stForm"] label p { color: #7a7a8e !important; font-size: 0.82rem !important; font-weight: 500 !important; }

/* Video card */
.vcard { display: flex; gap: 20px; align-items: flex-start; flex-wrap: wrap; background: #161619; border: 1px solid #1e1e24; border-radius: 16px; padding: 20px; margin: 1.5rem 0 1rem; }
.vcard-thumb { flex: 0 0 220px; border-radius: 10px; overflow: hidden; }
.vcard-thumb img { width: 100%; display: block; }
.vcard-info { flex: 1; min-width: 220px; }
.vcard-title { font-size: 1.05rem; font-weight: 600; color: #f0f0f5; line-height: 1.45; margin-bottom: 14px; }
.vcard-stats { display: flex; flex-wrap: wrap; gap: 8px; }
.stat-pill { background: #0f0f11; border: 1px solid #222228; border-radius: 8px; padding: 5px 12px; font-size: 0.78rem; color: #8a8a9e; display: flex; align-items: center; gap: 5px; }
.stat-pill strong { color: #c8c8d8; font-weight: 500; }

/* Summary */
.section-label { font-size: 0.7rem; font-weight: 600; letter-spacing: 0.08em; color: #7c6af7; text-transform: uppercase; margin-bottom: 10px; }
.summary-box { background: #161619; border: 1px solid #1e1e24; border-radius: 16px; padding: 24px; margin-bottom: 1rem; }
.summary-box h3 { color: #a89df5 !important; font-size: 0.95rem !important; font-weight: 600 !important; margin-top: 1.2rem !important; margin-bottom: 0.5rem !important; }
.summary-box p, .summary-box li { color: #c0c0cc !important; line-height: 1.8 !important; font-size: 0.9rem !important; }
.summary-box li { margin-bottom: 4px !important; }
.summary-box strong { color: #a89df5 !important; }

/* Exports */
[data-testid="stDownloadButton"] button { background: #161619 !important; border: 1px solid #2a2a32 !important; color: #8a8a9e !important; border-radius: 8px !important; font-size: 0.82rem !important; font-weight: 500 !important; transition: all 0.2s !important; }
[data-testid="stDownloadButton"] button:hover { border-color: #7c6af7 !important; color: #a89df5 !important; background: #1a1826 !important; }

/* Q&A */
.qa-header { font-size: 0.85rem; font-weight: 600; color: #f0f0f5; margin: 1.5rem 0 0.5rem; }
.qa-note { font-size: 0.78rem; color: #5c5c6e; margin-bottom: 1rem; }

/* History */
.hist-item { border-radius: 10px; padding: 10px 12px; margin-bottom: 6px; background: #111113; border: 1px solid #1c1c22; cursor: pointer; transition: border-color 0.15s; }
.hist-item:hover { border-color: #7c6af7; }
.hist-title { font-size: 0.8rem; font-weight: 500; color: #d0d0de; line-height: 1.3; }
.hist-ch { font-size: 0.72rem; color: #5c5c6e; margin-top: 2px; }

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0f0f11; }
::-webkit-scrollbar-thumb { background: #2a2a36; border-radius: 3px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### History")
    if not st.session_state.history:
        st.markdown('<p style="color:#3a3a4e;font-size:0.82rem;padding:6px 0;">Nothing yet — summarize a video to start.</p>', unsafe_allow_html=True)
    else:
        for i, entry in enumerate(reversed(st.session_state.history)):
            d = entry["video_details"]
            st.markdown(f'<div class="hist-item"><div class="hist-title">{d["title"]}</div><div class="hist-ch">{d["channel"]}</div></div>', unsafe_allow_html=True)
            if st.button("Load", key=f"h{i}", use_container_width=True):
                st.session_state.details = d
                st.session_state.summary = entry["summary"]
                st.session_state.chat = []
                st.rerun()
        st.markdown("---")
        if st.button("Clear history", use_container_width=True):
            st.session_state.history = []
            st.rerun()


# ── Header ────────────────────────────────────────────────────────────────────
logo = b64_img("youtube.png")
logo_tag = f'<img src="{logo}" class="app-logo" />' if logo else "🎬"
st.markdown(f"""
<div class="app-header">
  <div style="display:flex;align-items:center;gap:4px;">
    {logo_tag}
    <span class="app-title">YT Summarizer</span>
  </div>
  <div class="app-subtitle">Paste any YouTube URL — get a clean AI summary instantly.</div>
</div>
""", unsafe_allow_html=True)


# ── Input ─────────────────────────────────────────────────────────────────────
with st.form("main"):
    url_input = st.text_input("URL", placeholder="https://www.youtube.com/watch?v=...", label_visibility="collapsed")
    depth = st.select_slider("Depth", options=list(DEPTH.keys()), value="Standard (~300 words)", label_visibility="collapsed")
    submitted = st.form_submit_button("Summarize →")

if submitted:
    url = url_input.strip()
    if not url:
        st.warning("Paste a YouTube URL first.")
    elif not valid_yt_url(url):
        st.error("That doesn't look like a valid YouTube URL.")
    else:
        with st.spinner("Fetching video…"):
            d = get_video(url)
        if d:
            with st.spinner("Generating summary…"):
                s = summarize(d, DEPTH[depth])
            st.session_state.details, st.session_state.summary, st.session_state.chat = d, s, []
            if not any(e["video_details"]["id"] == d["id"] for e in st.session_state.history):
                st.session_state.history.append({"video_details": d, "summary": s})
            st.rerun()


# ── Results ───────────────────────────────────────────────────────────────────
d, s = st.session_state.details, st.session_state.summary
if d and s:
    # Video card
    thumb = f'<div class="vcard-thumb"><img src="{d["thumb"]}" /></div>' if d.get("thumb") else ""
    pills = "".join(f'<div class="stat-pill">{x}</div>' for x in [
        f'📺 <strong>{d["channel"]}</strong>',
        f'👁 <strong>{fmt(d["views"])}</strong> views',
        f'❤️ <strong>{fmt(d["likes"])}</strong> likes',
        f'🕒 {d["duration"]}',
        f'📅 {parse_date(d["date"])}',
        f'🌐 {d["lang"].upper()}',
    ])
    st.markdown(f'<div class="vcard">{thumb}<div class="vcard-info"><div class="vcard-title">{d["title"]}</div><div class="vcard-stats">{pills}</div></div></div>', unsafe_allow_html=True)

    # Summary
    st.markdown('<div class="section-label">AI Summary</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="summary-box">{md_to_html(s)}</div>', unsafe_allow_html=True)

    # Exports
    c1, c2, _ = st.columns([1, 1, 3])
    with c1: st.download_button("↓ Markdown", to_markdown(d, s), f"{d['id']}.md", "text/markdown", use_container_width=True)
    with c2: st.download_button("↓ CSV", to_csv(d, s), f"{d['id']}.csv", "text/csv", use_container_width=True)

    # Q&A
    st.markdown('<div class="qa-header">💬 Ask about this video</div>', unsafe_allow_html=True)
    st.markdown('<div class="qa-note">Questions are answered using the video transcript only.</div>', unsafe_allow_html=True)

    for m in st.session_state.chat:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if q := st.chat_input("Ask a question…"):
        st.session_state.chat.append({"role": "user", "content": q})
        with st.chat_message("user"): st.markdown(q)
        with st.chat_message("assistant"):
            with st.spinner(""):
                ans = ask(q, d, st.session_state.chat[:-1])
            st.markdown(ans)
        st.session_state.chat.append({"role": "model", "content": ans})

    if st.session_state.chat and st.button("Clear chat", key="cc"):
        st.session_state.chat = []
        st.rerun()
