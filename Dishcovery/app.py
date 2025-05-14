import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from pdf_utils import generate_pdf
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')

if not api_key:
    st.error("🔴 Google API Key not found.")
    st.stop()

genai.configure(api_key=api_key)


def generate_recipe(ingredients, dietary_prefs=None, recipe_type=None, cuisine=None):
    """Generate a recipe based on given ingredients and preferences using Google Gemini API
    
    Args:
        ingredients (list): List of ingredients to use
        dietary_prefs (str, optional): Dietary restrictions (e.g., vegan, vegetarian)
        recipe_type (str, optional): Type of recipe (e.g., main course, dessert)
        cuisine (str, optional): Preferred cuisine style
    """
    if not ingredients:
        st.warning("⚠️ Please enter at least one ingredient.")
        return ""

    # Validate ingredients against dietary preferences
    non_vegan = ['meat', 'chicken', 'beef', 'pork', 'fish', 'egg', 'milk', 'cream', 'cheese', 'butter', 'honey']
    non_vegetarian = ['meat', 'chicken', 'beef', 'pork', 'fish']
    
    if dietary_prefs == 'vegan':
        conflicts = [ing for ing in ingredients if any(non_veg in ing.lower() for non_veg in non_vegan)]
        if conflicts:
            return f"⚠️ Cannot generate a vegan recipe with these ingredients: {', '.join(conflicts)}. Please remove them or change dietary preference."
    elif dietary_prefs == 'vegetarian':
        conflicts = [ing for ing in ingredients if any(non_veg in ing.lower() for non_veg in non_vegetarian)]
        if conflicts:
            return f"⚠️ Cannot generate a vegetarian recipe with these ingredients: {', '.join(conflicts)}. Please remove them or change dietary preference."

    try:
        model = genai.GenerativeModel(
            'gemini-1.5-flash',
            generation_config={
                'temperature': 0.7,
                'max_output_tokens': 1024,
            },
            safety_settings=[
                {'category': 'HARM_CATEGORY_HARASSMENT', 'threshold': 'BLOCK_MEDIUM_AND_ABOVE'},
                {'category': 'HARM_CATEGORY_HATE_SPEECH', 'threshold': 'BLOCK_MEDIUM_AND_ABOVE'},
                {'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'threshold': 'BLOCK_MEDIUM_AND_ABOVE'},
                {'category': 'HARM_CATEGORY_DANGEROUS_CONTENT', 'threshold': 'BLOCK_MEDIUM_AND_ABOVE'}
            ]
        )

        # Build dietary requirements string
        requirements = []
        if dietary_prefs:
            requirements.append(f"Must be {dietary_prefs}")
        if recipe_type:
            requirements.append(f"Should be a {recipe_type}")
        if cuisine:
            requirements.append(f"Follow {cuisine} cuisine style")
        requirements_str = ' and '.join(requirements)

        # Enhances prompt with requirements
        prompt = (
            f"Create a detailed, delicious-sounding recipe using ONLY these ingredients if possible: {', '.join(ingredients)}. "
            f"{requirements_str + '. ' if requirements_str else ''}"
            "If essential complementary ingredients are missing (like oil, salt, pepper, water), you can assume they are available. "
            "The recipe should include:\n"
            "- **Recipe Title** (Creative and appealing)\n"
            "- **Description** (Brief, enticing summary)\n"
            "- **Prep time** (e.g., 15 minutes)\n"
            "- **Cook time** (e.g., 25 minutes)\n"
            "- **Total time** (e.g., 40 minutes)\n"
            "- **Servings** (e.g., 2 people)\n"
            "- **Difficulty** (e.g., Easy, Medium, Hard)\n"
            "- **Ingredients List** (Clearly formatted with quantities)\n"
            "- **Instructions** (Numbered steps, clear and concise)\n"
            "- **Optional: Tips or Variations**\n\n"
            "Format the output using Markdown for readability (bold headings, lists)."
        )

        response = model.generate_content(prompt)

        # Handle potential lack of response or blocked content
        if not response.parts:
             # Check if the prompt was blocked
            if response.prompt_feedback.block_reason:
                st.error(f"🚫 Recipe generation blocked due to: {response.prompt_feedback.block_reason.name}. Please adjust ingredients or try again.")
                return "Recipe generation blocked."
            else:
                st.error("🤔 Failed to generate recipe. The model didn't return content. Please try again.")
                return "Unable to generate recipe - empty response."

        return response.text.strip()

    except Exception as e:
        st.error(f"⚙️ Recipe Generation Error: {e}")
        return f"An error occurred: {str(e)}"


# --- Main Streamlit App ---
def main():
    st.set_page_config(page_title="🧑🏻‍🍳 AI Dishcovery", page_icon="🧑🏻‍🍳", layout="wide") # Use wide layout

    # --- Custom CSS ---
    st.markdown(
        r"""
        <style>
        /* Base theme adjustments */
        body {
            color: inherit; 
        }
        .main > div { /* Target the main block container */
             background-color: transparent; 
        }
        .stApp { /* Use default Streamlit theme */
             background-color: transparent;
        }
        .stSidebar > div:first-child { /* Sidebar styling */
             background-color: transparent; 
             padding: 1.5rem 1rem; 
        }

        /* Center content within the wide layout */
        .block-container {
            max-width: 750px; /* Max width for main content area */
            margin: 0 auto; /* Center the block */
            padding-top: 3rem;
            padding-bottom: 3rem;
        }

        /* Headings */
        h1, h2, h3 { color: #ff6d00 !important; font-weight: 700; }
        h1 { text-align: center; margin-bottom: 0.5em; }
        h3 { margin-top: 1.5em; margin-bottom: 0.8em; border-bottom: 1px solid #444; padding-bottom: 0.3em;}

        /* Text & Labels */
        .stMarkdown, p, label, .stTextInput label, .stSelectbox label {
            color: #e1e1e1 !important; /* Ensure text readability */
            font-size: 1.05em;
        }
        .stTextInput label, .stSelectbox label {
            font-weight: 600; /* Make labels slightly bolder */
            margin-bottom: 0.3em !important;
        }

        /* Input fields styling */
        .stTextInput > div > div > input, .stSelectbox > div > div {
            background: #222222;
            color: #e1e1e1;
            border-radius: 8px;
            border: 1px solid #4a4a5a; /* Subtle border */
        }
        .stTextInput > div > div > input:focus, .stSelectbox > div > div:focus-within {
             border-color: #F8F5E9; /* Highlight on focus */
             box-shadow: 0 0 0 2px rgba(255, 145, 77, 0.3);
        }

        /* Add margin specifically to sidebar selectboxes */
        .stSidebar .stSelectbox {
            margin-bottom: 0.1em; /* Reduce space below each selectbox */
        }

        /* Button styling */
        .stButton > button {
            background: linear-gradient(50deg, #222222 40%, #ff6d00 100%);
            color: #fff !important; /* Ensure white text */
            font-weight: 700; /* Bolder text */
            border-radius: 10px;
            padding: 0.8em 2.5em; /* Balanced padding */
            font-size: 1.1em;
            border: none; /* Remove default border */
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: transform 0.1s ease-out, box-shadow 0.1s ease-out;
            display: block; /* Make button block level */
            margin: 2em auto 0 auto; /* Center button */
            width: fit-content; /* Fit content width */
        }
        .stButton > button:hover {
            box-shadow: 0 6px 16px rgba(0,0,0,0.25);
            transform: translateY(-1px); /* Slight lift on hover */
        }
        .stButton > button:active {
            transform: translateY(0px); /* Press down effect */
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            background: linear-gradient(90deg, #ff6d00 40%, #ff914d 100%);
        }

        /* Expander styling */
        .st-expanderHeader {
            color: #ffb37a !important; /* Lighter orange for expander */
            font-weight: 600;
            font-size: 1.1em;
            border-radius: 8px;
            margin-bottom: 0.5em;
        }
        .st-expander {
             border: 1px solid #3a3a4a; /* Border for expander */
             border-radius: 8px;
             background: #23232d; /* Match card background */
             margin-bottom: 1.5em; /* Space below expander */
        }
        .st-expander > div > details > div { padding: 0.8em 1em; } /* Padding inside expander */

        /* Recipe Output Card */
        .recipe-output-card {
            background: #2a2a35; /* Slightly different background for output */
            border-radius: 14px;
            padding: 1.5em 2em;
            margin: 2em auto; /* Spacing around output */
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
            color: #e1e1e1;
            border: 1px solid #444;
        }
        .recipe-output-card h3 { /* Style subheader within output */
             color: #ffb37a !important;
             margin-top: 0.5em;
             margin-bottom: 0.8em;
             border-bottom: none;
        }
        .recipe-output-card p, .recipe-output-card li {
            line-height: 1.6; /* Improve readability */
        }

        /* Footer */
        footer {
            color: #888 !important;
            text-align: center;
            padding-top: 2em;
            padding-bottom: 1em;
        }
        footer a { color: #fff !important; text-decoration: none; }
        footer a:hover { color: #ccc !important; }
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- Header ---
    st.markdown("<h1>🧑🏻‍🍳 Dishcovery</h1>", unsafe_allow_html=True)
    
    # --- Sidebar Options ---
    st.sidebar.header("Choose your preferences")

    cuisine_options = [
        'Any', 'Italian', 'Mexican', 'Indian', 'Chinese', 'Mediterranean', 'American', 'Thai', 'French',
        'Spanish', 'Japanese', 'Korean', 'Vietnamese', 'British', 'Russian', 'Greek', 'Moroccan',
        'Brazilian', 'Cajun', 'Caribbean', 'Filipino', 'Hawaiian', 'Polish', 'Portuguese', 'Sushi', 'Turkish'
    ]
    selected_cuisine = st.sidebar.selectbox(
        "Cuisine Style",
        cuisine_options,
        index=0, # Default to 'Any'
        help="Pick a cuisine or leave as 'Any' for flexibility."
    )

    diet_options = [
        'None', 'Vegetarian', 'Vegan', 'Gluten-Free',
        'Low-Carb', 'Keto', 'Dairy-Free', 'Pescatarian'
    ]
    selected_diet = st.sidebar.selectbox(
        "Dietary Needs",
        diet_options,
        index=0, # Default to 'None'
        help="Select if you have any dietary preferences or restrictions."
    )

    # --- Main Input Area ---
    ingredient_input = st.text_input(
        "What ingredients do you have?",
        placeholder="Enter your ingredients...",
        help="List the main ingredients you want to use, separated by commas."
    )

    def handle_pdf_generation(recipe_text, recipe_title):
        """Handle PDF generation and download"""
        try:
            safe_name = re.sub(r'[^\w\-_\. ]', '_', recipe_title).replace(' ', '_')
            pdf_bytes = generate_pdf(recipe_text)
            if not pdf_bytes:
                st.error("Failed to generate PDF")
                return False
            return pdf_bytes, safe_name
        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            st.error(f'Could not generate PDF: {str(e)}')
            return False

    # --- Generate Button ---
    generate_btn = st.button("🍽️ Generate Recipe", 
                           help="Click to generate a recipe based on your selections.",
                           key="generate_recipe_btn")

    # Store recipe in session state
    if 'recipe_text' not in st.session_state:
        st.session_state.recipe_text = None
        st.session_state.recipe_title = None

    # Recipe Generation and Display 
    if generate_btn:
        if not ingredient_input or not ingredient_input.strip():
            st.warning("🤔 Please enter some ingredients first!")
        else:
            ingredients = [ing.strip() for ing in ingredient_input.split(',') if ing.strip()]
            if len(ingredients) < 1:
                st.warning("☹️ Please enter at least one ingredient.")
            else:
                with st.spinner('✨ Crafting your perfect recipe... Please wait.'):
                    recipe_text = generate_recipe(
                        ingredients=ingredients,
                        dietary_prefs=selected_diet if selected_diet != 'None' else None,
                        cuisine=selected_cuisine if selected_cuisine != 'Any' else None
                    )
                    st.session_state.recipe_text = recipe_text

                error_msgs = ["Unable to generate recipe", "Recipe generation blocked", "Cannot generate"]
                if any(msg in recipe_text for msg in error_msgs):
                    st.markdown(f"<p style='color:#ff6b6b;'>{recipe_text}</p>", unsafe_allow_html=True)
                else:
                    title_pattern = r'^#\s*(.+?)(?:\n|$)'
                    m = re.search(title_pattern, recipe_text, re.MULTILINE | re.IGNORECASE)
                    recipe_title = m.group(1).strip() if m and m.group(1).strip() else 'Recipe'
                    st.session_state.recipe_title = recipe_title

                    # --- Clean recipe markdown ---
                    recipe_md = re.sub(title_pattern + r'.*', '', recipe_text, flags=re.MULTILINE | re.IGNORECASE)
                    recipe_md = re.sub(r'^##\s*(.*)$', r'### \1', recipe_md, flags=re.MULTILINE)

                    st.markdown(f"### {recipe_title}")
                    st.markdown(recipe_md, unsafe_allow_html=True)

    # Shows PDF export button only if the recipe is generated
    if st.session_state.recipe_text and st.session_state.recipe_title:
        # Generate PDF only when needed
        if 'pdf_bytes' not in st.session_state or 'pdf_name' not in st.session_state:
            result = handle_pdf_generation(st.session_state.recipe_text, 
                                         st.session_state.recipe_title)
            if result:
                st.session_state.pdf_bytes, st.session_state.pdf_name = result
        
        # Shows download button if PDF is ready
        if 'pdf_bytes' in st.session_state and 'pdf_name' in st.session_state:
            st.download_button('Get A Copy',
                             data=st.session_state.pdf_bytes,
                             file_name=f"{st.session_state.pdf_name}_recipe.pdf",
                             mime='application/pdf',
                             use_container_width=True,
                             key="export_pdf_btn")

    # --- Footer ---
    st.markdown("---") # Use markdown for separator
    st.markdown(
        """
        <div style='text-align:center; color: #888;'>
            Powered by <b>Google Gemini AI</b> | View on <a href='https://github.com/aniketpotabatti/GenAIHub/tree/main/Dishcovery' target='_blank'>GitHub</a>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
