# AI Research Explainer

A modern Streamlit app that turns a PDF research paper into a readable study guide.

**Created:** Aug 2024

## Features

- Upload a PDF research paper.
- Extract text with PyMuPDF.
- Cache extracted text for faster reruns.
- Use an LLM to generate:
  - summary
  - key contributions
  - methodology
  - limitations
  - future work
  - ELI5 explanation
  - five flashcards
  - ten quiz questions
- Navigate with a sidebar.
- Review content in clean expandable sections.
- Export the generated study guide as Markdown.
- Choose Fast, Balanced, or Detailed analysis depth to trade speed for context.

## Setup

```bash
pip install -r requirements.txt
```

Set your Gemini API key:

```bash
$env:GEMINI_API_KEY="your-api-key"
```

Optionally choose a model:

```bash
$env:GEMINI_MODEL="gemini-3.5-flash"
```

## Run

```bash
streamlit run app.py
```

## Notes

- The app expects PDFs with selectable text. Scanned image-only PDFs need OCR first.
- Long papers are truncated before being sent to the LLM to keep requests manageable.
- PDF extraction is cached. LLM analysis runs only after you click **Analyze paper**.

