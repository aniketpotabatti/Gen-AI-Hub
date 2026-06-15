# PdfPal

PdfPal is a Streamlit-based AI application that allows users to chat with PDFs and web pages. Users can upload multiple PDF files or provide URLs, and the app processes the content using embeddings and a RAG (Retrieval-Augmented Generation) pipeline to understand the documents. When a user asks a question, the system retrieves the most relevant information and generates accurate, context-aware answers using Groq-powered LLMs, making it easier to explore and extract insights from large documents.

https://github.com/user-attachments/assets/0dc3b36a-81fd-481c-8095-31192c6f52bc

## 🛠️ Technical Details

- **Embeddings**: Hugging Face sentence-transformers
- **Vector Store**: FAISS for similarity search
- **LLM**: Groq's Llama models
- **UI Framework**: Streamlit
- **Text Processing**: PyMuPDF for PDFs, BeautifulSoup for web content

## 🏗️ Project Structure

```
PdfPal/
├── app.py              # Main application interface (120 lines)
├── embeddings.py       # HuggingFace embeddings logic
├── utils.py            # PDF/URL processing and text extraction
├── llm.py              # LLM and vector store operations
├── requirements.txt    # Python dependencies
├── .env               # API keys (create this file)
└── README.md          # This file
```

### Prerequisites

- Python 3.8 or higher
- Virtual environment (recommended)

### Installation

1. **Clone the repository** (or download the files)
   ```bash
   git clone <repository-url>
   cd PdfPal
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\Activate.ps1  # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   HUGGINGFACE_API_KEY=your_huggingface_api_key_here
   ```

5. **Run the application**
   ```bash
   streamlit run app.py
   ```

## 🔑 API Keys Setup

1. **Groq API Key**:
   - Visit [Groq Console](https://console.groq.com/)
   - Sign up and get your API key
   - Add it to your `.env` file

2. **Hugging Face API Key**:
   - Visit [Hugging Face](https://huggingface.co/settings/tokens)
   - Create a new token
   - Add it to your `.env` file

## 📝 Usage

1. **Upload Documents**: Use the sidebar to upload PDF files or enter URLs
2. **Process**: Click "Process Documents" to extract and index the content
3. **Chat**: Ask questions about your documents in the chat interface
4. **Clear**: Use "Clear Data" to reset the chat and vector store

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
