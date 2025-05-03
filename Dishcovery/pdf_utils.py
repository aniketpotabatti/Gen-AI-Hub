import os
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def find_system_font():
    """Find a suitable system font for PDF generation."""
    font_paths = [
        os.path.join(os.getenv('WINDIR', ''), 'Fonts', 'arial.ttf'),
        os.path.join(os.getenv('WINDIR', ''), 'Fonts', 'Arial.ttf'),
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/Library/Fonts/Arial.ttf'
    ]
    
    for path in font_paths:
        if os.path.exists(path):
            return path
    return None

def generate_pdf(recipe_text):
    """Generate a PDF from recipe text with professional formatting."""
    # Try to register a system font
    font_path = find_system_font()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont('CustomFont', font_path))
        except Exception:
            pass  # Fallback to default fonts if registration fails

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                            rightMargin=72, leftMargin=72, 
                            topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    
    # Custom styles with fallback fonts
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Title'],
        fontName='CustomFont' if 'CustomFont' in pdfmetrics._fonts else 'Helvetica',
        fontSize=16,
        textColor=HexColor('#2C3E50'),
        spaceAfter=12
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='CustomFont' if 'CustomFont' in pdfmetrics._fonts else 'Helvetica',
        fontSize=11,
        textColor=HexColor('#34495E'),
        leading=14
    )
    
    # Parse recipe sections
    sections = recipe_text.split('\n\n')
    story = []
    
    # Title
    story.append(Paragraph(sections[0], title_style))
    story.append(Spacer(1, 12))
    
    # Add other sections
    for section in sections[1:]:
        story.append(Paragraph(section, body_style))
        story.append(Spacer(1, 6))
    
    doc.build(story)
    buffer.seek(0)
    return buffer
