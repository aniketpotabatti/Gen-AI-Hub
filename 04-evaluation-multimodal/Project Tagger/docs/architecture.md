# Architecture: Multimodal Product Tagging

## Data flow

```
image + description
        │
        ▼
┌───────────────┐   prompts    ┌────────────┐  raw JSON   ┌──────────────┐
│ TaggingPipeline│ ──────────▶ │ BaseTagger │ ──────────▶ │ ProductTags  │
│ load → tag →   │  system +   │ subclass   │  validate   │  (Pydantic)  │
│ validate → save│  user+shots │ (provider) │  (×3 retry) │              │
└───────┬────────┘             └─────┬──────┘             └──────┬───────┘
        │ JSONL                       │ usage                    │ record
        ▼                             ▼                          ▼
  data/output/*.jsonl ─────────▶ CostTracker              scripts/evaluate.py
```

## Components

- **`src/tagger/`** — `BaseTagger` owns the whole tagging loop (prompt build →
  `_call_model()` with tenacity backoff → `ProductTags` validation with format
  nudge, max 3 attempts → cost recording). Subclasses (`GeminiTagger`,
  `OpenAITagger`, `AnthropicTagger`, `LocalTagger`) implement only
  `_call_model()` returning `(raw_text, usage)`. All SDK imports are lazy so the
  package imports without credentials or optional deps. `factory.create_tagger()`
  instantiates by provider name from `config/models.yaml`.
- **`src/schemas/`** — `ProductInput` (image path or base64 + description) and
  `ProductTags` (13 tagged fields + normalization/validation rules from the plan).
- **`src/prompts/`** — loads `system_prompt.txt` / `user_prompt_template.txt`;
  optional few-shot demos from `few_shot_examples.json` are appended as text
  (`image_note` stands in for demo images, which can't be embedded in text).
- **`src/validation/`** — standalone `validate_tags()` for externally produced
  JSON (pipeline re-validation, cached/human-annotated data).
- **`src/pipeline/`** — `TaggingPipeline` orchestrates single + batch tagging.
  Concurrency uses a `ThreadPoolExecutor` + semaphore because provider SDKs are
  blocking; `tag_one()` never raises (errors land in the record). Results
  persist as JSONL via `save_jsonl()`.
- **`src/evaluation/`** — pure-function metrics over `(predictions, truths)`:
  exact-match ratio, attribute-wise P/R/F1, hierarchical accuracy, latency,
  cost. `scripts/evaluate.py` aligns records by `product_id` (falls back to
  order) and writes the report.
- **`src/utils/`** — `image_utils` (verify/resize ≤1024px/base64) and
  `cost_tracker` (per-model $/1M-token table + aggregates).
- **`scripts/`** — thin CLI wrappers (`tag_single.py`, `tag_batch.py`,
  `evaluate.py`) sharing flags via `_cli_common.py` (not a public entry point).

## Key decisions

1. **Threads over asyncio** for batch: provider SDKs are sync/blocking, so a
   bounded thread pool with a semaphore is simpler and correct; the async
   `tag_batch()` wrapper just schedules `tag_one` onto the pool.
2. **Validation inside the tagger loop**, not only in the pipeline: retrying with
   a stricter format nudge recovers from malformed JSON without a new image load.
3. **Lazy SDK imports with clear errors**: missing `google-genai`/`openai`/
   `anthropic`/`ollama` or unresolved `${API_KEY}` placeholders raise actionable
   messages instead of import-time failures.
4. **Few-shot as text, not images**: demo images can't travel in a text prompt
   template, so `image_note` describes them; the live product image is still
   sent as real pixels every call.
5. **Cost as first-class output**: every `_call_model()` returns token usage;
   `CostTracker` aggregates per-model and average cost per product for the
   evaluation report.
