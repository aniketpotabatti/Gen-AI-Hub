# Multimodal Product Tagger

Generate structured product tags from an image and text description using Vision-Language Models (VLMs). Switch providers with a config change — Gemini, GPT-4o, Claude, or local LLaVA via Ollama.

## Features

- **Provider-agnostic** — Gemini, OpenAI, Anthropic, and local Ollama (LLaVA) through one pipeline
- **Structured JSON output** — validated against a Pydantic schema (category, color, material, style, and more)
- **Robust parsing** — defensive JSON extraction, validation retries, and exponential backoff on transport errors
- **Batch tagging** — concurrent processing with configurable parallelism and JSONL output
- **Cost tracking** — per-request token usage and estimated USD cost
- **Evaluation** — compare predictions to ground truth (exact match, macro F1, hierarchical accuracy)
- **Streamlit UI** — single-product, batch, and evaluation tabs in the browser
- **Few-shot support** — optional examples from `config/prompts/few_shot_examples.json`

## Requirements

- Python 3.10–3.12
- API key for cloud providers (Gemini, OpenAI, or Anthropic), or [Ollama](https://ollama.com/) for local tagging

## Installation

```bash
git clone https://github.com/your-org/gen-ai-hub.git
cd "04-evaluation-multimodal/Project Tagger"

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

## Configuration

Set API keys as environment variables (or in a `.env` file at the project root):

```bash
GEMINI_API_KEY=your-key
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
```

Provider defaults live in `config/models.yaml`:

```yaml
default_provider: gemini
default_model: gemini-2.5-flash

providers:
  gemini:
    api_key: "${GEMINI_API_KEY}"
    model: gemini-2.5-flash
  openai:
    api_key: "${OPENAI_API_KEY}"
    model: gpt-4o
  anthropic:
    api_key: "${ANTHROPIC_API_KEY}"
    model: claude-3-5-sonnet-20241022
  local:
    base_url: http://localhost:11434
    model: llava:latest
```

The tag taxonomy and allowed values are defined in `config/tags_schema.yaml`. Prompt templates are in `config/prompts/`.

## Usage

### Streamlit app

```bash
streamlit run app.py
```

Upload an image, enter a description, pick a provider, and download validated JSON tags. The app also supports batch CSV/JSONL upload and evaluation against ground truth.

### CLI

**Tag a single product:**

```bash
python scripts/tag_single.py \
  --image tests/fixtures/sample_image.jpg \
  --description "Red cotton casual t-shirt for men" \
  --provider gemini
```

**Batch tag from CSV or JSONL:**

```bash
python scripts/tag_batch.py \
  --input data/input/sample_products.csv \
  --output data/output/tags.jsonl \
  --provider openai \
  --max-concurrency 4
```

CSV columns: `product_id`, `image`, `description`. JSONL rows may also include `image_base64`.

**Evaluate predictions:**

```bash
python scripts/evaluate.py \
  --predictions data/output/tags.jsonl \
  --ground-truth data/input/sample_ground_truth.jsonl \
  --output data/output/report.json
```

Common flags for tagging scripts: `--provider`, `--model`, `--few-shot`, `--max-concurrency`, `--log-level`.

### Python API

```python
from pathlib import Path

from src.pipeline.tagging_pipeline import TaggingPipeline
from src.schemas.product import ProductInput

pipeline = TaggingPipeline(provider="gemini")

product = ProductInput(
    product_id="product-001",
    image_path=Path("tests/fixtures/sample_image.jpg"),
    description="Red cotton casual t-shirt for men",
)

record = pipeline.tag_one(product)
print(record["tags"])
```

## Output schema

Each tagged product returns a record with `product_id`, `tags`, `error`, `usage`, and `latency_s`. Tags follow the `ProductTags` schema:

| Field | Type | Example |
|-------|------|---------|
| `category` | string | `apparel` |
| `subcategory` | string | `t-shirt` |
| `brand` | string | `Nike` |
| `color` | list | `["red"]` |
| `material` | list | `["cotton"]` |
| `pattern` | string | `solid` |
| `style` | list | `["casual"]` |
| `gender` | string | `men` |
| `age_group` | string | `adult` |
| `usage_occasion` | list | `["casual"]` |
| `size` | string | `M` |
| `is_waterproof` | bool | `false` |

## Providers

| Provider | Class | Notes |
|----------|-------|-------|
| `gemini` | `GeminiTagger` | Google GenAI SDK |
| `openai` | `OpenAITagger` | JSON response format |
| `anthropic` | `AnthropicTagger` | Claude vision models |
| `local` | `LocalTagger` | Ollama + LLaVA, no API key |

To add a provider: subclass `BaseTagger` in `src/tagger/`, implement `_call_model()`, and register it in `src/tagger/factory.py`.

## Project structure

```
├── app.py                      # Streamlit web UI
├── config/
│   ├── models.yaml             # Provider and model settings
│   ├── tags_schema.yaml        # Tag taxonomy
│   └── prompts/                # System, user, and few-shot prompts
├── scripts/
│   ├── tag_single.py           # Single-product CLI
│   ├── tag_batch.py            # Batch tagging CLI
│   └── evaluate.py             # Evaluation CLI
├── src/
│   ├── tagger/                 # BaseTagger + provider implementations
│   ├── pipeline/               # TaggingPipeline orchestration
│   ├── schemas/                # ProductInput and ProductTags models
│   ├── prompts/                # Prompt loading and rendering
│   ├── validation/             # Tag validation helpers
│   ├── evaluation/             # Metrics (F1, exact match, etc.)
│   └── utils/                  # JSON, image, and cost utilities
├── tests/                      # Unit and integration tests
└── data/                       # Sample inputs and outputs
```

## Development

```bash
# Run tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=src --cov-report=term-missing

# Lint
ruff check .

# Auto-fix lint issues
ruff check --fix .
```

See `docs/architecture.md` for a deeper overview of the data flow and design decisions.

## License

MIT — see the [Gen-AI-Hub](https://github.com/aniketpotabatti/gen-ai-hub) repository LICENSE.
