"""
Author: @aniketpotabatti
Project: Dishcovery
Created: 2024-04-30
"""

import base64
from pathlib import Path

import streamlit as st
import google.generativeai as genai
from fpdf import FPDF

LOGO_PATH = Path(__file__).parent / "assets" / "Discovery logo.png"

st.set_page_config(
    page_title="Dishcovery - AI Recipe Generator",
    page_icon=str(LOGO_PATH),
    layout="wide"
)

# Custom CSS for advanced UI design (no main title)
st.markdown("""
<style>
/* Page background */
body {
    background: linear-gradient(135deg, #f0f4f8, #e0eafc);
    background-attachment: fixed;
    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

/* Card container for recipe output */
.recipe-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 24px;
    margin-top: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    line-height: 1.6;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #23272a, #191B1C);
}

/* Button enhancements */
.stButton > button {
    font-weight: bold;
    border-radius: 12px;
    padding: 10px 24px;
    transition: transform 0.1s ease;
}
.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}
</style>
""", unsafe_allow_html=True)

# Core Logic 
def generate_recipe_prompt(ingredients, dietary_prefs=None, recipe_type=None, cuisine=None, servings=None, allergies=None, cooking_time=None, difficulty=None):
    """Builds the prompt for the Gemini API."""
    requirements = []
    if dietary_prefs: requirements.append(f"Must be {dietary_prefs}")
    if recipe_type: requirements.append(f"Should be a {recipe_type}")
    if cuisine: requirements.append(f"Follow {cuisine} cuisine style")
    if servings: requirements.append(f"For {servings} servings")
    if allergies and "None" not in allergies: requirements.append(f"Excluding ingredients like {', '.join(allergies)}")
    if cooking_time and cooking_time != "None": requirements.append(f"That takes {cooking_time} to cook")
    if difficulty and difficulty != "None": requirements.append(f"With {difficulty} difficulty")
    requirements_str = ' and '.join(requirements)

    return (
        f"Create a detailed, delicious-sounding recipe using ONLY these ingredients if possible: {', '.join(ingredients)}. "
        f"{requirements_str + '. ' if requirements_str else ''}"
        "If essential complementary ingredients are missing (like oil, salt, pepper, water), you can assume they are available. "
        "The recipe should include:\n\n"
        "- **Recipe Title** (Creative and appealing)\n"
        "- **Description** (Brief, enticing summary)\n"
        "- **Prep time**, \n **Cook time**, \n **Total time** (e.g., 15 minutes)\n"
        "- **Servings** (e.g., 2 people)\n"
        "- **Difficulty** (e.g., Easy, Medium, Hard)\n"
        "- **Ingredients List** (Clearly formatted with quantities)\n"
        "- **Instructions** (Numbered steps, clear and concise)\n"
        "- **Optional: Tips or Variations**\n\n"
        "Format the output using Markdown for readability (bold headings, lists)."
    )

