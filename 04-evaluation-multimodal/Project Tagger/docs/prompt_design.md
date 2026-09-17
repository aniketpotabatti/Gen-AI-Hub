# Prompt Design

## System prompt (`config/prompts/system_prompt.txt`)

Casts the VLM as an expert product-tagging assistant with six rules:

1. Enumerates the extractable attributes (category → usage occasion).
2. **Evidence-only rule** — use only what's visible or stated; never invent.
3. **JSON-only rule** — output must match the schema.
4. **Null-over-guess rule** — omit uncertain fields (precision > recall).
5. Prioritize precision over comprehensiveness.

Low temperature (0.2 in `models.yaml`) keeps output deterministic; the JSON-only
rule pairs with provider JSON modes (Gemini `response_mime_type`, OpenAI
`response_format`, Ollama `format="json"`) and a code-level `FORMAT_NUDGE`
retry when validation fails.

## User prompt (`config/prompts/user_prompt_template.txt`)

```
Product Description: {description}

Please analyze the product image and description above to generate structured product tags.
Respond with valid JSON only, matching the ProductTags schema (no markdown fences, no commentary).
```

The image travels as the actual multimodal payload (provider-specific encoding);
the text template carries the description plus the JSON-only instruction. The
final line was added because VLMs otherwise wrap JSON in fences or add
commentary — `extract_json_block()` still strips those defensively.

## Few-shot examples (`config/prompts/few_shot_examples.json`)

Up to 3 demonstrations appended as `Example N: Image: <image_note> /
Description: ... / Tags: {...}`. Shipped with 3 diverse apparel/footwear
examples covering lists (`color`, `material`), scalars (`pattern`, `size`),
and multi-value `style`/`usage_occasion`. Enable with `--few-shot`.

**Why text-only demos?** Prompt templates are plain text, so demo images are
represented by `image_note` descriptions. This still teaches output shape and
taxonomy vocabulary; the live call always includes the real product image.

## Optimization knobs (from the plan)

| Knob | Setting | Rationale |
|---|---|---|
| Temperature | 0.2 | Deterministic, comparable tags |
| Max tokens | 1000 | Bounds cost, fits the 13-field schema |
| Top-p | 0.9 | Mild diversity without drift |
| Validation retries | 3, with `FORMAT_NUDGE` | Recovers from fence-wrapped/incomplete JSON |
| Image cap | 1024px longest side | Cuts vision tokens, keeps attributes legible |

## A/B testing ideas

- Zero-shot vs `--few-shot` on the eval set (`scripts/evaluate.py`, macro F1).
- Temperature 0.0 vs 0.2 for consistency (exact-match across repeat runs).
- Adding taxonomy vocab lists into the system prompt vs prompt length/cost.
