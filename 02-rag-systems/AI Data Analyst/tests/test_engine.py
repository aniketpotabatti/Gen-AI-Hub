"""Unit tests for local analysis helpers (no Gemini API required)."""

import io

import pandas as pd

from src.engine.ai_analyst import format_result, parse_model_json, safe_execute
from src.engine.doc_processor import chunk_text, document_to_chunks, load_csv_from_bytes, load_pdf_from_bytes
from src.engine.doc_processor import Document
from src.viz.chart_generator import auto_chart, generate_chart


def test_parse_model_json_strips_fences():
    raw = """```json
{"code": "result = df.head()", "explanation": "preview", "chart_type": "none"}
```"""
    parsed = parse_model_json(raw)
    assert parsed is not None
    assert parsed["code"] == "result = df.head()"
    assert parsed["chart_type"] == "none"


def test_parse_model_json_embedded_object():
    raw = 'Here you go:\n{"code": "result = 1", "explanation": "one"}\nThanks'
    parsed = parse_model_json(raw)
    assert parsed["code"] == "result = 1"


def test_safe_execute_allows_common_builtins():
    df = pd.DataFrame({"n": [1, 2, 3, 4]})
    out = safe_execute("result = round(float(df['n'].mean()), 2)", df)
    assert out["error"] is None
    assert out["result"] == 2.5


def test_safe_execute_blocks_import():
    df = pd.DataFrame({"n": [1]})
    out = safe_execute("import os\nresult = os.getcwd()", df)
    assert out["result"] is None
    assert out["error"]


def test_format_result_dataframe():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    text = format_result(df)
    assert "a" in text
    assert "1" in text


def test_chunk_text_respects_size():
    text = "\n\n".join([f"Paragraph {i} " + ("word " * 20) for i in range(8)])
    chunks = chunk_text(text, chunk_size=120, overlap=20)
    assert chunks
    assert all(len(c) <= 160 for c in chunks)


def test_document_to_chunks_ids():
    doc = Document(content="Hello world. " * 80, metadata={"source": "demo.pdf"})
    chunks = document_to_chunks(doc, chunk_size=80, overlap=10)
    assert chunks
    assert chunks[0]["metadata"]["source"] == "demo.pdf"
    assert chunks[0]["id"].endswith("_chunk_0")


def test_load_csv_from_bytes():
    csv = b"name,value\nalice,1\nbob,2\n"
    df = load_csv_from_bytes(csv, "demo.csv")
    assert list(df.columns) == ["name", "value"]
    assert len(df) == 2


def test_load_empty_csv():
    df = load_csv_from_bytes(b"", "empty.csv")
    assert df.empty


def test_auto_chart_and_generate_chart():
    df = pd.DataFrame({"category": ["a", "b", "a", "b"], "value": [10, 20, 15, 25]})
    overview = auto_chart(df, title="Demo")
    assert overview is not None

    result = df.groupby("category", as_index=False)["value"].mean()
    fig = generate_chart(
        result=result,
        chart_suggestion={"type": "bar", "config": {"x": "category", "y": "value", "title": "Avg"}},
        df=df,
    )
    assert fig is not None


def test_load_pdf_from_bytes_emptyish():
    # Minimal PDF with no extractable text should still return a Document.
    from pypdf import PdfWriter

    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(buffer)
    doc = load_pdf_from_bytes(buffer.getvalue(), "blank.pdf")
    assert doc.metadata["source"] == "blank.pdf"
    assert document_to_chunks(doc) == []
