# Multimodal Product Tagging

Automatically generate structured product tags from **product images + descriptions** using Vision-Language Foundation Models (VLMs) — Gemini 2.5 Flash, GPT-4o, Claude 3.5 Sonnet, or local LLaVA/Qwen2-VL via Ollama/vLLM. Outputs validated JSON conforming to a Pydantic `ProductTags` schema.

## Quickstart

```bash
# 1. Install (from this folder)
pip install -e ".[dev]"

# 2. Configure credentials
cp .env.example .env   # then fill in GEMINI_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY

# 3. Tag a single product
python scripts/tag_single.py --image tests/fixtures/sample_image.jpg \
    --description "Red cotton casual t-shirt for men" --provider gemini

# 4. Batch tag from CSV/JSONL -> JSONL
python scripts/tag_batch.py --input data/input/products.csv --output data/output/tags.jsonl

# 5. Evaluate predictions vs ground truth
python scripts/evaluate.py --predictions data/output/tags.jsonl \
    --ground-truth data/input/ground_truth.jsonl --output data/output/report.json

# 6. Run tests
pytest
```

### Web app (Streamlit)

```bash
streamlit run app.py
```

Three tabs: **Tag Single** (upload image + description → tags), **Batch Tag**
(upload CSV/JSONL → results table + JSONL download), **Evaluate** (predictions
vs ground-truth JSONL → exact-match, macro F1, per-attribute chart). Provider,
model override, few-shot, and concurrency are set in the sidebar. Live tagging
needs an API key (`.env`); the Evaluate tab works fully offline via the
"Use sample ground truth" button.

### Batch input formats

CSV (`--input products.csv`):
```csv
product_id,image,description
p001,images/shirt.jpg,Red cotton casual t-shirt for men
```

JSONL (`--input products.jsonl`, one object per line):
```json
{"product_id": "p001", "image": "images/shirt.jpg", "description": "Red cotton t-shirt"}
```

Image paths may be absolute or relative to the input file. `image_base64` is accepted as an alternative to `image`/`image_path`.

### Few-shot prompting

```bash
python scripts/tag_single.py --image img.jpg --description "..." --few-shot
```

Appends up to 3 demonstrations from `config/prompts/few_shot_examples.json` (edit that file to add your own domain examples).

## Project layout

```
config/            models.yaml, tags_schema.yaml, prompts/
src/
  tagger/          BaseTagger + gemini/openai/anthropic/local + factory
  schemas/         ProductInput / ProductTags (Pydantic)
  prompts/         prompt loader (incl. few-shot support)
  validation/      JSON schema validation
  pipeline/        TaggingPipeline (tag -> validate -> save JSONL)
  evaluation/      exact-match, attribute F1, hierarchical accuracy, latency, cost
  utils/           image handling, cost tracking
scripts/           tag_single.py, tag_batch.py, evaluate.py
tests/             mock-based unit tests + fixtures
docs/              architecture.md, prompt_design.md, model_comparison.md
notebooks/         01_explore_models, 02_prompt_engineering, 03_evaluation
data/input|output  sample inputs (git-ignored outputs)
```

See `plan.md` for the full design, and `docs/` for architecture, prompt-design, and model-comparison notes.
