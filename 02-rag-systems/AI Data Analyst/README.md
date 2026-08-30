# AI Data Analyst

<p align="center">
  <img src="src/assets/AI Data Analyst logo.png" alt="AI Data Analyst Logo" width="200"/>
</p>

An AI-powered data analytics tool that lets you upload CSV or PDF files and ask questions in plain English. It returns answers, runs data analysis, and generates charts automatically.

Built with Python, Streamlit, Google Gemini, and ChromaDB.

---

## Features

- **CSV Analysis**: Upload a CSV, ask questions, and get answers backed by auto‑generated pandas code and Plotly charts.  
- **PDF Q&A**: Upload PDFs, and ask questions about their content using retrieval‑augmented generation (RAG).  
- **Smart Routing**: When both CSVs and PDFs are loaded, the AI decides which source to query based on your question.  
- **Auto Visualization**: Charts are generated automatically when the AI determines the result is visual.  
- **Insight Memory**: Notable Q&A results with charts are saved to an Insights tab for later reference.  

---

## Project Structure

```
src/
├── app.py                   # Streamlit dashboard (entry point)
├── assets/                  # Static assets (logo, images)
├── data/                    # Data storage (ChromaDB, processed files)
├── engine/
│   ├── ai_analyst.py           # Core AI engine (Gemini LLM)
│   ├── doc_processor.py        # PDF/CSV loading and text chunking
│   └── vector_store.py         # ChromaDB wrapper with Gemini embeddings
├── viz/
│   └── chart_generator.py      # Plotly chart generation from AI responses
└── utils/
    └── config.py               # Default settings
```

---

## Setup

**Requirements**: Python 3.10‑3.12, a Google Gemini API key.

1. **Clone the repository and create a virtual environment**

   ```bash
   git clone https://github.com/your-username/ai-data-analyst.git
   cd ai-data-analyst
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```

2. **Install dependencies**

   ```bash
   pip install -e .
   ```

3. **Run the app**

   ```bash
   streamlit run src/app.py
   ```

   When the app starts, enter your Google Gemini API key in the sidebar input field. The key is stored only in the session and is never written to disk.

4. Open <http://localhost:8501> in your browser.

---

## Configuration

All configurable values are defined in `src/utils/config.py` as sensible defaults. The only required input is the Google Gemini API key, which you provide via the Streamlit sidebar when the app launches.

| Variable               | Default                | Description                                          |
|------------------------|------------------------|------------------------------------------------------|
| `GEMINI_MODEL`         | `gemini-2.0-flash`     | LLM model for Q&A and analysis                       |
| `EMBEDDING_MODEL`      | `models/embedding-001` | Model for document embeddings                        |
| `CHROMA_PERSIST_DIR`   | `./data/chromadb`      | Where ChromaDB stores vectors                        |
| `CHUNK_SIZE`           | `500`                  | Text chunk size for document splitting               |
| `TOP_K`                | `5`                    | Number of chunks retrieved per query                 |

To change any of these values, edit `src/utils/config.py` directly.

---

## How It Works

1. **Upload** – Drop a CSV or PDF file into the sidebar.  
2. **Process** – CSVs are loaded into pandas; PDFs are chunked, embedded with Gemini, and stored in ChromaDB.  
3. **Ask** – Type a question in the chat input.  
4. **Analyze** – The AI routes your question to the appropriate handler (data analysis or document retrieval), generates an answer, and suggests a chart if applicable.  
5. **View** – Results appear in the chat with expandable source citations and the generated code. Charts are displayed automatically when relevant.

---

## Tech Stack

| Component      | Technology                                 |
|----------------|--------------------------------------------|
| LLM            | Google Gemini (`gemini-2.0-flash`)         |
| Embeddings     | Gemini `embedding-001`                     |
| Vector DB      | ChromaDB                                   |
| Dashboard      | Streamlit                                  |
| Charts         | Plotly                                     |
| Data Manipulation | pandas                                 |

---

## License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

---

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

1. Fork the repository.  
2. Create a feature branch (`git checkout -b feature/amazing-feature`).  
3. Commit your changes (`git commit -m 'Add amazing feature'`).  
4. Push to the branch (`git push origin feature/amazing-feature`).  
5. Open a Pull Request.

---

## Contact

For questions or feedback, please open an issue on GitHub.
