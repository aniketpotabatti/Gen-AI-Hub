<div align="center">
  <img src="assets/pdfpal logo.png" width="50%"/>
</div>


PdfPal is an intuitive Retrieval-Augmented Generation (RAG) tool that lets you chat with your PDF files and web pages using your preferred AI models.

<!--https://github.com/user-attachments/assets/0dc3b36a-81fd-481c-8095-31192c6f52bc-->


## Features

- Multi-Source Input: Upload one or more PDF files and paste web page URLs to analyze simultaneously.
- Multi-Provider AI Support: Choose between Groq, OpenAI, Google Gemini, Anthropic, and Mistral AI.
- State-of-the-Art Models: Select modern models like Llama 3.3 70B, GPT-4o, Gemini 2.5 Flash, Claude 3.5 Sonnet, and Mistral Large.
- Flexible Authentication: Enter API keys directly in the sidebar UI or store them in a local `.env` file.
- Privacy & Local Indexing: Uses local FAISS vector storage and Hugging Face sentence-transformers embeddings for fast retrieval.

## How to Use PdfPal

1. Select Model & Provider: Open "API & Model Settings" in the sidebar, pick your preferred AI provider, select a model, and paste your API key.
2. Add Documents: Upload your PDF files or paste web URLs into the sidebar inputs.
3. Process Content: Click "Process Documents" to extract text and build the searchable index.
4. Chat: Ask questions in the chat box to receive answers grounded directly in your documents.
5. Reset: Click "Clear Chat & Data" anytime to purge the current session index and chat history.

## Quick Start

### 1. Clone & Install

```bash
git clone <repository-url>
cd PdfPal
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)

You can enter API keys in the app UI, or pre-configure them in a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
MISTRAL_API_KEY=your_mistral_api_key
HUGGINGFACE_API_KEY=your_huggingface_api_key
```

### 3. Run Application

```bash
streamlit run app.py
```

## Supported Providers & API Keys

Get API keys from official provider dashboards:

- Groq: https://console.groq.com
- OpenAI: https://platform.openai.com
- Google Gemini: https://aistudio.google.com
- Anthropic: https://console.anthropic.com
- Mistral AI: https://console.mistral.ai
- Hugging Face (Embeddings): https://huggingface.co/settings/tokens

## Project Structure

```text
PdfPal/
├── app.py          # Streamlit UI layout and event loop
├── config.py       # Centralized settings and provider model registry
├── llm.py          # Provider LLM builder strategies and FAISS manager
├── embeddings.py   # Hugging Face embeddings wrapper
├── utils.py        # PDF and URL text extraction utilities
└── requirements.txt# Project dependencies
```

## Quick Start

### 1. Installation

```bash
git clone <repository-url>
cd PdfPal
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory (optional if entering keys directly in the UI):

```env
GROQ_API_KEY=your_groq_key
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
ANTHROPIC_API_KEY=your_anthropic_key
MISTRAL_API_KEY=your_mistral_key
HUGGINGFACE_API_KEY=your_huggingface_key
```

### 3. Execution

```bash
streamlit run app.py
```

## Technical Stack

- Frontend: Streamlit
- Vector Store: FAISS
- Embeddings: Hugging Face `sentence-transformers/all-MiniLM-L6-v2`
- Framework: LangChain (`langchain-core`, `langchain-community`, `langchain-text-splitters`)

## License

MIT License
