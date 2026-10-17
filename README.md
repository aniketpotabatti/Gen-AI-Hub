# Gen-AI-Hub

A curated collection of generative AI projects—LLM applications, retrieval-augmented generation (RAG) systems, fine-tuning experiments, and multimodal tools. Each project lives in its own folder with its own README, dependencies, and run instructions.

**Author:** [@aniketpotabatti](https://github.com/aniketpotabatti) · **License:** [MIT](LICENSE)

---

## Repository layout

Projects are grouped by theme. Open the folder for setup, architecture notes, and demos.

| Folder | Focus |
|--------|--------|
| [`01-llm-apps/`](01-llm-apps/) | Standalone LLM-powered apps (chat, summarization, codegen helpers) |
| [`02-rag-systems/`](02-rag-systems/) | Document Q&A, hybrid search, and knowledge retrieval |
| [`03-fine-tuning/`](03-fine-tuning/) | Custom model training (LoRA / QLoRA) |
| [`04-evaluation-multimodal/`](04-evaluation-multimodal/) | Vision, video, and VLM evaluation pipelines |

> **Note:** Some apps also appear at the repo root (`PdfPal/`, `Dishcovery/`, `NutriGuide/`) as earlier copies. Prefer the paths under the numbered folders above—they are the maintained locations.

---

## 01 — LLM applications

| Project | Description | Stack (high level) |
|---------|-------------|-------------------|
| [Automated Technical Writer](01-llm-apps/Automated%20Technical%20Writer/) | Paste code → production-style docs with streaming preview and Markdown/HTML export | Next.js, FastAPI, LangChain, Gemini |
| [Blog to Podcasts Agent](01-llm-apps/Blog%20to%20Podcasts%20Agent/) | Turn a blog URL into a short podcast script and MP3 | Streamlit, Agno, Groq, Docling, gTTS |
| [CodeSense](01-llm-apps/CodeSense/) | Real-time explain / review / suggest for code in the browser | React, Monaco, Express gateway, BYOK LLMs |
| [Data Science Project Reviewer](01-llm-apps/Data%20Science%20Project%20Reviewer/) | Score a public GitHub ML repo across organization, metrics, deployment, and more | Streamlit, Gemini |
| [Dishcovery](01-llm-apps/Dishcovery/) | Ingredient-based recipe generation with dietary filters and PDF export | Streamlit, Gemini |
| [End-to-End Youtube Video Summarizer](01-llm-apps/End-to-End%20Youtube%20Video%20Summarizer/) | Summarize YouTube videos, Q&A on transcripts, export summaries | Streamlit, Gemini |
| [OpsAgent](01-llm-apps/OpsAgent/) | Analyze JSON system alerts → severity + summary with history | Streamlit, OpenAI / Gemini |

---

## 02 — RAG & knowledge systems

| Project | Description | Stack (high level) |
|---------|-------------|-------------------|
| [AI Data Analyst](02-rag-systems/AI%20Data%20Analyst/) | Ask questions in plain English over CSVs and PDFs; auto charts and insight memory | Streamlit, ChromaDB, Gemini |
| [AI Research Explainer](02-rag-systems/AI%20Reserch%20Explainer/) | PDF papers → study guides, flashcards, quizzes, ELI5 | Streamlit, PyMuPDF, Gemini |
| [PdfPal](02-rag-systems/PdfPal/) | Chat with PDFs and web pages; multi-provider LLM support | Streamlit, FAISS, sentence-transformers |
| [SemanticSearchX](02-rag-systems/SemanticSearchX/) | Modular RAG with hybrid retrieval, reranking, benchmarks, and observability | FastAPI, dense + sparse fusion, Prometheus |
| [AI-powered finance report analyst](02-rag-systems/AI-powered%20finance%20report%20analyst/) | *Placeholder — README and implementation coming soon* | — |
| [LLM Youtube Mixtape Creator](02-rag-systems/LLM%20Youtube%20Mixtape%20Creator/) | *Placeholder — README and implementation coming soon* | — |

---

## 03 — Fine-tuning

| Project | Description | Stack (high level) |
|---------|-------------|-------------------|
| [Customer Support Bot](03-fine-tuning/Customer%20Support%20Bot/) | QLoRA fine-tune on Bitext support data; Gradio chat UI | Hugging Face Transformers, TRL, PEFT, Gradio |

---

## 04 — Evaluation & multimodal

| Project | Description | Stack (high level) |
|---------|-------------|-------------------|
| [Image Caption Generator](04-evaluation-multimodal/Image%20Caption%20Generator/) | BLIP + GPT-2 captions; API, CLI, and Streamlit UI | FastAPI, Streamlit, LoRA style control |
| [NutriGuide](04-evaluation-multimodal/NutriGuide/) | Food photo → calories, macros, health rating, diet tips | Streamlit, Gemini multimodal |
| [Project Tagger](04-evaluation-multimodal/Project%20Tagger/) | Structured product tags from image + text (Gemini, GPT-4o, Claude, LLaVA) | Pydantic validation, batch eval, Streamlit |
| [VidLens AI](04-evaluation-multimodal/VidLens%20AI/) | Video Q&A with Gemini plus live DuckDuckGo web grounding | Streamlit, Gemini 2.5 |

---

## Getting started

1. **Pick a project** from the tables above and open its folder.
2. **Read that project’s `README.md`** for prerequisites, API keys, and run commands.
3. **Use a virtual environment** per project (`python -m venv .venv` or the stack’s documented setup).
4. **Never commit secrets** — use `.env` or session-only keys as each README describes.

Many apps need a **Google Gemini**, **Groq**, or **OpenAI** API key. Free tiers are documented in individual project READMEs where applicable.

---

## Contributing

This hub is a portfolio monorepo. To extend it:

- Add new work under the matching numbered category (or propose a new category folder).
- Keep each project self-contained (`requirements.txt`, README, `.gitignore`).
- Follow existing naming and README patterns in sibling projects.

---

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting. Do not open issues with live API keys or private data.
