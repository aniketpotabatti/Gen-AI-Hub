# Model Comparison (template)

Run each provider over the same eval set, then fill in this table from
`scripts/evaluate.py` reports. Suggested commands:

```bash
for p in gemini openai anthropic local; do
  python scripts/tag_batch.py --input data/input/eval.jsonl --output data/output/tags_$p.jsonl --provider $p
  python scripts/evaluate.py --predictions data/output/tags_$p.jsonl \
      --ground-truth data/input/ground_truth.jsonl --output data/output/report_$p.json
done
```

| Model | Exact match | Macro F1 | Hier. acc. | Mean latency | Avg cost/product | Notes |
|---|---|---|---|---|---|---|
| Gemini 2.5 Flash | | | | | | Fast, cheap; default provider |
| GPT-4o | | | | | | Strongest reasoning; JSON mode |
| Claude 3.5 Sonnet | | | | | | Large context; good reasoning |
| LLaVA (local) | | | | | | Free; needs Ollama running |

Also compare **zero-shot vs `--few-shot`** per model (macro F1 delta) and log
failure patterns (fence-wrapped JSON, invented attributes, taxonomy drift) to
feed back into `docs/prompt_design.md`.
