import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Any

import fitz
import streamlit as st


APP_TITLE = "AI Research Explainer"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
MAX_INPUT_CHARS = 60_000
ANALYSIS_DEPTHS = {
    "Fast": 18_000,
    "Balanced": 35_000,
    "Detailed": 60_000,
}


@dataclass
class PaperAnalysis:
    title: str
    summary: str
    key_contributions: list[str]
    methodology: list[str]
    limitations: list[str]
    future_work: list[str]
    eli5: str
    flashcards: list[dict[str, str]]
    quiz_questions: list[dict[str, Any]]


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1180px;
        }
        .hero {
            padding: 1.35rem 1.5rem;
            border-radius: 1.25rem;
            background:
                radial-gradient(circle at top left, rgba(99, 102, 241, 0.20), transparent 35%),
                linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.92));
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.10);
            margin-bottom: 1.25rem;
        }
        .hero h1 {
            margin: 0;
            font-size: 2.35rem;
            letter-spacing: -0.04em;
        }
        .hero p {
            margin: 0.5rem 0 0;
            color: rgba(255, 255, 255, 0.78);
            font-size: 1.02rem;
        }
        .metric-card {
            padding: 1rem;
            border-radius: 1rem;
            border: 1px solid rgba(148, 163, 184, 0.25);
            background: rgba(248, 250, 252, 0.72);
        }
        .pill {
            display: inline-block;
            padding: 0.18rem 0.55rem;
            border-radius: 999px;
            background: rgba(99, 102, 241, 0.12);
            color: rgb(67, 56, 202);
            font-size: 0.78rem;
            font-weight: 650;
            margin-bottom: 0.4rem;
        }
        div[data-testid="stExpander"] {
            border-radius: 1rem;
            border-color: rgba(148, 163, 184, 0.30);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1>🧠 AI Research Explainer</h1>
            <p>Upload a paper, extract its text, and turn dense research into a clean study guide.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def extract_text_from_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    """Extract text from a PDF using PyMuPDF and cache by file bytes."""
    file_hash = hashlib.sha256(pdf_bytes).hexdigest()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    pages: list[dict[str, Any]] = []
    for index, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        pages.append({"page": index, "text": text, "chars": len(text)})

    full_text = "\n\n".join(
        f"[Page {page['page']}]\n{page['text']}" for page in pages if page["text"]
    ).strip()

    return {
        "file_hash": file_hash,
        "page_count": doc.page_count,
        "char_count": len(full_text),
        "pages": pages,
        "text": full_text,
    }


def truncate_text(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    head = text[: int(max_chars * 0.72)]
    tail = text[-int(max_chars * 0.28) :]
    return (
        f"{head}\n\n[... middle of paper truncated for length ...]\n\n{tail}"
    )


def get_gemini_api_key() -> str | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        return api_key

    try:
        return st.secrets.get("GEMINI_API_KEY")
    except Exception:
        return None


def get_llm_client(api_key: str | None = None):
    try:
        from google import genai
    except ImportError as exc:
        raise RuntimeError(
            "The `google-genai` package is not installed. Run `pip install -r requirements.txt`."
        ) from exc

    api_key = api_key or get_gemini_api_key()
    if not api_key:
        raise RuntimeError(
            "Enter a Gemini API key in the sidebar, or set GEMINI_API_KEY in your environment or Streamlit secrets."
        )

    return genai.Client(api_key=api_key)


def analysis_schema() -> str:
    return """
{
  "title": "Short inferred paper title",
  "summary": "Clear 2-4 paragraph summary",
  "key_contributions": ["3-6 concrete contributions"],
  "methodology": ["4-7 bullets explaining data, model, experiment, or proof strategy"],
  "limitations": ["3-6 limitations or threats to validity"],
  "future_work": ["3-6 plausible next steps grounded in the paper"],
  "eli5": "A friendly explanation for a curious 10-year-old",
  "flashcards": [
    {"front": "Question or term", "back": "Concise answer"}
  ],
  "quiz_questions": [
    {
      "question": "Question text",
      "options": ["A", "B", "C", "D"],
      "answer": "Exact correct option text",
      "explanation": "Why the answer is correct"
    }
  ]
}
"""


def analyze_paper_with_llm(
    text: str,
    model: str,
    temperature: float,
    file_hash: str,
    api_key: str | None,
    max_input_chars: int,
) -> dict[str, Any]:
    """Analyze extracted text. file_hash is included to make cache intent explicit."""
    _ = file_hash
    client = get_llm_client(api_key)
    from google.genai import types

    paper_text = truncate_text(text, max_chars=max_input_chars)

    system_prompt = (
        "You are an expert research-paper explainer. You turn technical PDFs into "
        "accurate, readable study guides. Stay faithful to the provided paper text. "
        "If details are missing, say so rather than inventing them. Return only valid JSON."
    )
    user_prompt = f"""
Analyze the research paper text below.

Return JSON matching exactly this shape:
{analysis_schema()}

Requirements:
- Generate exactly 5 flashcards.
- Generate exactly 10 quiz questions.
- Quiz options must contain exactly 4 options.
- Use precise, grounded wording.
- Avoid unsupported claims.

Paper text:
{paper_text}
"""

    response = client.models.generate_content(
        model=model,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )

    content = response.text or "{}"
    return normalize_analysis(json.loads(content))


def normalize_analysis(data: dict[str, Any]) -> dict[str, Any]:
    normalized = {
        "title": str(data.get("title") or "Untitled research paper"),
        "summary": str(data.get("summary") or ""),
        "key_contributions": ensure_list(data.get("key_contributions"))[:6],
        "methodology": ensure_list(data.get("methodology"))[:7],
        "limitations": ensure_list(data.get("limitations"))[:6],
        "future_work": ensure_list(data.get("future_work"))[:6],
        "eli5": str(data.get("eli5") or ""),
        "flashcards": ensure_card_list(data.get("flashcards"), 5),
        "quiz_questions": ensure_quiz_list(data.get("quiz_questions"), 10),
    }
    return normalized


def ensure_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def ensure_card_list(value: Any, limit: int) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    cards = []
    for item in value[:limit]:
        if isinstance(item, dict):
            front = str(item.get("front") or item.get("question") or "").strip()
            back = str(item.get("back") or item.get("answer") or "").strip()
            if front and back:
                cards.append({"front": front, "back": back})
    return cards


def ensure_quiz_list(value: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    questions = []
    for item in value[:limit]:
        if not isinstance(item, dict):
            continue
        options = ensure_list(item.get("options"))[:4]
        questions.append(
            {
                "question": str(item.get("question") or "").strip(),
                "options": options,
                "answer": str(item.get("answer") or "").strip(),
                "explanation": str(item.get("explanation") or "").strip(),
            }
        )
    return [question for question in questions if question["question"]]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return slug or "research-explainer"


def to_markdown(analysis: dict[str, Any], source_name: str) -> str:
    lines = [
        f"# {analysis['title']}",
        "",
        f"_Generated from: {source_name}_",
        "",
        "## Summary",
        "",
        analysis["summary"],
        "",
        "## Key Contributions",
        "",
        *[f"- {item}" for item in analysis["key_contributions"]],
        "",
        "## Methodology",
        "",
        *[f"- {item}" for item in analysis["methodology"]],
        "",
        "## Limitations",
        "",
        *[f"- {item}" for item in analysis["limitations"]],
        "",
        "## Future Work",
        "",
        *[f"- {item}" for item in analysis["future_work"]],
        "",
        "## ELI5 Explanation",
        "",
        analysis["eli5"],
        "",
        "## Flashcards",
        "",
    ]

    for index, card in enumerate(analysis["flashcards"], start=1):
        lines.extend(
            [
                f"### Flashcard {index}",
                "",
                f"**Front:** {card['front']}",
                "",
                f"**Back:** {card['back']}",
                "",
            ]
        )

    lines.extend(["## Quiz Questions", ""])
    for index, question in enumerate(analysis["quiz_questions"], start=1):
        lines.extend([f"### Question {index}", "", question["question"], ""])
        for option in question["options"]:
            lines.append(f"- {option}")
        lines.extend(
            [
                "",
                f"**Answer:** {question['answer']}",
                "",
                f"**Explanation:** {question['explanation']}",
                "",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def render_bullets(items: list[str], empty_text: str = "No items generated.") -> None:
    if not items:
        st.info(empty_text)
        return
    for item in items:
        st.markdown(f"- {item}")


def render_overview(analysis: dict[str, Any]) -> None:
    st.subheader(analysis["title"])
    with st.expander("Summary", expanded=True):
        st.markdown(analysis["summary"] or "_No summary generated._")

    left, right = st.columns(2)
    with left:
        with st.expander("Key contributions", expanded=True):
            render_bullets(analysis["key_contributions"])
        with st.expander("Limitations", expanded=False):
            render_bullets(analysis["limitations"])
    with right:
        with st.expander("Methodology", expanded=True):
            render_bullets(analysis["methodology"])
        with st.expander("Future work", expanded=False):
            render_bullets(analysis["future_work"])


def render_eli5(analysis: dict[str, Any]) -> None:
    st.subheader("ELI5 explanation")
    st.markdown(analysis["eli5"] or "_No ELI5 explanation generated._")


def render_flashcards(analysis: dict[str, Any]) -> None:
    st.subheader("Flashcards")
    if not analysis["flashcards"]:
        st.info("No flashcards generated.")
        return

    for index, card in enumerate(analysis["flashcards"], start=1):
        with st.expander(f"Flashcard {index}: {card['front']}", expanded=False):
            st.markdown(card["back"])


def render_quiz(analysis: dict[str, Any]) -> None:
    st.subheader("Quiz")
    if not analysis["quiz_questions"]:
        st.info("No quiz questions generated.")
        return

    for index, question in enumerate(analysis["quiz_questions"], start=1):
        with st.expander(f"Question {index}: {question['question']}", expanded=index == 1):
            selected = st.radio(
                "Choose an answer",
                question["options"] or ["No options generated"],
                key=f"quiz_{index}",
                index=None,
            )
            if selected:
                if selected == question["answer"]:
                    st.success("Correct.")
                else:
                    st.error(f"Not quite. Correct answer: {question['answer']}")
                if question["explanation"]:
                    st.caption(question["explanation"])


def render_export(analysis: dict[str, Any], source_name: str) -> None:
    st.subheader("Markdown export")
    markdown = to_markdown(analysis, source_name)
    st.download_button(
        "Download Markdown",
        markdown,
        file_name=f"{slugify(analysis['title'])}.md",
        mime="text/markdown",
        use_container_width=True,
    )
    with st.expander("Preview Markdown", expanded=False):
        st.code(markdown, language="markdown")


def render_extracted_text(extraction: dict[str, Any]) -> None:
    st.subheader("Extracted text")
    st.caption(
        f"{extraction['page_count']} pages · {extraction['char_count']:,} characters · "
        f"SHA-256: {extraction['file_hash'][:12]}…"
    )
    with st.expander("Full extracted text", expanded=False):
        st.text_area(
            "PDF text",
            extraction["text"],
            height=460,
            label_visibility="collapsed",
        )


def main() -> None:
    inject_styles()
    render_hero()

    with st.sidebar:
        st.header("Paper")
        uploaded_file = st.file_uploader("Upload a PDF research paper", type=["pdf"])
        st.divider()
        st.header("LLM settings")
        model = st.text_input("Model", value=DEFAULT_MODEL)
        api_key = st.text_input(
            "Gemini API key",
            value="",
            type="password",
            placeholder="Paste your Gemini API key",
            help="This is used for the current session. You can also set GEMINI_API_KEY in your environment.",
        )
        depth = st.radio(
            "Analysis depth",
            options=list(ANALYSIS_DEPTHS.keys()),
            index=0,
            horizontal=True,
            help="Fast sends less paper text to Gemini. Detailed is slower but gives the model more context.",
        )
        temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)
        st.caption("Use the field above, or set `GEMINI_API_KEY` in your environment/secrets.")
        st.divider()
        section = st.radio(
            "Navigate",
            ["Overview", "ELI5", "Flashcards", "Quiz", "Extracted text", "Export"],
        )

    if not uploaded_file:
        st.info("Upload a PDF to begin. The extraction step is cached, so re-runs stay snappy.")
        st.stop()

    pdf_bytes = uploaded_file.getvalue()
    with st.spinner("Extracting text with PyMuPDF..."):
        extraction = extract_text_from_pdf(pdf_bytes)

    col_a, col_b, col_c = st.columns(3)
    col_a.markdown(
        f"<div class='metric-card'><span class='pill'>Pages</span><h3>{extraction['page_count']}</h3></div>",
        unsafe_allow_html=True,
    )
    col_b.markdown(
        f"<div class='metric-card'><span class='pill'>Characters</span><h3>{extraction['char_count']:,}</h3></div>",
        unsafe_allow_html=True,
    )
    col_c.markdown(
        f"<div class='metric-card'><span class='pill'>Cached ID</span><h3>{extraction['file_hash'][:8]}</h3></div>",
        unsafe_allow_html=True,
    )

    if not extraction["text"]:
        st.error("No selectable text was found in this PDF. It may be scanned or image-only.")
        st.stop()

    active_hash = extraction["file_hash"]
    has_current_analysis = (
        "analysis" in st.session_state
        and st.session_state.get("analysis_file_hash") == active_hash
    )

    run_analysis = st.button(
        "Analyze paper",
        type="primary",
        use_container_width=True,
        help="Runs the Gemini analysis. PDF extraction is already complete.",
    )
    if run_analysis:
        with st.spinner("Asking the LLM to build the explainer..."):
            try:
                st.session_state.analysis = analyze_paper_with_llm(
                    extraction["text"],
                    model=model,
                    temperature=temperature,
                    file_hash=extraction["file_hash"],
                    api_key=api_key.strip() or None,
                    max_input_chars=ANALYSIS_DEPTHS.get(depth or "Fast", 18_000),
                )
                st.session_state.source_name = uploaded_file.name
                st.session_state.analysis_file_hash = active_hash
            except Exception as exc:
                st.error(str(exc))
                st.stop()

    has_current_analysis = (
        "analysis" in st.session_state
        and st.session_state.get("analysis_file_hash") == active_hash
    )

    if not has_current_analysis:
        st.info(
            "PDF text is extracted and ready. Click **Analyze paper** when you want Gemini to generate the results."
        )
        with st.expander("Preview extracted text while you wait", expanded=False):
            st.text_area(
                "Extracted text preview",
                extraction["text"][:12_000],
                height=320,
                label_visibility="collapsed",
            )
        if section == "Extracted text":
            st.divider()
            render_extracted_text(extraction)
        st.stop()

    analysis = st.session_state.analysis
    source_name = st.session_state.get("source_name", uploaded_file.name)

    st.divider()
    if section == "Overview":
        render_overview(analysis)
    elif section == "ELI5":
        render_eli5(analysis)
    elif section == "Flashcards":
        render_flashcards(analysis)
    elif section == "Quiz":
        render_quiz(analysis)
    elif section == "Extracted text":
        render_extracted_text(extraction)
    elif section == "Export":
        render_export(analysis, source_name)


if __name__ == "__main__":
    main()
