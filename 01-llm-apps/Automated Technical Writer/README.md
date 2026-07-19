# 🧠 Automated Technical Writer

> AI-powered technical documentation generator — paste your code, get production-quality docs in seconds.

![Tech Stack](https://img.shields.io/badge/Next.js-16-black?logo=next.js) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi) ![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?logo=langchain) ![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?logo=google)

##### Created: April 2025

---


## Features

- **Code-Aware Parsing** - Extracts functions, classes, imports, and docstrings via AST (never hallucinates API signatures)
- **AI Doc Architect** - Gemini plans the full documentation structure before writing a single word
- **Real-Time Streaming** - Watch documentation appear token by token via Server-Sent Events
- **Multi-Language** - Python, JavaScript, TypeScript, Go, Java, Rust
- **Multi-Format Export** - Download as Markdown (`.md`) or styled dark-mode HTML (`.html`)
- **3-Panel Editor** - Code input · Doc plan · Live preview, all in one view

---



## Quick Start



### Prerequisites

- **Node.js 18+** and **npm**
- **Python 3.11+**
- A **Google Gemini API key** — [get one free at Google AI Studio](https://aistudio.google.com/)



### 1. Clone & Configure

```bash
git clone <repo-url>
cd automated-technical-writer

# Copy the env template and fill in your API key
cp .env.example .env
```

Open `.env` and set your `GEMINI_API_KEY`.

### 2. Start the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# → API running at http://localhost:8000
# → Swagger docs at http://localhost:8000/docs
```

> ⚠️ **Important**: Always run `uvicorn` from inside the `backend/` directory, not the project root.



### 3. Start the Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```



### 4. Open the App

Navigate to **[http://localhost:3000/editor](http://localhost:3000/editor)**, paste your code, and click **Parse & Analyze**.

### 5. (Optional) Docker Compose

```bash
# From project root:
docker-compose up
```

---



## Tech Stack


| Layer        | Technology                                           |
| ------------ | ---------------------------------------------------- |
| Frontend     | Next.js 16 (App Router, Turbopack) + Tailwind CSS v4 |
| Backend      | FastAPI + Python 3.11                                |
| LLM          | Google Gemini 2.5 Flash via LangChain                |
| Code Parsing | Regex AST extractor (Tree-sitter optional)           |
| Streaming    | Server-Sent Events (SSE)                             |
| Export       | Markdown + styled HTML                               |


---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'feat: add my feature'`
4. Push and open a Pull Request

---
### License
   - MIT License
