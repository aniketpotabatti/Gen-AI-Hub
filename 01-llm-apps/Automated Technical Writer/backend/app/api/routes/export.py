"""
Export API routes — convert generated docs to downloadable formats.

Routes:
  POST /api/export/markdown  — Combine all sections into one .md file
  POST /api/export/html      — Convert combined markdown to HTML
"""
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from app.models.schemas import ExportRequest

router = APIRouter(prefix="/api/export", tags=["export"])
logger = logging.getLogger(__name__)


def _combine_sections(request: ExportRequest) -> str:
    """
    Merge all generated sections in doc_plan order into a single markdown string.
    """
    parts = []
    for section in request.doc_plan.sections:
        content = request.sections_content.get(section.id)
        if content:
            parts.append(content.strip())
    return "\n\n---\n\n".join(parts)


@router.post("/markdown")
async def export_markdown(request: ExportRequest):
    """
    Combine all generated sections into a single downloadable Markdown file.
    """
    try:
        combined = _combine_sections(request)
        filename = f"{request.doc_plan.project_name.replace(' ', '_').lower()}_docs.md"
        return Response(
            content=combined,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        logger.exception("Markdown export failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/html")
async def export_html(request: ExportRequest):
    """
    Convert the combined markdown documentation to a styled HTML file.
    """
    try:
        import markdown as md_lib

        combined = _combine_sections(request)
        project_name = request.doc_plan.project_name

        html_body = md_lib.markdown(
            combined,
            extensions=["fenced_code", "tables", "toc", "attr_list"],
        )

        # Wrap in a clean, styled HTML template
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{project_name} — Documentation</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f0f14; color: #e2e8f0; line-height: 1.7; }}
    .container {{ max-width: 860px; margin: 0 auto; padding: 2rem 1.5rem; }}
    h1, h2, h3, h4 {{ color: #f8fafc; margin: 2rem 0 1rem; }}
    h1 {{ font-size: 2.5rem; border-bottom: 2px solid #7c3aed; padding-bottom: 0.5rem; }}
    h2 {{ font-size: 1.8rem; color: #a78bfa; }}
    h3 {{ font-size: 1.3rem; color: #7dd3fc; }}
    p {{ margin-bottom: 1rem; }}
    pre {{ background: #1e1b2e; border: 1px solid #2d2b55; border-radius: 8px;
           padding: 1.25rem; overflow-x: auto; margin: 1.5rem 0; }}
    code {{ font-family: 'Fira Code', 'Cascadia Code', monospace; font-size: 0.88rem; }}
    p code {{ background: #1e1b2e; color: #a78bfa; padding: 2px 6px; border-radius: 4px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 1.5rem 0; }}
    th, td {{ border: 1px solid #2d2b55; padding: 0.75rem 1rem; text-align: left; }}
    th {{ background: #1e1b2e; color: #a78bfa; }}
    hr {{ border: none; border-top: 1px solid #2d2b55; margin: 2rem 0; }}
    a {{ color: #7dd3fc; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    ul, ol {{ margin: 1rem 0 1rem 2rem; }}
    li {{ margin-bottom: 0.4rem; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>{project_name}</h1>
    {html_body}
  </div>
</body>
</html>"""

        filename = f"{project_name.replace(' ', '_').lower()}_docs.html"
        return Response(
            content=html,
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        logger.exception("HTML export failed")
        raise HTTPException(status_code=500, detail=str(e))
