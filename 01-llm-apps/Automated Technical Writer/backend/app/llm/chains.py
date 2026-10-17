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


def _get_llm(
    streaming: bool = False,
    api_key: str | None = None,
    provider: str | None = None,
    model: str | None = None,
):
    """
    Instantiate the configured LLM.
    Supports: Google Gemini (default), OpenAI GPT-4o.
    Uses runtime overrides if provided, otherwise falls back to environment configuration.
    """
    active_provider = (provider or settings.llm_provider).lower()
    active_model = model or settings.llm_model

    if active_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore
        key = api_key or settings.gemini_api_key
        return ChatGoogleGenerativeAI(
            model=active_model or "gemini-2.5-flash",
            google_api_key=key,
            temperature=settings.llm_temperature,
            streaming=streaming,
        )
    elif active_provider == "openai":
        from langchain_openai import ChatOpenAI  # type: ignore
        key = api_key or settings.openai_api_key
        return ChatOpenAI(
            model=active_model or "gpt-4o",
            api_key=key,
            temperature=settings.llm_temperature,
            streaming=streaming,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {active_provider}")


# ── Planner Chain ─────────────────────────────────────────────────────────────

def run_planner_chain(
    code_context: CodeContext,
    api_key: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> DocPlan:
    """
    Synchronously run the planner chain.
    Returns a DocPlan with the proposed documentation architecture.
    """
    llm = _get_llm(streaming=False, api_key=api_key, provider=provider, model=model)
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
    api_key: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    tone: str | None = None,
    audience: str | None = None,
) -> AsyncIterator[str]:
    """
    Asynchronously stream the writer chain output token by token.
    Yields markdown string chunks as they arrive from the LLM.
    """
    llm = _get_llm(streaming=True, api_key=api_key, provider=provider, model=model)
    prompt = build_writer_prompt()
    chain = prompt | llm | StrOutputParser()

    prompt_vars = format_writer_input(
        code_context, doc_plan, section, tone=tone, audience=audience
    )

    async for chunk in chain.astream(prompt_vars):
        yield chunk
