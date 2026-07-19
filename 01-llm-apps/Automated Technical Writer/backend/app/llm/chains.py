"""
LangChain chains for the Automated Technical Writer.

Two main chains:
1. build_planner_chain() — Produces a DocPlan JSON from CodeContext
2. build_writer_chain()  — Streams markdown content for one doc section
"""
from __future__ import annotations
import json
import logging
from typing import AsyncIterator

from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.models.schemas import CodeContext, DocPlan, DocSection
from app.llm.prompts.doc_planner_prompt import (
    build_planner_prompt,
    format_planner_input,
)
from app.llm.prompts.doc_writer_prompt import (
    build_writer_prompt,
    format_writer_input,
)

logger = logging.getLogger(__name__)


def _get_llm(streaming: bool = False):
    """
    Instantiate the configured LLM.
    Supports: Google Gemini (default), OpenAI GPT-4o.
    """
    if settings.llm_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.gemini_api_key,
            temperature=settings.llm_temperature,
            streaming=streaming,
        )
    elif settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI  # type: ignore
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=settings.llm_temperature,
            streaming=streaming,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


# ── Planner Chain ─────────────────────────────────────────────────────────────

def run_planner_chain(code_context: CodeContext) -> DocPlan:
    """
    Synchronously run the planner chain.
    Returns a DocPlan with the proposed documentation architecture.
    """
    llm = _get_llm(streaming=False)
    prompt = build_planner_prompt()
    chain = prompt | llm | StrOutputParser()

    prompt_vars = format_planner_input(code_context)
    raw_output = chain.invoke(prompt_vars)

    # Clean up markdown code fences if present
    raw_output = raw_output.strip()
    if raw_output.startswith("```"):
        lines = raw_output.split("\n")
        raw_output = "\n".join(lines[1:-1]) if lines[-1] == "```" else "\n".join(lines[1:])

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError as e:
        logger.error("Planner JSON parse error: %s\nRaw: %s", e, raw_output[:500])
        # Return a safe fallback plan
        data = {
            "project_type": "script",
            "project_name": code_context.filename,
            "reasoning": "Could not determine project type automatically.",
            "sections": [
                {"id": "overview", "title": "Overview", "description": "High-level overview.", "estimated_words": 150, "subsections": []},
                {"id": "usage", "title": "Usage", "description": "How to use this code.", "estimated_words": 200, "subsections": []},
                {"id": "api_reference", "title": "API Reference", "description": "Function and class reference.", "estimated_words": 300, "subsections": []},
            ],
        }

    # Add status field to each section
    sections = []
    for s in data.get("sections", []):
        s.setdefault("status", "pending")
        s.setdefault("subsections", [])
        sections.append(DocSection(**s))

    return DocPlan(
        project_type=data.get("project_type", "script"),
        project_name=data.get("project_name", code_context.filename),
        sections=sections,
        reasoning=data.get("reasoning", ""),
    )


# ── Writer Chain (Streaming) ──────────────────────────────────────────────────

async def stream_writer_chain(
    code_context: CodeContext,
    doc_plan: DocPlan,
    section: DocSection,
) -> AsyncIterator[str]:
    """
    Asynchronously stream the writer chain output token by token.
    Yields markdown string chunks as they arrive from the LLM.
    """
    llm = _get_llm(streaming=True)
    prompt = build_writer_prompt()
    chain = prompt | llm | StrOutputParser()

    prompt_vars = format_writer_input(code_context, doc_plan, section)

    async for chunk in chain.astream(prompt_vars):
        yield chunk
