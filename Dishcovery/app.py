import os
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from pdf_utils import generate_pdf
import re

# Load environment variables
load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')

if not api_key:
    st.error("🔴 Google API Key not found.")
    st.stop()

genai.configure(api_key=api_key)


def generate_recipe(ingredients):
    """Generate a recipe based on given ingredients using Google Gemini API"""
    if not ingredients:
        st.warning("⚠️ Please enter at least one ingredient.")
        return ""

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

        # Enhanced prompt
        prompt = (
            f"Create a detailed, delicious-sounding recipe using ONLY these ingredients if possible: {', '.join(ingredients)}. "
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
        /* Base dark theme adjustments */
        body {
            color: #e1e1e1; /* Light gray text */
        }
        .main > div { /* Target the main block container */
             background-color: #181820; /* Dark background */
        }
        .stApp { /* Ensure app background is dark */
             background-color: #181820;
        }
        .stSidebar > div:first-child { /* Sidebar styling */
             background: #2a2a35; /* Match output card background */
             padding: 1.5rem 1rem; /* Add horizontal padding */
        }

        /* Center content within the wide layout */
        .block-container {
            max-width: 750px; /* Max width for main content area */
            margin: 0 auto; /* Center the block */
            padding-top: 3rem;
            padding-bottom: 3rem;
        }

        /* Headings */
        h1, h2, h3 { color: #ff914d !important; font-weight: 700; }
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
            background: #2e2e38;
            color: #e1e1e1;
            border-radius: 8px;
            border: 1px solid #4a4a5a; /* Subtle border */
        }
        .stTextInput > div > div > input:focus, .stSelectbox > div > div:focus-within {
             border-color: #ff914d; /* Highlight on focus */
             box-shadow: 0 0 0 2px rgba(255, 145, 77, 0.3);
        }

        /* Add margin specifically to sidebar selectboxes */
        .stSidebar .stSelectbox {
            margin-bottom: 0.1em; /* Reduce space below each selectbox */
        }

        /* Button styling */
        .stButton > button {
            background: linear-gradient(90deg, #ff914d 40%, #ff6d00 100%);
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

        /* Download Button */
        .stDownloadButton > button {
            background-color: #4caf50;
            color: white !important;
            font-weight: 600;
            border-radius: 8px;
            padding: 0.6em 1.8em;
            border: none;
            margin-top: 1em;
            transition: background-color 0.2s;
        }
        .stDownloadButton > button:hover {
             background-color: #388e3c;
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
        placeholder="e.g. chicken, tomatoes, pasta, olive oil",
        help="List the main ingredients you want to use, separated by commas."
    )

    # --- Generate Button ---
    generate_btn = st.button("🍽️ Generate Recipe", help="Click to generate a recipe based on your selections.")

    # --- Recipe Generation and Display ---
    if generate_btn:
        if ingredient_input:
            ingredients = [ing.strip() for ing in ingredient_input.split(',') if ing.strip()]
            if len(ingredients) < 1:
                st.warning("⚠️ Please enter at least one ingredient.")
            else:
                with st.spinner('✨ Crafting your perfect recipe... Please wait.'):
                    recipe_text = generate_recipe(ingredients)

                # --- Refined Recipe Output ---
                if "Unable to generate recipe" in recipe_text or "Recipe generation blocked" in recipe_text:
                    st.markdown(f"<p style='color:#ff6b6b;'>{recipe_text}</p>", unsafe_allow_html=True)
                else:
                    # Extract title
                    m = re.search(r'^#\\s*(.+?)(?:\\n|$)', recipe_text,
                                  re.MULTILINE|re.IGNORECASE)
                    recipe_title = m.group(1).strip() if m else 'Recipe'

                    # Strip the top-level header, bump ## to ###, leave the rest
                    recipe_md = re.sub(
                        r'^#\\s*(.+?)(?:\\n|$).*', '', recipe_text,
                        flags=re.MULTILINE|re.IGNORECASE
                    )
                    recipe_md = re.sub(
                        r'^##\\s*(.*)$', r'### \1',
                        recipe_md, flags=re.MULTILINE
                    )

                    # Display the recipe
                    st.markdown(recipe_md, unsafe_allow_html=True)

                    # Export PDF button at the end of the recipe
                    export = st.button('Get A Copy', use_container_width=True)
                    if export:
                        try:
                            safe_name = re.sub(r'[^\w\-_\. ]', '_', recipe_title).replace(' ', '_')
                            buf = generate_pdf(recipe_text)
                            st.download_button(
                                'Download Recipe PDF',
                                data=buf.getvalue(),
                                file_name=f'{safe_name}_recipe.pdf',
                                mime='application/pdf',
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f'Could not generate PDF: {e}')

        else:
            st.warning("🤔 Please enter some ingredients first!")

    # --- Footer ---
    st.markdown("---") # Use markdown for separator
    st.markdown(
        """
        <div style='text-align:center; color: #888;'>
            Powered by <b>Google Gemini AI</b> | View on <a href='https://github.com/your-repo' target='_blank'>GitHub</a>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()