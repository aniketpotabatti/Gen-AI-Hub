# SemanticSearchX

A modular Retrieval-Augmented Generation (RAG) system with hybrid retrieval, reranking, observability, and benchmarking capabilities.

## Features

- **Hybrid Retrieval**: Combines dense (vector) and sparse (BM25, exact match) search with reciprocal rank fusion.
- **Reranking**: Cross‑encoder and heuristic rerankers for improved relevance.
- **Adaptive Retrieval**: Dynamically selects the best pipeline per query.
- **Observability**: Prometheus metrics, structured logging, and OpenTelemetry tracing.
- **Benchmark Arena**: Compare multiple pipelines on Recall@K, MRR, nDCG, latency, and throughput.
- **Extensible**: Plug‑in architecture for vector stores, embeddings, and rerankers.

## Project Structure

```
SemanticSearchX/
├─ api/                 # FastAPI application
├─ ingestion/           # Document loaders and chunkers
├─ observability/       # Metrics, logging, tracing
├─ retrieval/           # Dense vector store abstractions
├─ sparse_retrieval/    # BM25 and exact‑match implementations
├─ hybrid_retrieval/    # Fusion logic
├─ reranking/           # Cross‑encoder and heuristic rerankers
├─ adaptive_retrieval/  # Adaptive pipeline selection
├─ evaluation/          # Benchmarking utilities (arena.py)
├─ tests/               # Unit and integration tests
└─ utils/               # Helper functions
```

## Installation

```bash
# Clone the repository
git clone https://github.com/your-org/SemanticSearchX.git
cd SemanticSearchX

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

1. **Start the API server**

```bash
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

2. **Interact with the API**

- Open Swagger UI: <http://localhost:8000/docs>
- Use the `/api/v1/index` endpoint to ingest documents.
- Query with `/api/v1/retrieve`.
- View the benchmark dashboard at `/arena`.

3. **Run the benchmark arena from CLI**

```bash
python -m evaluation.arena --help
```

## Running Tests

```bash
pytest tests/ -q
```

## Benchmark Arena

The arena compares six pipelines:

1. Dense (FAISS)  
2. BM25  
3. Hybrid (Dense + BM25)  
4. Hybrid + Reranker  
5. Adaptive (router)  
6. Adaptive + Reranker  

Metrics computed: Recall@K, MRR, nDCG, median/95th‑percentile latency, throughput (QPS).

Results can be exported as JSON or CSV.

## Configuration

Adjust settings via environment variables or edit `config/default.yaml` (if used). Key variables:

- `SEMANTICSEARCHX_EMBEDDING_MODEL`: SentenceTransformer model name.
- `SEMANTICSEARCHX_CACHE_SIZE`: LRU cache size for queries.
- `SEMANTICSEARCHX_LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR.

## Contributing

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Open a pull request.

Please follow the existing code style (ruff, black) and add tests for new functionality.

## License

MIT License – see the `LICENSE` file for details.

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/), [Sentence‑Transformers](https://www.sbert.net/), [FAISS](https://github.com/facebookresearch/faiss), [rank‑bm25](https://github.com/dorianbrown/rank_bm25), and [Prometheus client](https://github.com/prometheus/client_python).


