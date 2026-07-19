"""
Prompts for the Section Writer Agent.
Takes a CodeContext + DocPlan + section ID and writes the markdown content.
"""
from langchain_core.prompts import ChatPromptTemplate
from app.models.schemas import CodeContext, DocPlan, DocSection


WRITER_SYSTEM = """You are an expert technical writer. Write the requested documentation section
using ONLY the information available in the provided code context.

Critical rules:
- Never invent APIs, parameters, or behavior that don't appear in the code
- Always include working code examples using the actual function/class names from the code
- Use markdown formatting consistently
- Start directly with the section content — no preamble
- Keep the tone professional, clear, and helpful
"""

WRITER_HUMAN = """Write the **{section_title}** section of the documentation.

**Project**: {project_name} ({project_type})
**File**: {filename} ({language})

**Section description**: {section_description}

**Code Context**:
Module docstring: {module_docstring}

Functions available:
{functions_detail}

Classes available:
{classes_detail}

**Raw code snippet** (for reference):
```{language}
{code_snippet}
```

Write the complete "{section_title}" section in markdown. Be thorough but concise.
Include practical code examples using the actual functions/classes above."""


def build_writer_prompt() -> ChatPromptTemplate:
    """Return the ChatPromptTemplate for the section writer chain."""
    return ChatPromptTemplate.from_messages([
        ("system", WRITER_SYSTEM),
        ("human", WRITER_HUMAN),
    ])


def format_writer_input(ctx: CodeContext, plan: DocPlan, section: DocSection) -> dict:
    """Format inputs for the writer prompt."""
    functions_detail = "\n".join(
        f"- **{f.name}**({', '.join(f.params)}) -> {f.return_type or 'None'}\n"
        + (f"  {f.docstring}" if f.docstring else "")
        for f in ctx.functions[:15]
    ) or "(no functions)"

    classes_detail = "\n".join(
        f"- **class {c.name}**({', '.join(c.base_classes)})\n"
        + "\n".join(f"  - {m.name}({', '.join(m.params)})" for m in c.methods[:10])
        for c in ctx.classes[:5]
    ) or "(no classes)"

    # Use first 2000 chars of code as context snippet
    code_snippet = ctx.raw_code[:2000]
    if len(ctx.raw_code) > 2000:
        code_snippet += "\n# ... (truncated)"

    return {
        "section_title": section.title,
        "section_description": section.description,
        "project_name": plan.project_name,
        "project_type": plan.project_type,
        "filename": ctx.filename,
        "language": ctx.language,
        "module_docstring": ctx.module_docstring or "(none)",
        "functions_detail": functions_detail,
        "classes_detail": classes_detail,
        "code_snippet": code_snippet,
    }
