"""
Author: @aniketpotabatti
Project: NutriGuide App
Created: 2024-03-22
"""

import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from PIL import Image

# Load API key from environment variable
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Input Prompt Field
input_prompt = """
You are an expert nutritionist. Analyze the food items in the image and provide:
- Calories for each item (list format)
- Whether the food is healthy or not
- Percentage split of carbohydrates, fats, fibers, sugar, and other important nutrients
Format:
1. item 1 - no.of calories
2. item 2 - no.of calories
...
Summary at the end.
"""

# Function to generate response from Gemini 
def get_gemini_response(input_text, image_data, prompt):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content([input_text, image_data[0], prompt])
        return response.text
    except Exception as e:
        st.error("Error generating response: " + str(e))
        return None

# Function to setup input image
def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        try:
            bytes_data = uploaded_file.getvalue()
            image_parts = [
                {
                    "mime_type": uploaded_file.type,
                    "data": bytes_data
                }
            ]
            return image_parts
        except Exception as e:
            st.error("Error processing image: " + str(e))
            return None
    else:
        st.error("No file uploaded")
        return None

# --- Streamlit Page Config ---
st.set_page_config(page_title="NutriGuide App", layout="wide", page_icon="🥗")

# --- Custom CSS for style ---
st.markdown(
    """
    <style>
    .main {background-color:rgb(0, 0, 0);}
    .stApp {background-color: #f8fafc;}
    .stButton>button {background-color: #4CAF50; color: white; font-weight: bold;}
    .stTextInput>div>input {background-color: #fffbe7;}
    .stFileUploader {background-color: #fffbe7;}
    .stHeader {color: #4CAF50;}
   
    div.st-expanderHeader, div.st-expanderHeader > span {
    font-size: 7.2rem !important;
    font-weight: bold !important;
    color: #4CAF50 !important;
}
    .stButton > button:hover, .stButton > button:active, .stButton > button:focus {
    background-color: #388e3c !important;
    color: #4CAF50 !important;
    border: none;
    transition: color 0.2s;
</style>
    """,
    unsafe_allow_html=True
)

# --- App Title ---
st.markdown("""
<h1 style='color:#4CAF50; font-size:2.5rem; text-align:center;'>🥗 NutriGuide App</h1>
""", unsafe_allow_html=True)

st.write("")

# --- Instructions/Help ---
with st.expander("▼ Instructions", expanded=False):
    st.markdown("""
    <ol style='font-size:1.15rem; font-weight:bold;'>
      <li>Type your food-related query or prompt.</li>
      <li>Upload a food image (jpg or png).</li>
      <li>Click 'Analyze & Calculate Calories' to get detailed nutritional info.</li>
      <li>See results, suggestions, and food health analysis!</li>
    </ol>
    """, unsafe_allow_html=True)

st.write("")

# --- Main Layout ---
col1, col2 = st.columns([1, 1])

with col1:
    
    with st.form("input_form"):
        input_text = st.text_input("Input Prompt", key="input", placeholder="Describe your meal or ask a nutrition question...")
        uploaded_file = st.file_uploader("Upload a food image", ["jpg", "png"])
        submit = st.form_submit_button("Analyze & Calculate Calories")

    if uploaded_file is not None:
        try:
            image = Image.open(uploaded_file)
            st.image(image, caption='🍽️ Uploaded Image', use_column_width=True)
        except Exception as e:
            st.error("Error opening image: " + str(e))

with col2:
    st.markdown("### 📊 Results & Analysis")
    tab1, tab2 = st.tabs(["Nutritional Breakdown", "Diet Suggestions"])
    with tab1:
        if submit:
            with st.spinner('Analyzing image and generating nutritional info...'):
                image_data = input_image_setup(uploaded_file)
                if image_data is not None:
                    response = get_gemini_response(input_text, image_data, input_prompt)
                    if response:
                        st.success("Analysis complete!")
                        st.markdown(f"<div style='padding:18px; border-radius:10px;'><b>🔎 Results:</b><br>{response}</div>", unsafe_allow_html=True)
                    else:
                        st.error("Received an empty response from the model.")
    with tab2:
        if submit:
            st.info("💡 Try to balance your meals with a good mix of carbs, proteins, fats, and fibers. Drink plenty of water and avoid excessive sugar!")

# --- Gemini Input Prompt ---
input_prompt = """
You are an expert nutritionist. Analyze the food items in the image and provide:
- Calories for each item (list format)
- Whether the food is healthy or not
- Percentage split of carbohydrates, fats, fibers, sugar, and other important nutrients
Format:
1. item 1 - no.of calories
2. item 2 - no.of calories
...
Summary at the end.
"""

