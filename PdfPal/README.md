# PdfPal 🤖

PdfPal is a simple and elegant Streamlit application that allows you to chat with your documents. Upload PDF files or provide URLs, and ask questions about their content using the power of Groq's LLM models and Hugging Face embeddings.

## ✨ Features

-   **Multi-Source Support**: Upload multiple PDF files and provide web URLs.
-   **Conversational Interface**: Ask questions in natural language and get detailed answers.
-   **Minimalist UI**: A clean WhatsApp-style interface for a seamless user experience.
-   **Powered by Groq**: Leverages Groq's fast language models for accurate responses.
-   **Organized Codebase**: Modular structure with separate files for better maintainability.

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

## 🚀 Getting Started

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

## 🛠️ Technical Details

- **Embeddings**: Hugging Face sentence-transformers
- **Vector Store**: FAISS for similarity search
- **LLM**: Groq's Llama models
- **UI Framework**: Streamlit
- **Text Processing**: PyMuPDF for PDFs, BeautifulSoup for web content

## 🐛 Troubleshooting

### Common Issues

1. **"The truth value of an array with more than one element is ambiguous"**
   - This has been fixed in the latest version with proper numpy array handling

2. **"cannot import name 'FAISS' from 'faiss'"**
   - Use `from langchain_community.vectorstores import FAISS` instead

3. **API Key Errors**
   - Ensure your `.env` file is properly configured
   - Check that API keys are valid and have sufficient permissions

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

If you encounter any issues or have questions, please open an issue on the repository.