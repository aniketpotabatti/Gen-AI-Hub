# Dishcovery 🍲

https://github.com/user-attachments/assets/1be63955-3163-4912-ad43-da55a936935c

Discover delicious recipes with the ingredients you already have at home! Dishcovery uses Google's Gemini AI to generate creative and personalized recipes based on your preferences.

## Key Features

- **Ingredient-Based Recipe Generation**: Enter the ingredients you have, and get a complete recipe in seconds.
- **Advanced Customization**: Filter recipes by dietary needs, cuisine type, cooking time, and difficulty.
- **Allergy-Aware**: Exclude common allergens to ensure your recipes are safe for you and your family.
- **Download as PDF**: Save your favorite recipes as a beautifully formatted PDF file for offline access.
- **Powered by Gemini**: Utilizes the `gemini-2.5-flash` model for fast and creative recipe ideas.

## Getting Started

Follow these steps to get Dishcovery up and running on your local machine.

### Prerequisites

- Python 3.8 or higher
- An active Google Gemini API Key

### Installation

1.  **Create and activate a virtual environment:**
    ```bash
    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

2.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up your API key:**
    - Create a new file named `.env` in the root of the project.
    - Add your Google Gemini API key to the `.env` file as follows:
      ```
      GOOGLE_API_KEY="your_api_key_here"
      ```

### Run the App

Once the setup is complete, run the following command to start the Streamlit application:

```bash
streamlit run app.py
```

## Usage

1.  Enter the ingredients you have in the main text box.
2.  Use the sidebar to set your preferences (e.g., dietary, cuisine, allergies).
3.  Click "Generate Recipe" to get your custom recipe.
4.  If you like the recipe, click "Download PDF" to save it.
