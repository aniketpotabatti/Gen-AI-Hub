"""
Pydantic schemas for request/response data models.
"""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ── Code Parser Schemas ───────────────────────────────────────────────────────

class FunctionInfo(BaseModel):
    name: str
    params: list[str] = []
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    start_line: int = 0
    end_line: int = 0


class ClassInfo(BaseModel):
    name: str
    methods: list[FunctionInfo] = []
    docstring: Optional[str] = None
    base_classes: list[str] = []


class CodeContext(BaseModel):
    """Structured representation of parsed source code."""
    language: str
    filename: str
    raw_code: str
    functions: list[FunctionInfo] = []
    classes: list[ClassInfo] = []
    imports: list[str] = []
    module_docstring: Optional[str] = None
    total_lines: int = 0


# ── Doc Planning Schemas ──────────────────────────────────────────────────────

class DocSection(BaseModel):
    id: str
    title: str
    description: str
    estimated_words: int = 200
    subsections: list[DocSection] = []
    status: str = "pending"  # pending | generating | done | error


class DocPlan(BaseModel):
    """Proposed documentation architecture."""
    project_type: str          # library | cli | api | service | script
    project_name: str
    sections: list[DocSection]
    reasoning: str


class CodeFile(BaseModel):
    filename: str
    code: str


class ParseRequest(BaseModel):
    code: Optional[str] = Field(default=None, description="Raw source code string (single file mode)")
    filename: str = Field(default="code.py", description="Filename (used for language detection)")
    files: Optional[list[CodeFile]] = Field(default=None, description="List of files for multi-file/project mode")


class ParseResponse(BaseModel):
    success: bool
    code_context: Optional[CodeContext] = None
    error: Optional[str] = None


class PlanRequest(BaseModel):
    code_context: CodeContext
    api_key: Optional[str] = Field(default=None, description="Optional user-provided LLM API Key")
    provider: Optional[str] = Field(default=None, description="Optional provider (gemini or openai)")
    model: Optional[str] = Field(default=None, description="Optional model name")
    tone: Optional[str] = Field(default=None, description="Documentation tone (balanced, concise, tutorial, in-depth)")
    audience: Optional[str] = Field(default=None, description="Audience level (beginner, intermediate, expert)")


class PlanResponse(BaseModel):
    success: bool
    doc_plan: Optional[DocPlan] = None
    error: Optional[str] = None


class WriteRequest(BaseModel):
    code_context: CodeContext
    doc_plan: DocPlan
    section_id: str = Field(..., description="ID of the section to generate")
    api_key: Optional[str] = Field(default=None, description="Optional user-provided LLM API Key")
    provider: Optional[str] = Field(default=None, description="Optional provider (gemini or openai)")
    model: Optional[str] = Field(default=None, description="Optional model name")
    tone: Optional[str] = Field(default=None, description="Documentation tone (balanced, concise, tutorial, in-depth)")
    audience: Optional[str] = Field(default=None, description="Audience level (beginner, intermediate, expert)")


class ExportRequest(BaseModel):
    doc_plan: DocPlan
    sections_content: dict[str, str] = Field(
        ..., description="Map of section_id → generated markdown content"
    )
    format: str = Field(default="markdown", description="markdown | html")


class HealthResponse(BaseModel):
    status: str
    version: str
    llm_provider: str