def call_gemini_api(prompt):
    """Calls the Gemini API and returns the response text."""
    try:
        model = genai.GenerativeModel(
            'gemini-2.5-flash',
            generation_config={'temperature': 0.7, 'max_output_tokens': 4000},
            safety_settings=[
                {'category': 'HARM_CATEGORY_HARASSMENT', 'threshold': 'BLOCK_MEDIUM_AND_ABOVE'},
                {'category': 'HARM_CATEGORY_HATE_SPEECH', 'threshold': 'BLOCK_MEDIUM_AND_ABOVE'},
                {'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'threshold': 'BLOCK_MEDIUM_AND_ABOVE'},
                {'category': 'HARM_CATEGORY_DANGEROUS_CONTENT', 'threshold': 'BLOCK_MEDIUM_AND_ABOVE'}
            ]
        )
        response = model.generate_content(prompt)
        
        if not response.parts:
            if response.prompt_feedback.block_reason:
                return f"Recipe generation blocked due to: {response.prompt_feedback.block_reason.name}. Please adjust ingredients or try again."
        return response.text.strip()
    except Exception as e:
        return f"An error occurred: {str(e)}"

def create_pdf(text):
    """Creates a PDF from the given text with modern formatting."""

    # Sanitize text by replacing Unicode characters
    replacements = {
        "•": "*", "●": "*", "◦": "*", "–": "-", "—": "-", "−": "-",
        '“': '"', '”': '"', '‘': "'", '’': "'", "…": "...", "×": "x",
        "©": "(c)", "®": "(r)", "™": "(tm)", "°": "deg", "±": "+/-",
        "≠": "!=", "≤": "<=", "≥": ">=", "∞": "inf", "∑": "sum",
        "∏": "prod", "∫": "int", "∂": "diff", "√": "sqrt", "∆": "delta",
        "∇": "grad", "→": "->", "←": "<-", "↑": "^", "↓": "v", "↔": "<->",
        "⇒": "=>", "⇐": "<=", "⇑": "^^", "⇓": "vv", "℉": "F", "℃": "C",
        "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR", "§": "section",
        "¶": "para", "†": "+", "‡": "++", "‰": "%", "‱": "/10000"
    }
    for unicode, ascii_char in replacements.items():
        text = text.replace(unicode, ascii_char)
    text = ''.join(char for char in text if ord(char) < 128 or char in '\n\r\t')

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    font_family = 'Arial'  # Default font
    try:
        pdf.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        font_family = 'DejaVu'  # Switch to DejaVu if loaded successfully
    except (RuntimeError, FileNotFoundError):
        pass  # Keep Arial if DejaVu is not found

    def set_font_style(pdf, style='', size=11):
        pdf.set_font(font_family, style, size)

    # Define formatting styles for markdown elements
    styles = {
        '##': {'size': 18, 'style': 'B', 'align': 'C', 'ln': 14, 'space': 10},
        '###': {'size': 16, 'style': 'B', 'align': 'C', 'ln': 12, 'space': 8},
        '####': {'size': 14, 'style': 'B', 'ln': 10, 'space_before': 8, 'space_after': 4},
        '**': {'size': 12, 'style': 'B', 'ln': 8, 'space_before': 6, 'space_after': 3},
        '*': {'size': 11, 'style': '', 'ln': 6, 'bullet': True},
        'default': {'size': 11, 'style': '', 'ln': 6}
    }

    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue

        if line.startswith('## '):
            style = styles['##']
            content = line[3:].strip()
            set_font_style(pdf, style['style'], style['size'])
            pdf.multi_cell(0, style['ln'], content, align=style['align'], ln=1)
            if style.get('space'): pdf.ln(style['space'])
        elif line.startswith('### '):
            style = styles['###']
            content = line[4:].strip()
            if style.get('space_before'): pdf.ln(style['space_before'])
            set_font_style(pdf, style['style'], style['size'])
            pdf.multi_cell(0, style['ln'], content, ln=1)
            if style.get('space_after'): pdf.ln(style['space_after'])

        elif line.startswith('### '):
            style = styles['###']
            content = line[4:].strip()
            if style.get('space_before'): pdf.ln(style['space_before'])
            set_font_style(pdf, style['style'], style['size'])
            pdf.multi_cell(0, style['ln'], content, ln=1)
            if style.get('space_after'): pdf.ln(style['space_after'])

        elif line.startswith('**') and line.endswith('**'):
            style = styles['**']
            content = line[2:-2].strip()
            if style.get('space_before'): pdf.ln(style['space_before'])
            set_font_style(pdf, style['style'], style['size'])
            pdf.multi_cell(0, style['ln'], content, ln=1)
            if style.get('space_after'): pdf.ln(style['space_after'])
            
        elif line.startswith('*'):
            style = styles['*']
            set_font_style(pdf, style['style'], style['size'])
            content = line[2:].strip()  # Get content after '* ' and strip whitespace
            
            pdf.cell(5)  # Indentation for the bullet
            pdf.write(style['ln'], '* ')
            
            # Process the rest of the line for inline bolding
            parts = content.split('**')
            for i, part in enumerate(parts):
                if i % 2 == 1:  # Bold part
                    set_font_style(pdf, 'B', style['size'])
                else:  # Regular part
                    set_font_style(pdf, '', style['size'])
                if part:
                    pdf.write(style['ln'], part)
            pdf.ln(style['ln'])
        else:
            style = styles['default']
            set_font_style(pdf, style['style'], style['size'])
            parts = line.split('**')
            for i, part in enumerate(parts):
                if i % 2 == 1:
                    set_font_style(pdf, 'B', style['size'])
                else:
                    set_font_style(pdf, '', style['size'])
                if part:
                    pdf.write(style['ln'], part)
            pdf.ln(style['ln'])

    return bytes(pdf.output())

st.markdown("""<style>
.stButton > button {
    font-weight: bold;
    border-radius: 12px;
    padding: 10px 24px;
}
.stButton > button[kind='primary'] {
    background-image: radial-gradient(circle, #7bd47f, #FFFFFF);
    border: 2px solid #000000;
    color: black;
}
.stButton > button[kind='secondary'] {
    background-image: radial-gradient(circle, #7bd47f, #FFFFFF);
    border: 1px solid #000000;
    color: black !important;
}
.stButton > button[kind='secondary'][aria-label='Update Recipe'] {
    background-color: #2196F3 !important;
    color: white !important;
    border: 3px solid #2196F3 !important;
}
.stButton > button[kind='secondary'][aria-label='Download PDF'] {
    background-color: #4CAF50 !important;
    color: white !important;
    border: none;
}
</style>""", unsafe_allow_html=True)

# Inject app logo and title into the native Streamlit header via CSS
logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
st.markdown(f"""
<style>
header[data-testid="stHeader"] {{
    position: relative;
    overflow: visible;
}}
header[data-testid="stHeader"]::before {{
    content: "";
    position: absolute;
    left: 41%;
    top: 38%;
    transform: translate(-50%, -50%);
    width: 500px;
    height: 100%;
    background: url("data:image/png;base64,{logo_b64}") center / contain no-repeat;
    filter:drop-shadow(0 0 14px rgb(197, 236, 198, 0.75));
    z-index: 1000;
    pointer-events: none;
}}
</style>
""", unsafe_allow_html=True)
st.markdown("#### Discover recipes with the ingredients you have!")
st.sidebar.title("Preferences")

# API key input
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

st.session_state.api_key = st.sidebar.text_input(
    "Google API Key", 
    type="password", 
    value=st.session_state.api_key,
    key="api_key_input"
)

if st.session_state.api_key:
    genai.configure(api_key=st.session_state.api_key)
elif 'recipe' not in st.session_state:
    st.sidebar.warning("Please enter your Google API key to generate recipes.")

dietary_prefs = st.sidebar.selectbox("Dietary Preference", ["None", "Vegetarian", "Vegan", "Non-Vegetarian", "Gluten-Free", "Dairy-Free", "Keto", "Paleo", "Low-Carb", "Low-Fat", "High-Protein", "Mediterranean", "Pescatarian"], key="dietary_prefs")
cuisine = st.sidebar.selectbox("Cuisine", ["None", "Italian", "Mexican", "Indian", "Chinese", "Japanese", "Thai", "French", "Mediterranean", "American", "Greek", "Spanish", "Middle Eastern", "Korean", "Vietnamese", "Ethiopian", "Moroccan", "Caribbean", "Brazilian", "German", "Russian", "African", "Australian", "Peruvian", "Argentinian", "Turkish", "Pakistani", "Bengali", "Nepalese", "Sri Lankan", "Malaysian", "Indonesian", "Filipino", "Singaporean", "Burmese", "Cambodian", "Laotian", "Tibetan", "Mongolian", "Central American", "South American", "Eastern European", "Western European", "Northern European", "Southern European", "Oceanic", "Fusion", "Other"], key="cuisine")
allergies = st.sidebar.multiselect("Allergies", ["None", "Peanuts", "Tree Nuts", "Dairy", "Eggs", "Wheat", "Soy", "Fish", "Shellfish", "Sesame", "Mustard", "Celery", "Lupin", "Molluscs", "Sulphites"], key="allergies")
cooking_time = st.sidebar.selectbox("Cooking Time", ["None", "Under 15 minutes", "15-30 minutes", "30-60 minutes", "1-2 hours", "Over 2 hours"], key="cooking_time")
difficulty = st.sidebar.selectbox("Difficulty", ["None", "Easy", "Medium", "Hard"], key="difficulty")
servings = st.sidebar.number_input("Servings", min_value=1, value=2, key="servings")

def get_sidebar_preferences():
    """Gets all preferences from the sidebar controls."""
    return {
        'dietary_prefs': st.session_state.get('dietary_prefs', 'None'),
        'cuisine': st.session_state.get('cuisine', 'None'),
        'allergies': st.session_state.get('allergies', []),
        'cooking_time': st.session_state.get('cooking_time', 'None'),
        'difficulty': st.session_state.get('difficulty', 'None'),
        'servings': st.session_state.get('servings', 2)
    }

def handle_recipe_generation(ingredients_str):
    """Handles the recipe generation process."""
    if not ingredients_str:
        st.warning("Please enter at least one ingredient.")
        return
    
    with st.spinner("✨ Generating recipe..."):
        prefs = get_sidebar_preferences()
        prompt = generate_recipe_prompt(ingredients_str.split(','), **prefs)
        recipe_text = call_gemini_api(prompt)
        st.session_state.recipe = recipe_text

# Sidebar buttons
# Single column in sidebar for both buttons
if 'recipe' in st.session_state and st.session_state.get('ingredients_input'):
    if st.sidebar.button("Update Recipe", key="update_button", use_container_width=True):
        handle_recipe_generation(st.session_state.ingredients_input)
        st.rerun()

if st.sidebar.button("Reset", key="reset_button", use_container_width=True):
    st.session_state.clear()
    st.rerun()

# Ingredients input and Generate button below the sidebar, one column layout
ingredients = st.text_input("Enter your ingredients (comma-separated)", key="ingredients_input")
if st.button("Generate Recipe", type="primary"):
    handle_recipe_generation(ingredients)

# Display the generated recipe inside a styled card
if 'recipe' in st.session_state:
    st.markdown(st.session_state.recipe)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Download button (styled via existing CSS)
    pdf_bytes = create_pdf(st.session_state.recipe)
    st.download_button(
        label="📄 Download PDF",
        data=pdf_bytes,
        file_name="recipe.pdf",
        mime="application/pdf",
        key="download_button",
        type="secondary"
    )
