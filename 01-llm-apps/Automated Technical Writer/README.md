# AutoWriter AI

> AI-powered technical documentation generator — paste your code, get production-quality docs in seconds.

![Nodejs](https://img.shields.io/badge/Next.js-16-black?logo=next.js) 
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi) 
![LangChain](https://img.shields.io/badge/LangChain-0.3-1C3C3C?logo=langchain) 
![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?logo=google)

**Created:** April 2025

---

## Features

- **Editor Settings & Functionalities Panel** — A dedicated top-right ⚙️ Settings panel to configure personal Google Gemini or OpenAI API keys, switch models (`gemini-2.5-flash`, `gemini-1.5-pro`, `gpt-4o`, `gpt-4o-mini`), customize documentation tone (Balanced, Concise, Tutorial, In-depth), and choose target audience level. Stored safely in local browser storage.
- **Instant Code Presets** — 1-click sample templates (FastAPI Auth Service, TypeScript LRU Cache) to immediately test and experience the generation pipeline.
- **Code-Aware Parsing** — Extracts functions, classes, imports, and docstrings via AST (never hallucinates API signatures).
- **AI Doc Architect** — Plans the complete documentation structure and sections before writing a single word.
- **Real-Time Streaming** — Watch documentation appear token by token via Server-Sent Events (SSE).
- **Multi-Language Support** — Python, JavaScript, TypeScript, Go, Java, Rust.
- **Multi-Format Export** — Instant 1-click copy or download as Markdown (`.md`) and dark-mode styled HTML (`.html`).
- **3-Panel Glassmorphic Studio** — Code input · Interactive Doc plan · Live preview in a cohesive dark theme.

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


## Project Structure

```
automated-technical-writer/
├── .gitignore
├── docker-compose.yml
├── package.json              # Root proxy scripts (npm run dev → frontend)
│
├── backend/                  # FastAPI application
│   ├── app/
│   │   ├── api/routes/       # parse, plan, write, export endpoints
│   │   ├── core/             # Config (pydantic-settings)
│   │   ├── llm/              # LangChain chains + prompts
│   │   ├── models/           # Pydantic schemas
│   │   └── services/         # Code parser (regex AST)
│   ├── Dockerfile
│   └── requirements.txt
│
└── frontend/                 # Next.js application
    └── src/
        ├── app/              # Pages (/, /editor)
        ├── components/       # CodeUploader, DocArchitecture, StreamingOutput, ExportButton
        └── lib/              # API client (api.ts)
```

---

## 🚀 Future Improvements & Production Readiness Roadmap

To transition AutoWriter AI from MVP to an enterprise-grade, production-ready system:

### 1. 🛡️ Security & Authentication
- **User Authentication**: Implement OAuth2 & SSO (e.g., Clerk, Auth.js, or Supabase Auth) for protected workspaces and user sessions.
- **Enterprise Key Vault**: Provide backend encryption for stored API keys (AWS KMS / HashiCorp Vault) rather than relying strictly on browser storage for shared team plans.
- **Rate Limiting & Abuse Prevention**: Implement Redis-backed token bucket rate limiters (`slowapi` or Upstash Redis) to prevent LLM quota exhaustion and DDoS attacks.

### 2. 🧬 Style DNA & Custom Brand Guidelines
- **RAG Style Learning**: Ingest existing documentation repositories or brand voice guides (via ChromaDB/Pinecone) to match tone, formatting conventions, and naming styles.
- **Audience & Tone Switcher**: Dynamic prompt adjustments to generate docs targeted at **Beginners**, **Intermediate Engineers**, or **System Architects** on demand.

### 3. 🔄 Living Docs & Automated CI/CD
- **GitHub Webhook Integration**: Automatically listen to PRs/merges, inspect `git diff`, and trigger incremental re-generation for only modified modules.
- **Automated Pull Request Creation**: Open automatic PRs titled `docs: sync documentation with commit <hash>` directly on GitHub or GitLab.

### 4. 🌳 Tree-Sitter Universal AST
- **Deep Language Support**: Upgrade the lightweight regex AST extractor to compiled `tree-sitter` bindings for full multi-file dependency trees and cross-file symbol resolution.
- **Multi-File Workspace Parsing**: Support uploading an entire repository (zip or GitHub link) and building a dependency graph before writing the docs.

### 5. ☁️ Cloud & Platform Integrations
- **Export Targets**: Direct 1-click publishing to Notion, Confluence, Mintlify, GitBook, and Docusaurus.
- **Doc Health & Coverage Dashboard**: Visual analysis showing which functions/endpoints are missing documentation or have broken example snippets.

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'feat: add my feature'`
4. Push and open a Pull Request

---



## License

This project is licensed under the [MIT License](../../LICENSE) at the repository root.
