# Dishcovery


https://github.com/user-attachments/assets/b6b24de3-9613-499e-b1b2-9321dfc30657


## Setup Instructions

1. Create a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Set Google Gemini API Key:
- Create a `.env` file in the project root
- Add your Google Gemini API key: `GOOGLE_API_KEY=your_api_key_here`

4. Run the app:
```
streamlit run app.py
```

## Features
- Generate recipes based on available ingredients
- Uses Google Gemini `gemini-2.0-flash-exp` model to create creative recipes
- Simple and intuitive interface

## Requirements
- streamlit==1.30.0
- google-generativeai==0.7.2
- python-dotenv==1.0.0


