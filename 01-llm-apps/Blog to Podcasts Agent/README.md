# 🎙️ Blog to Podcast Agent

A modern, AI-powered Streamlit web application that transforms any blog post or article into an engaging, AI-narrated audio podcast — built entirely with **free** tools and APIs.

Built with **Streamlit**, **Agno Agents**, **Groq**, **IBM Docling**, and **Google TTS (gTTS)**.

**Created:** Dec 2025

---

## ✨ Features

- **Sleek UI/UX:** A premium, fully responsive dark-themed glassmorphism interface.
- **Intelligent Document Extraction:** Uses IBM Docling to convert blog/article URLs into clean markdown content.
- **Smart Summarization:** Leverages Groq (Llama 3.3 70B) via an Agno Agent to digest the article into a conversational, podcast-ready script (under 2,000 characters).
- **Free Voice Synthesis:** Uses Google Text-to-Speech (`gTTS`) to generate a clear MP3 podcast — no paid TTS API required.
- **Listen & Download:** Instantly play the generated podcast in your browser or download it as an `.mp3` file.

---

## 🛠️ Technology Stack

| Role | Tool | Cost |
|------|------|------|
| UI | [Streamlit](https://streamlit.io/) | Free |
| Agent framework | [Agno](https://github.com/agno-agi/agno) | Free |
| LLM (summarization) | [Groq](https://console.groq.com/) — Llama 3.3 70B | Free tier |
| Web/doc extraction | [IBM Docling](https://github.com/DS4SD/docling) | Free / local |
| Text-to-Speech | [gTTS](https://gtts.readthedocs.io/) (Google TTS) | Free |

### What changed from the paid stack

| Before (paid / keys) | After (free alternatives) |
|----------------------|---------------------------|
| Google Gemini | **Groq API** |
| Firecrawl | **IBM Docling** |
| ElevenLabs TTS | **Google TTS (gTTS)** |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- A free **Groq API Key** from [console.groq.com](https://console.groq.com/)  
  (Docling and Google TTS do not require API keys.)

### Installation

1. **Navigate to the project directory:**
   ```bash
   cd "Different Approach - Blog to podcasts agent"
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running the App

1. Start the Streamlit server:
   ```bash
   streamlit run blog_to_podcasts_agent.py
   ```
2. Open the app in your browser (typically `http://localhost:8501`).
3. Enter your **Groq API key** in the left sidebar.
4. Paste a public blog URL into the main input field.
5. Click **"✨ Generate Podcast"** and wait for the pipeline to finish.

---

## 🔄 How it works

```
Blog URL
   │
   ▼
[1] Docling  →  clean markdown / text
   │
   ▼
[2] Agno + Groq  →  conversational podcast script (≤ 2000 chars)
   │
   ▼
[3] Google TTS (gTTS)  →  MP3 audio
   │
   ▼
Play in browser  ·  Download podcast.mp3
```

---

## ⚠️ Troubleshooting

- **Groq API errors / rate limits:**  
  Confirm the key is valid at [console.groq.com](https://console.groq.com/). Free tier has rate limits; wait a moment and retry if you hit them.

- **Docling scrape failures:**  
  Some sites block automated access or require login/paywall. Prefer public articles. Complex JS-only pages may return little content.

- **Google TTS / network errors:**  
  `gTTS` needs internet access (it calls Google’s free TTS endpoint). Check connectivity if audio generation fails.

- **Empty or short summaries:**  
  Very short pages or pages Docling cannot parse well may produce weak scripts. Try a longer, public article.

---

## 📄 License

This project is licensed under the MIT License.
