"""
Prompts for the Doc Architecture Agent.
Takes a CodeContext and produces a structured documentation plan.
"""
from langchain_core.prompts import ChatPromptTemplate
from app.models.schemas import CodeContext


DOC_PLANNER_SYSTEM = """You are a documentation architect. Your job is to analyze source code and propose
the ideal documentation structure BEFORE any writing begins.

Your output must be valid JSON matching this exact schema:
{{
  "project_type": "<library | cli | api | service | script>",
  "project_name": "<inferred from code>",
  "reasoning": "<1-2 sentences explaining your classification>",
  "sections": [
    {{
      "id": "<snake_case_id>",
      "title": "<Section Title>",
      "description": "<What this section covers in 1 sentence>",
      "estimated_words": <number>,
      "subsections": []
    }}
  ]
}}

Standard section templates by project type:

LIBRARY: overview, installation, quick_start, api_reference, examples, troubleshooting, changelog
CLI: overview, installation, usage, commands, configuration, examples, troubleshooting
API: overview, authentication, endpoints, request_response, errors, rate_limits, examples
SERVICE: overview, architecture, configuration, deployment, api_reference, monitoring, troubleshooting
SCRIPT: overview, usage, configuration, examples

Only include sections that are relevant to the actual code. Add or remove sections as needed.
Output ONLY the JSON object. No markdown, no explanation."""


DOC_PLANNER_HUMAN = """Analyze this source code and propose a documentation architecture:

**File**: {filename}
**Language**: {language}
**Total Lines**: {total_lines}
**Module Docstring**: {module_docstring}

**Imports** ({import_count} total):
{imports_summary}

**Functions** ({function_count} total):
{functions_summary}

**Classes** ({class_count} total):
{classes_summary}

Based on the above, propose the ideal documentation structure as JSON."""


def build_planner_prompt() -> ChatPromptTemplate:
    """Return the ChatPromptTemplate for the doc planner chain."""
    return ChatPromptTemplate.from_messages([
        ("system", DOC_PLANNER_SYSTEM),
        ("human", DOC_PLANNER_HUMAN),
    ])


def format_planner_input(ctx: CodeContext) -> dict:
    """Format a CodeContext into prompt variables for the planner."""
    functions_summary = "\n".join(
        f"  - {f.name}({', '.join(f.params)}) -> {f.return_type or 'None'}"
        + (f"\n    Docstring: {f.docstring[:80]}..." if f.docstring else "")
        for f in ctx.functions[:20]  # cap at 20 for context length
    ) or "  (none)"

    classes_summary = "\n".join(
        f"  - class {c.name}({', '.join(c.base_classes)}): {len(c.methods)} methods"
        for c in ctx.classes[:10]
    ) or "  (none)"

    imports_summary = "\n".join(
        f"  {imp}" for imp in ctx.imports[:15]
    ) or "  (none)"

    return {
        "filename": ctx.filename,
        "language": ctx.language,
        "total_lines": ctx.total_lines,
        "module_docstring": ctx.module_docstring or "(none)",
        "import_count": len(ctx.imports),
        "imports_summary": imports_summary,
        "function_count": len(ctx.functions),
        "functions_summary": functions_summary,
        "class_count": len(ctx.classes),
        "classes_summary": classes_summary,
    }
