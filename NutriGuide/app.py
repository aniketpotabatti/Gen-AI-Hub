import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
load_dotenv() 
from PIL import Image

genai.configure(api_key = os.getenv("GOOGLE_API_KEY"))

# Generate a response from Gemini
def get_gemini_response(input,image,prompt):
    model = genai.GenerativeModel('gemini-pro-vision')
    response = model.generate_content([input,image[0],prompt])
    return response.text

def input_image_setup(uploaded_file):
    # Check if a file has been uploaded
    if uploaded_file is not None:
        # Read the file into bytes
        bytes_data = uploaded_file.getvalue()
        image_parts = [
            {
                "mime_type": uploaded_file.type,  # Get the mime type of the uploaded file
                "data": bytes_data
            }
        ]
        return image_parts
    else:
        raise FileNotFoundError("No file uploaded")
    
# Initialize our streamlit app 
st.set_page_config(page_title="Nutriguide App", layout="wide")

st.header("Nutriguide Health App")
with st.form("input_form"):
    input_text = st.text_input("Input Prompt: ", key="input")
    uploaded_file = st.file_uploader("Upload an image", ["jpg", "png"])
    submit = st.form_submit_button("Calculate the total calories")

if uploaded_file is not None:
    try:
        image = Image.open(uploaded_file)
        st.image(image, caption='Uploaded Image', use_column_width=True)
    except Exception as e:
        st.error("Error opening image: " + str(e))

input_prompt = """
            You are an expert in nutritionist where you need to see the food items from the image
            and provide information on how much calories they contain. Please describe each item 
            and its corresponding calories and provide information on how much calories they contain
            in below format

            1. item 1 - no.of calories
            2. item 3 - no.of calories
            -----
            -----
    Finally, you can also mention whether the food is healthy or not and also mention the 
    percentage split of the ratio of carbohydrates, fats, fibers, sugar and other important 
    things required in our diet.
"""

if submit:
    try:
        image_data = input_image_setup(uploaded_file)
        response = get_gemini_response(input_text, image_data, input_prompt)
        if response:
            st.subheader("The Response is")
            st.write(response)
        else:
            st.error("Received an empty response from the model.")
    except Exception as e:
        st.error("An error occurred: " + str(e))    # NutriGuide App
