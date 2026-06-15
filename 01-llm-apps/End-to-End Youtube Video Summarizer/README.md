# <img src="youtube.png" width="32px" height="35px"> YT Summarizer</img>

Paste any YouTube URL — get a clean AI-powered summary instantly. Built with Streamlit and Google Gemini.

## Video Overview


https://github.com/user-attachments/assets/19abbc0d-c0e7-45d2-81c3-ee66eabf18c3


## ✨ Features

- **AI Summaries** — Generates structured summaries (topics, key takeaways, detailed summary, audience fit) using Google Gemini
- **Adjustable Depth** — Choose between Quick (~100 words), Standard (~300), or Deep Dive (~600)
- **Q&A Chat** — Ask follow-up questions about the video, answered from the transcript
- **Video Metadata** — Displays thumbnail, channel, views, likes, duration, publish date, and language
- **Export** — Download summaries as Markdown or CSV
- **Session History** — Sidebar keeps track of previously summarized videos for quick reload
- **Multi-Language** — Automatically detects and fetches the best available transcript language
- **Dark Minimal UI** — Custom-styled dark theme with Inter font and indigo accents

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone <repository-url>
cd End-to-End-Youtube-Video-Summarizer
pip install -r requirements.txt
```

### 2. Add your API key

Create a `.env` file:

```
GOOGLE_API_KEY=your_google_api_key_here
```

Optionally set a custom model:

```
GEMINI_MODEL=gemini-2.5-flash
```

### 3. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## 📦 Tech Stack

| Component | Library |
|-----------|---------|
| UI | Streamlit |
| AI | Google Gemini (`google-generativeai`) |
| Transcripts | `youtube-transcript-api` |
| Metadata | `yt-dlp` |
| Config | `python-dotenv` |

## 📁 Project Structure

```
├── app.py                 # Single-file app (UI, logic, CSS — ~265 lines)
├── requirements.txt       # Pinned dependencies
├── .env                   # API key (not committed)
├── .streamlit/
│   └── config.toml        # Streamlit theme config
├── youtube.png            # App logo
├── .gitignore
└── README.md
```

## 🛠 Troubleshooting

| Problem | Solution |
|---------|----------|
| `GOOGLE_API_KEY missing` | Create a `.env` file with your key |
| `No transcript available` | The video may not have captions — try a different video |
| Module not found | Run `pip install -r requirements.txt` |

## 📄 License


This project is licensed under the [MIT License](LICENSE).
