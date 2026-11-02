<p align="center">
  <img src="src/assets/AI Data Analyst logo.png" alt="AI Data Analyst Logo" width="220"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10--3.12-3776AB?logo=python&logoColor=white" alt="Python 3.10–3.12" />
  <img src="https://img.shields.io/badge/Streamlit-1.51+-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/Gemini%20AI-Google-4285F4?logo=google&logoColor=white" alt="Gemini AI" />
  <img src="https://img.shields.io/badge/Charts-Plotly-3F4F75?logo=plotly&logoColor=white" alt="Plotly" />
</p>

An AI-powered analytics workspace for asking questions about CSV datasets and PDF documents in plain English. Upload files, inspect an automatic data profile, and explore answers with generated pandas code, citations, and charts.

## Features

- **Multiple file uploads:** Upload several CSV and PDF files together.
- **CSV analysis:** Ask questions about an individual dataset or choose `All datasets` to analyze them together. The combined view aligns columns by name and adds a `_source_file` column.
- **Automatic data overview:** Each loaded dataset shows row, column, missing-cell, and duplicate-row counts, a data preview, and a chart selected for the available data.
- **Analysis results and findings:** Review numeric summaries, column quality, potential outliers, and plain-language observations.
- **Dataset-specific question starters:** Click prompts based on the selected dataset's columns below the dataset selector.
- **Adaptive charts:** The overview can create time trends, category comparisons, numeric scatter plots, numeric distributions, or category-frequency charts. Analysis charts use a shared dark theme.
- **PDF question answering:** PDFs are indexed for retrieval-augmented generation (RAG), with source references included in answers.
- **CSV and PDF routing:** When both kinds of files are loaded, questions are routed to CSV analysis or PDF search based on their content.
- **Generated analysis code:** CSV answers include the pandas code used to calculate the result.

## Requirements

- Python 3.10–3.12
- A Google Gemini API key for analysis and PDF indexing

## Setup

Create and activate a virtual environment from the project directory:

```bash
python -m venv .venv

# Windows PowerShell
.venv/Scripts/Activate.ps1

# macOS or Linux
source .venv/bin/activate
```

Install the project:

```bash
pip install -e .
```

Start the app:

```bash
streamlit run src/app.py
```

Open <http://localhost:8501>, then enter your Gemini API key in the sidebar. The key is held in the Streamlit session and is not written to the project files.

## Using the app

1. Enter your Gemini API key in the sidebar.
2. Upload one or more `.csv` and `.pdf` files.
3. Review the data preview, analysis results, findings, and generated chart.
4. If you uploaded multiple CSVs, use **Dataset to analyze** to select one file or **All datasets**.
5. Use the dataset-specific suggested questions below the selector, or ask in Chat.

The combined CSV view appends rows and aligns columns by name. If files have different schemas, missing values will appear where a file does not contain a column. The `_source_file` column identifies each row's originating file.

CSV data is held in the current app session. PDF text embeddings are stored in the local ChromaDB directory configured in `src/utils/config.py`. **Reset Data** clears the loaded CSVs and chat. When an API key is configured, it also clears the indexed document collection.

## Configuration

Defaults are defined in `src/utils/config.py`:

| Setting | Default | Purpose |
|---|---|---|
| `gemini_model` | `gemini-3.5-flash` | Gemini model used for answers and analysis |
| `embedding_model` | `gemini-embedding-001` | Model used to embed PDF text and queries |
| `embedding_dimension` | `768` | Embedding vector dimension |
| `chroma_persist_dir` | `data/chromadb` | Local ChromaDB storage directory |
| `chroma_collection` | `documents` | ChromaDB collection name |
| `chunk_size` | `500` | PDF text chunk size |
| `chunk_overlap` | `50` | Overlap between adjacent PDF chunks |
| `top_k` | `5` | Maximum number of PDF chunks retrieved per query |

Edit `src/utils/config.py` to change these defaults.

## Project structure

```text
AI Data Analyst/
├── .streamlit/
│   └── config.toml
├── data/
│   └── chromadb/                 # Local PDF embeddings
├── src/
│   ├── app.py                    # Streamlit interface and upload workflow
│   ├── assets/                   # App logo and static assets
│   ├── engine/
│   │   ├── ai_analyst.py         # Gemini routing and pandas analysis
│   │   ├── data_profiler.py      # Local dataset profile and question suggestions
│   │   ├── doc_processor.py      # CSV/PDF loading and PDF chunking
│   │   └── vector_store.py       # ChromaDB and Gemini embeddings
│   ├── utils/
│   │   └── config.py             # Application defaults
│   └── viz/
│       └── chart_generator.py    # Automatic and analysis chart generation
├── tests/
│   └── test_engine.py
├── pyproject.toml
└── README.md
```

## Development

Install development dependencies and run the test suite:

```bash
pip install -e ".[dev]"
pytest
```

## License

This project is licensed under the [MIT License](../../LICENSE) at the repository root.
