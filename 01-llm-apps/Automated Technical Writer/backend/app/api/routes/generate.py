"""
Generate API routes — core LLM pipeline endpoints.

Routes:
  POST /api/generate/parse  — Parse source code → CodeContext
  POST /api/generate/plan   — CodeContext → DocPlan
  POST /api/generate/write  — Stream one doc section (SSE)
"""
import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import (
    ParseRequest,
    ParseResponse,
    PlanRequest,
    PlanResponse,
    WriteRequest,
)
from app.services.code_parser import parse_code
from app.llm.chains import run_planner_chain, stream_writer_chain

router = APIRouter(prefix="/api/generate", tags=["generate"])
logger = logging.getLogger(__name__)


@router.post("/parse", response_model=ParseResponse)
async def parse_code_endpoint(request: ParseRequest):
    """
    Parse raw source code into a structured CodeContext.
    This is the first step in the Code-to-Doc pipeline.
    """
    try:
        code_context = parse_code(code=request.code, filename=request.filename)
        return ParseResponse(success=True, code_context=code_context)
    except Exception as e:
        logger.exception("Code parsing failed")
        return ParseResponse(success=False, error=str(e))


@router.post("/plan", response_model=PlanResponse)
async def plan_docs_endpoint(request: PlanRequest):
    """
    Run the Doc Architecture Agent on a parsed CodeContext.
    Returns a proposed documentation structure for user approval.
    """
    try:
        doc_plan = run_planner_chain(request.code_context)
        return PlanResponse(success=True, doc_plan=doc_plan)
    except Exception as e:
        logger.exception("Doc planning failed")
        return PlanResponse(success=False, error=str(e))


@router.post("/write")
async def write_section_endpoint(request: WriteRequest):
    """
    Stream a single documentation section via Server-Sent Events (SSE).
    The client receives markdown tokens in real time.
    """
    # Find the requested section in the plan
    section = next(
        (s for s in request.doc_plan.sections if s.id == request.section_id),
        None,
    )
    if not section:
        raise HTTPException(
            status_code=404,
            detail=f"Section '{request.section_id}' not found in doc plan",
        )

    async def event_generator() -> AsyncIterator[dict]:
        """Yield SSE events for each token chunk."""
        try:
            async for chunk in stream_writer_chain(
                code_context=request.code_context,
                doc_plan=request.doc_plan,
                section=section,
            ):
                yield {"event": "token", "data": chunk}
            # Signal completion
            yield {"event": "done", "data": json.dumps({"section_id": request.section_id})}
        except Exception as e:
            logger.exception("Streaming writer failed for section %s", request.section_id)
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())
