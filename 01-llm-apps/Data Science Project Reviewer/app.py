"""
Data Science Project Reviewer is a Streamlit web application designed to automatically review machine learning and data science repositories.

Author: @aniketpotabatti
Created: May 2024
"""
import streamlit as st
import requests
import zipfile
import io
import os
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Tuple, Dict

# Page Configuration
st.set_page_config(
    page_title="Data Science Project Reviewer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Premium Dark Mode Look
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    /* Apply modern typography globally */
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Outfit', sans-serif;
    }

    /* Style titles with dynamic tech gradient */
    .title-gradient {
        background: linear-gradient(135deg, #22d3ee 0%, #0d9488 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.8rem;
        margin-bottom: 0.5rem;
        letter-spacing: -0.025em;
    }

    /* Premium card design with glassmorphism */
    .metric-card {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        border: 1px solid rgba(6, 182, 212, 0.15);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        margin-bottom: 20px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .metric-card:hover {
        transform: translateY(-5px);
        border-color: rgba(34, 211, 238, 0.6);
        box-shadow: 0 12px 24px rgba(6, 182, 212, 0.1), 0 0 15px rgba(6, 182, 212, 0.25);
    }
    .metric-title {
        font-size: 15px;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 14px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .metric-score-container {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        font-size: 24px;
        font-weight: 700;
        color: white;
    }
    .score-high {
        background: linear-gradient(135deg, #0d9488 0%, #14b8a6 100%);
        box-shadow: 0 0 15px rgba(20, 184, 166, 0.4);
    }
    .score-mid {
        background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%);
        box-shadow: 0 0 15px rgba(245, 158, 11, 0.35);
    }
    .score-low {
        background: linear-gradient(135deg, #e11d48 0%, #f43f5e 100%);
        box-shadow: 0 0 15px rgba(244, 63, 94, 0.35);
    }
    .overview-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(4, 47, 46, 0.8) 100%);
        backdrop-filter: blur(8px);
        border-radius: 16px;
        padding: 28px;
        border: 1px solid rgba(20, 184, 166, 0.25);
        margin-bottom: 30px;
        color: #f1f5f9;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
    }

    /* Style Streamlit primary button */
    div.stButton > button {
        background: linear-gradient(135deg, #06b6d4 0%, #0d9488 100%) !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 12px 28px !important;
        font-weight: 600 !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(6, 182, 212, 0.3) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        width: auto !important;
    }
    div.stButton > button:hover {
        background: linear-gradient(135deg, #22d3ee 0%, #14b8a6 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(6, 182, 212, 0.5) !important;
    }
    div.stButton > button:active {
        transform: translateY(0px) !important;
    }

    /* Style Streamlit Tabs for tech brand consistency */
    button[data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #22d3ee !important;
        border-bottom-color: #22d3ee !important;
        font-weight: 600 !important;
    }
    button[data-baseweb="tab"]:hover {
        color: #22d3ee !important;
    }
    
    /* Styling Streamlit sidebar */
    [data-testid="stSidebar"] {
        background-color: #0b1329 !important;
        border-right: 1px solid #1e293b !important;
    }
    
    /* Streamlit controls input styles */
    .stTextInput input, .stSelectbox [data-baseweb="select"] {
        background-color: #0f172a !important;
        color: #e2e8f0 !important;
        border: 1px solid #1e293b !important;
        border-radius: 8px !important;
    }
    .stTextInput input:focus {
        border-color: #06b6d4 !important;
        box-shadow: 0 0 0 2px rgba(6, 182, 212, 0.2) !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State Variables
if 'review_data' not in st.session_state:
    st.session_state['review_data'] = None
if 'source_files' not in st.session_state:
    st.session_state['source_files'] = {}
if 'excluded_files' not in st.session_state:
    st.session_state['excluded_files'] = []
if 'is_truncated' not in st.session_state:
    st.session_state['is_truncated'] = False
if 'total_chars' not in st.session_state:
    st.session_state['total_chars'] = 0

# Define Pydantic Models for Structured LLM Output
class CategoryReview(BaseModel):
    score: int = Field(..., description="An integer score from 1 to 10 evaluating this category.")
    critique: str = Field(..., description="Detailed, technical critique of this category in the codebase.")
    strengths: List[str] = Field(..., description="List of notable strengths or best practices observed in this category.")
    improvements: List[str] = Field(..., description="List of step-by-step, specific, actionable improvements for this category.")

class ProjectReview(BaseModel):
    project_overview: str = Field(..., description="High-level executive summary of the repository and its machine learning/data science goal.")
    project_organization: CategoryReview = Field(..., description="Review of project directory organization, setup scripts, environment files.")
    readme_quality: CategoryReview = Field(..., description="Review of README file quality, explanation of the project, setup guide, clarity.")
    feature_engineering: CategoryReview = Field(..., description="Review of data prep, cleaning, scalers, encoders, and leakage prevention.")
    model_choice: CategoryReview = Field(..., description="Review of model selection, hyperparameter tuning, training pipelines.")
    evaluation_metrics: CategoryReview = Field(..., description="Review of validation strategy, cross-validation, proper metrics choice, evaluation logic.")
    deployment_readiness: CategoryReview = Field(..., description="Review of model serialization, inference code, API wrapper, Dockerization.")
    documentation_quality: CategoryReview = Field(..., description="Review of docstrings, type hinting, inline comments, API documentation.")
    code_structure: CategoryReview = Field(..., description="Review of modularity, coding standards (PEP8), code reuse, design patterns.")

# File Processing Configuration Constants
EXCLUDED_DIRS = {
    '.git', '.github', 'node_modules', 'venv', 'env', '.venv', 'venv_name',
    '__pycache__', '.ipynb_checkpoints', 'dist', 'build', '.pytest_cache',
    'egg-info', '.agents', '.gemini', '.idea', '.vscode'
}

EXCLUDED_FILES = {
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock',
    'poetry.toml', 'Pipfile.lock', 'Cargo.lock', 'LICENSE', 'LICENCE',
    '.gitignore', '.DS_Store'
}

EXCLUDED_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.pdf', '.zip',
    '.tar', '.gz', '.tar.gz', '.pkl', '.h5', '.joblib', '.pt', '.onnx',
    '.sqlite', '.db', '.mp3', '.mp4', '.avi', '.mov', '.csv', '.xlsx',
    '.parquet', '.feather', '.woff', '.woff2', '.ttf', '.eot'
}

def parse_ipynb(content_str: str) -> str:
    """Parses a Jupyter Notebook JSON string, extracting only source code and markdown cells to save tokens."""
    try:
        notebook = json.loads(content_str)
        cells_text = []
        for i, cell in enumerate(notebook.get('cells', [])):
            cell_type = cell.get('cell_type', 'code')
            source = cell.get('source', [])
            source_code = "".join(source) if isinstance(source, list) else str(source)
            if source_code.strip():
                cells_text.append(f"## CELL {i} ({cell_type})\n{source_code}")
        return "\n\n".join(cells_text)
    except Exception as e:
        return f"[Error parsing Jupyter Notebook JSON: {e}]"

def download_and_extract_repo(repo_url: str, branch: str = None) -> zipfile.ZipFile:
    """Downloads a public GitHub repository as a ZIP file into memory."""
    url_clean = repo_url.strip().rstrip('/')
    if url_clean.endswith('.git'):
        url_clean = url_clean[:-4]

    parts = url_clean.split('/')
    
    # Handle branches embedded in URL if tree/ exists
    if '/tree/' in url_clean:
        main_part, branch_part = url_clean.split('/tree/', 1)
        branch = branch_part.split('/')[0]
        parts = main_part.split('/')
    
    if len(parts) < 5:
        raise ValueError("Invalid GitHub URL format. Please enter a URL like: https://github.com/owner/repo")
        
    owner = parts[-2]
    repo = parts[-1]
    
    zip_urls = []
    if branch:
        zip_urls.append(f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip")
    else:
        # Try common defaults then API fallback redirect
        zip_urls.append(f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip")
        zip_urls.append(f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip")
        zip_urls.append(f"https://api.github.com/repos/{owner}/{repo}/zipball")
        
    response = None
    last_err = None
    
    for url in zip_urls:
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                response = r
                break
        except Exception as e:
            last_err = e
            
    if not response:
        err_msg = f"HTTP Status {r.status_code}" if 'r' in locals() else str(last_err)
        raise RuntimeError(f"Could not download repository ZIP. Please verify the URL is public and correct. (Error details: {err_msg})")
        
    return zipfile.ZipFile(io.BytesIO(response.content))

def process_zip_contents(zip_file: zipfile.ZipFile, max_file_size: int = 153600) -> Tuple[Dict[str, str], List[Tuple[str, str]]]:
    """Crawls ZIP archive, filtering files and reading text contents."""
    source_files = {}
    excluded_files = []
    
    for file_path in zip_file.namelist():
        if file_path.endswith('/'):
            continue
            
        segments = file_path.replace('\\', '/').split('/')
        if any(seg in EXCLUDED_DIRS for seg in segments):
            excluded_files.append((file_path, "Excluded directory segment"))
            continue
            
        filename = segments[-1]
        if filename in EXCLUDED_FILES:
            excluded_files.append((file_path, "Excluded config/metadata file"))
            continue
            
        _, ext = os.path.splitext(filename)
        ext = ext.lower()
        if ext in EXCLUDED_EXTENSIONS:
            excluded_files.append((file_path, "Excluded binary or data file extension"))
            continue
            
        info = zip_file.getinfo(file_path)
        if info.file_size > max_file_size:
            excluded_files.append((file_path, f"File size exceeds limit ({info.file_size / 1024:.1f} KB)"))
            continue
            
        try:
            with zip_file.open(file_path) as f:
                content_bytes = f.read()
                
            try:
                content_str = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                content_str = content_bytes.decode('latin-1')
                
            if ext == '.ipynb':
                content_str = parse_ipynb(content_str)
                
            # Remove top-level zip wrapper folder directory segment
            cleaned_path = "/".join(segments[1:]) if len(segments) > 1 else file_path
            if not cleaned_path:
                cleaned_path = file_path
                
            source_files[cleaned_path] = content_str
        except Exception as e:
            excluded_files.append((file_path, f"Read error: {str(e)}"))
            
    return source_files, excluded_files

def compile_payload(source_files: Dict[str, str], max_aggregate_chars: int = 1500000) -> Tuple[str, bool]:
    """Compiles source files into a single text payload, truncating if it exceeds character limits."""
    payload = []
    current_chars = 0
    truncated = False
    
    # Sort files to prioritize documentation and code, keeping large config files at the end
    def file_priority(path):
        ext = os.path.splitext(path)[1].lower()
        if path.lower().startswith('readme'):
            return 0
        if ext == '.py':
            return 1
        if ext == '.ipynb':
            return 2
        if ext in ('.md', '.txt'):
            return 3
        return 4
        
    sorted_paths = sorted(source_files.keys(), key=file_priority)
    
    for path in sorted_paths:
        content = source_files[path]
        file_block = f"### FILE: {path}\n```\n{content}\n```\n" + "="*80 + "\n"
        if current_chars + len(file_block) > max_aggregate_chars:
            truncated = True
            continue
        payload.append(file_block)
        current_chars += len(file_block)
        
    return "\n".join(payload), truncated

def run_code_review(repo_url: str, branch: str, api_key: str, model_name: str) -> None:
    """Handles the processing, payload assembly, and API communication, saving results to session state."""
    zip_file = download_and_extract_repo(repo_url, branch if branch.strip() else None)
    source_files, excluded_files = process_zip_contents(zip_file)
    
    if not source_files:
        raise ValueError("No valid text files or source code found in the repository!")
        
    payload, is_truncated = compile_payload(source_files)
    total_chars = sum(len(c) for c in source_files.values())
    
    client = genai.Client(api_key=api_key)
    
    prompt = f"""
You are provided with the codebase of a machine learning / data science project.
Analyze the repository and perform a comprehensive review.

Evaluate the project across these 8 specific categories:
1. Project Organization (e.g., directory structures, setup scripts, environment definitions, reproducibility)
2. README Quality (e.g., description, setup instructions, usage, clarity, results)
3. Feature Engineering (e.g., data preprocessing pipelines, encoders, scalers, imputers, handling leakage)
4. Model Choice (e.g., appropriate models, hyperparameter tuning, model training structure)
5. Evaluation Metrics (e.g., validation split strategy, cross-validation, proper metrics choice, confusion matrix/plots)
6. Deployment Readiness (e.g., inference script, serialization, containerization like Docker, API wrappers like FastAPI/Flask)
7. Documentation Quality (e.g., docstrings, inline comments, type hints, architectural drawings)
8. Code Structure (e.g., modularity, PEP8 compliance, reuse, separation of concerns)

For each category, you must assign a score between 1 and 10, write a deep critique detailing what is good and bad, list specific strengths, and provide a clear, step-by-step, actionable improvement plan.

Return your response in the requested JSON structure.
Here is the codebase payload:

{payload}
"""
    
    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ProjectReview,
            system_instruction=(
                "You are an expert Senior Data Scientist and Machine Learning Architect. "
                "You evaluate codebases objectively and thoroughly, checking for industry best practices in ML, data validation, and software architecture. "
                "Respond only with a JSON payload fitting the requested schema."
            )
        )
    )
    
    review_data = ProjectReview.model_validate_json(response.text)
    
    # Store results in Streamlit session state
    st.session_state['review_data'] = review_data
    st.session_state['source_files'] = source_files
    st.session_state['excluded_files'] = excluded_files
    st.session_state['is_truncated'] = is_truncated
    st.session_state['total_chars'] = total_chars

# ==================== STREAMLIT UI ====================

st.markdown('<h1 class="title-gradient">🔍 Data Science Project Reviewer</h1>', unsafe_allow_html=True)
st.markdown('<p style="font-size: 1.15rem; color: #94a3b8; margin-bottom: 2rem;">Analyze and evaluate your machine learning / data science repository in a single-shot using Gemini.</p>', unsafe_allow_html=True)

# Sidebar Configuration Layout
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Gemini API Key", type="password", help="Your Gemini API key. Stored only in memory for this session.")
model_name = st.sidebar.selectbox(
    "Gemini Model",
    ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash", "gemini-1.5-pro"],
    index=0,
    help="Gemini 2.5 Flash is recommended for fast, high-quality, large-context window reasoning."
)
manual_branch = st.sidebar.text_input("Branch/Ref (Optional)", placeholder="main", help="Target branch name. Defaults to main or master if empty.")

st.sidebar.markdown("---")
st.sidebar.markdown("""
### How it works:
1. Downloads the repository ZIP ball.
2. Extracts code scripts, notebooks, and configurations.
3. Packages code segments with clear file paths.
4. Leverages Gemini's high-context reasoning capabilities to inspect project quality.
5. Returns a detailed review and visual scorecard.
""")

# URL Input Field
repo_url = st.text_input("Enter Public GitHub Repository URL", placeholder="https://github.com/username/repo-name")

# Review Execution Action Trigger
if st.button("Review Project", type="primary"):
    if not api_key:
        st.error("Please enter your Gemini API Key in the sidebar.")
    elif not repo_url:
        st.error("Please enter a GitHub repository URL.")
    else:
        # Reset state while running new analysis to display the loading progress indicator cleanly
        st.session_state['review_data'] = None
        
        status_placeholder = st.empty()
        with status_placeholder.container():
            try:
                run_code_review(repo_url, manual_branch, api_key, model_name)
                st.success("Review generated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ An error occurred during analysis: {e}")
                st.info("Please verify your API key is correct and you have an active internet connection.")

# Render Results from Session State
if st.session_state['review_data'] is not None:
    review_data = st.session_state['review_data']
    source_files = st.session_state['source_files']
    excluded_files = st.session_state['excluded_files']
    is_truncated = st.session_state['is_truncated']
    total_chars = st.session_state['total_chars']

    if is_truncated:
        st.warning("⚠️ The repository is large. The codebase payload was truncated to stay within optimal analysis limits, focusing on docs and source files.")

    # Display Overview Card
    st.markdown(f"""
    <div class="overview-card">
        <h3>📋 Project Overview</h3>
        <p style="font-size:16px; line-height:1.6; color:#e2e8f0;">{review_data.project_overview}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Scorecard Grid Section
    st.markdown("## 📊 Category Scorecard")
    
    categories_map = [
        ("Project Organization", review_data.project_organization),
        ("README Quality", review_data.readme_quality),
        ("Feature Engineering", review_data.feature_engineering),
        ("Model Choice", review_data.model_choice),
        ("Evaluation Metrics", review_data.evaluation_metrics),
        ("Deployment Readiness", review_data.deployment_readiness),
        ("Documentation Quality", review_data.documentation_quality),
        ("Code Structure", review_data.code_structure)
    ]
    
    col1, col2, col3, col4 = st.columns(4)
    cols = [col1, col2, col3, col4]
    for idx, (cat_name, cat_data) in enumerate(categories_map[:4]):
        score = cat_data.score
        score_class = "score-high" if score >= 8 else ("score-mid" if score >= 5 else "score-low")
        cols[idx].markdown(f"""
        <div class="metric-card">
            <div class="metric-title">{cat_name}</div>
            <div class="metric-score-container {score_class}">{score}</div>
        </div>
        """, unsafe_allow_html=True)
        
    col5, col6, col7, col8 = st.columns(4)
    cols_bottom = [col5, col6, col7, col8]
    for idx, (cat_name, cat_data) in enumerate(categories_map[4:]):
        score = cat_data.score
        score_class = "score-high" if score >= 8 else ("score-mid" if score >= 5 else "score-low")
        cols_bottom[idx].markdown(f"""
        <div class="metric-card">
            <div class="metric-title">{cat_name}</div>
            <div class="metric-score-container {score_class}">{score}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Detailed Breakdown Section
    st.markdown("## 🔎 Detailed Breakdown & Actionable Improvements")
    
    tab_names = [cat[0] for cat in categories_map] + ["📂 Codebase Stats"]
    tabs = st.tabs(tab_names)
    
    for idx, (cat_name, cat_data) in enumerate(categories_map):
        with tabs[idx]:
            st.markdown(f"### Score: {cat_data.score}/10")
            st.markdown("#### 🔬 Technical Critique")
            st.write(cat_data.critique)
            
            st.markdown("#### 🌟 Key Strengths")
            for strength in cat_data.strengths:
                st.markdown(f"- ✅ {strength}")
                
            st.markdown("#### 🛠️ Actionable Improvement Plan")
            for improvement in cat_data.improvements:
                st.markdown(f"- ⚙️ {improvement}")
    
    # Codebase Stats Tab
    with tabs[-1]:
        st.subheader("Repository Scan Statistics")
        st.markdown(f"**Total files detected:** {len(source_files) + len(excluded_files)}")
        st.markdown(f"**Files analyzed:** {len(source_files)}")
        st.markdown(f"**Files excluded:** {len(excluded_files)}")
        st.markdown(f"**Total aggregate size analyzed:** {total_chars:,} characters (~{total_chars // 4:,} tokens)")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("#### Included Files")
            included_list = [{"File Path": path, "Length (chars)": len(content)} for path, content in source_files.items()]
            st.dataframe(included_list, use_container_width=True)
            
        with col_right:
            st.markdown("#### Excluded Files")
            if excluded_files:
                excluded_list = [{"File Path": path, "Reason": reason} for path, reason in excluded_files]
                st.dataframe(excluded_list, use_container_width=True)
            else:
                st.info("No files were excluded.")
