# 🔍Data Science Project Reviewer

Data Science Project Reviewer is a Streamlit web application designed to automatically review machine learning and data science repositories. The application accepts a public GitHub repository URL, extracts text-based files (including Python scripts, Jupyter notebooks, config files, and documentation), packages them, and forwards the content to a Gemini model for structured analysis.

* **Author:** @aniketpotabatti
* **Created:** Aug 2024

The analysis scores and evaluates the repository across eight key categories:
1. Project Organization
2. README Quality
3. Feature Engineering
4. Model Choice
5. Evaluation Metrics
6. Deployment Readiness
7. Documentation Quality
8. Code Structure

## Features

- Dynamic Repository Download: Automatically fetches repository zipballs from GitHub based on the branch or reference.
- Jupyter Notebook Extraction: Extracts markdown and source code content from Jupyter Notebooks (IPYNB files) to optimize LLM input context.
- Advanced Caching: Employs Streamlit session state caching to prevent review resets and duplicate API requests during user interactions.
- Responsive Metrics Grid: Visualizes results through a clean dark-mode dashboard styled with Custom HSL colors and a premium font family.
- Breakdown Tabs: Separates review output into categorized sections containing critique notes, strengths, and step-by-step actionable recommendations.

## Prerequisites

- Python 3.9 or higher
- Streamlit
- Google GenAI SDK (google-genai)
- Pydantic
- Requests

## Installation

1. Clone the repository or download the source files.
2. Navigate to the project root directory.
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the Streamlit application:
   ```bash
   streamlit run app.py
   ```
2. Open the web interface in your browser (typically at http://localhost:8501).
3. Retrieve a Gemini API Key from your Google AI Studio account.
4. Input the Gemini API Key in the sidebar configuration section.
5. Select a preferred Gemini model (e.g., gemini-2.5-flash).
6. Enter a public GitHub repository URL in the input field.
7. Click the "Review Project" button to perform the analysis.
