"""
Author: @aniketpotabatti
Project: NutriGuide App - Multimodal AI Nutrition Analyzer
"""

import streamlit as st
import google.generativeai as genai
import os, base64
from dotenv import load_dotenv
from PIL import Image
from pathlib import Path

# Load environment variables
load_dotenv()

# ── Page Config ───────────────────────────────────────────────────────────────
LOGO_PATH = Path(__file__).parent / "assets" / "nutriguide logo.png"
page_icon_val = str(LOGO_PATH) if LOGO_PATH.exists() else "🥗"

st.set_page_config(
    page_title="NutriGuide - AI Food Calorie & Nutrition Analyzer",
    page_icon=page_icon_val,
    layout="wide"
)

AVAILABLE_MODELS = ["gemini-3.5-flash","gemini-3.0-flash", "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"]
DEFAULT_MODEL = "gemini-3.5-flash"

SYSTEM_NUTRITION_PROMPT = """
You are a top clinical nutritionist and dietary analyst.
Analyze the food items shown in the image carefully along with any user prompt.

Provide a comprehensive, structured response formatted strictly in Markdown with clear headings:

### 🥗 Identified Food Items & Calorie Estimation
List every food item identified in the image with estimated portion size and calorie content:
- **Item 1**: ~X kcal (Portion size)
- **Item 2**: ~Y kcal (Portion size)
- **Estimated Total Energy**: ~Z kcal

### 📊 Macronutrient & Nutrient Split
Provide an estimated macronutrient breakdown:
- **Carbohydrates**: ~X%
- **Proteins**: ~Y%
- **Healthy Fats**: ~Z%
- **Dietary Fiber**: ~A g
- **Sugars**: ~B g

### 💚 Health & Nutrition Assessment
- **Rating**: (e.g. 🟢 Highly Nutritious / 🟡 Moderate / 🔴 High Calorie or Processed)
- **Nutritional Quality Analysis**: Detail vitamins, minerals, key health benefits or concerns.

### 💡 Dietary Suggestions & Healthy Swaps
- Actionable advice to balance this meal, portion control tips, or healthier alternative swaps.
"""

# ── Session State Defaults ───────────────────────────────────────────────────
env_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
defaults = {
    "google_api_key": env_api_key,
    "selected_model": DEFAULT_MODEL,
    "analysis_result": None,
    "analyzed_image": None,
    "prompt_input_val": "",
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

if st.session_state.google_api_key:
    try:
        genai.configure(api_key=st.session_state.google_api_key)
    except Exception:
        pass


# ── Helpers ───────────────────────────────────────────────────────────────────
def b64_img(path):
    if not path.exists():
        return ""
    try:
        return f"data:image/png;base64,{base64.b64encode(path.read_bytes()).decode()}"
    except Exception:
        return ""

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
    return None

def get_gemini_response(input_text, image_data, prompt, model_name=DEFAULT_MODEL):
    if not st.session_state.google_api_key:
        st.error("⚠️ Please configure your Google Gemini API key in the sidebar.")
        return None
    try:
        genai.configure(api_key=st.session_state.google_api_key)
        model = genai.GenerativeModel(model_name)
        contents = []
        if input_text:
            contents.append(f"User Query / Meal Context: {input_text}")
        contents.append(prompt)
        contents.append(image_data[0])
        
        response = model.generate_content(contents)
        return response.text
    except Exception as e:
        st.error("Error generating nutrition response: " + str(e))
        return None


# ── Custom CSS Design System ──────────────────────────────────────────────────
logo_src = b64_img(LOGO_PATH)

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [data-testid="stAppViewContainer"] {{
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
    background-color: #060a07 !important;
    color: #e2e8f0 !important;
}}

[data-testid="stSidebar"] {{
    background-color: #0b140d !important;
    border-right: 1px solid rgba(16, 185, 129, 0.15) !important;
}}

#MainMenu, footer {{ visibility: hidden; }}
.block-container {{
    max-width: 1040px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 3rem !important;
}}

/* Streamlit Top Header Bar with Logo */
header[data-testid="stHeader"] {{
    position: relative !important;
    background: rgba(6, 10, 7, 0.8) !important;
    backdrop-filter: blur(12px) !important;
    border-bottom: 1px solid rgba(16, 185, 129, 0.15) !important;
    z-index: 100 !important;
}}
header[data-testid="stHeader"]::before {{
    content: "";
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 200px;
    height: 100px;
    background: url("{logo_src}") center / contain no-repeat;
    pointer-events: none;
    filter: drop-shadow(0 0 12px rgba(16, 185, 129, 0.5));
}}

/* App Banner */
.nutri-banner {{
    background: linear-gradient(135deg, #0d1e12 0%, #152c1b 50%, #0d1810 100%);
    border: 1px solid rgba(52, 211, 153, 0.2);
    border-radius: 20px;
    padding: 24px 28px;
    margin-bottom: 1.8rem;
    box-shadow: 0 12px 35px -10px rgba(0,0,0,0.6);
}}
.nutri-banner-title {{
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #34d399 0%, #a7f3d0 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 4px 0;
    letter-spacing: -0.02em;
}}
.nutri-banner-subtitle {{
    color: #94a3b8;
    font-size: 0.95rem;
    margin-bottom: 14px;
}}
.nutri-banner-badges {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}}
.banner-pill {{
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.25);
    color: #6ee7b7;
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.78rem;
    font-weight: 600;
}}

/* Custom Expander */
div.st-expander {{
    background-color: #0c180e !important;
    border: 1px solid rgba(52, 211, 153, 0.2) !important;
    border-radius: 14px !important;
    margin-bottom: 1.5rem !important;
}}
div.st-expanderHeader p {{
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    color: #34d399 !important;
}}

/* Form Styling */
div[data-testid="stForm"] {{
    background: #0c180e !important;
    border: 1px solid rgba(52, 211, 153, 0.2) !important;
    border-radius: 18px !important;
    padding: 24px !important;
    box-shadow: 0 10px 30px -10px rgba(0,0,0,0.5) !important;
}}
div[data-testid="stForm"] > div {{ border: none !important; }}

div[data-baseweb="input"] {{
    background-color: #060a07 !important;
    border: 1px solid rgba(52, 211, 153, 0.25) !important;
    border-radius: 10px !important;
    color: #f8fafc !important;
}}
div[data-baseweb="input"]:focus-within {{
    border-color: #10b981 !important;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.2) !important;
}}
div[data-baseweb="input"] input {{ color: #f8fafc !important; font-size: 0.92rem !important; }}

/* Form Submit Button Target Fix */
div[data-testid="stFormSubmitButton"] > button,
div.stFormSubmitButton > button,
button[kind="primaryFormSubmit"] {{
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 24px !important;
    width: 100% !important;
    box-shadow: 0 4px 16px rgba(16, 185, 129, 0.4) !important;
    transition: all 0.2s ease !important;
}}
div[data-testid="stFormSubmitButton"] > button:hover,
div.stFormSubmitButton > button:hover,
button[kind="primaryFormSubmit"]:hover {{
    background: linear-gradient(135deg, #34d399 0%, #10b981 100%) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 22px rgba(16, 185, 129, 0.55) !important;
}}

/* File Uploader */
div[data-testid="stFileUploader"] {{
    background-color: #060a07 !important;
    border: 1px dashed rgba(52, 211, 153, 0.3) !important;
    border-radius: 12px !important;
    padding: 8px !important;
    transition: border-color 0.2s;
}}
div[data-testid="stFileUploader"]:hover {{
    border-color: #10b981 !important;
}}

/* Custom Empty State Card */
.empty-state-card {{
    background: #0c180e;
    border: 1px solid rgba(52, 211, 153, 0.18);
    border-radius: 18px;
    padding: 32px 24px;
    text-align: center;
}}
.empty-state-icon {{
    font-size: 3rem;
    margin-bottom: 12px;
}}
.empty-state-title {{
    font-size: 1.15rem;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 8px;
}}
.empty-state-text {{
    font-size: 0.9rem;
    color: #94a3b8;
    line-height: 1.6;
    max-width: 360px;
    margin: 0 auto 20px;
}}
.empty-state-tips {{
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 12px;
    padding: 14px 18px;
    font-size: 0.82rem;
    color: #a7f3d0;
    text-align: left;
}}
.empty-state-tips ul {{
    margin: 6px 0 0 0;
    padding-left: 18px;
}}

/* Result Markdown Container */
.result-card {{
    background: #0c180e;
    border: 1px solid rgba(52, 211, 153, 0.2);
    border-radius: 18px;
    padding: 28px;
    line-height: 1.75;
}}
.result-card h3 {{
    color: #34d399 !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    margin-top: 1.4rem !important;
    margin-bottom: 0.6rem !important;
    border-bottom: 1px solid rgba(52, 211, 153, 0.15);
    padding-bottom: 6px;
}}
.result-card h3:first-child {{ margin-top: 0 !important; }}
.result-card p, .result-card li {{
    color: #cbd5e1 !important;
    font-size: 0.95rem !important;
}}
.result-card strong {{ color: #f8fafc !important; }}

[data-testid="stDownloadButton"] button {{
    background: #0c180e !important;
    border: 1px solid rgba(52, 211, 153, 0.3) !important;
    color: #34d399 !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.2s !important;
}}
[data-testid="stDownloadButton"] button:hover {{
    background: rgba(16, 185, 129, 0.15) !important;
    border-color: #10b981 !important;
}}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ App Settings")
    
    api_key_val = st.text_input(
        "Google Gemini API Key",
        type="password",
        value=st.session_state.google_api_key,
        placeholder="AIzaSy...",
        help="Obtain your free Gemini API key from Google AI Studio (aistudio.google.com)"
    )
    if api_key_val != st.session_state.google_api_key:
        st.session_state.google_api_key = api_key_val
        st.rerun()

    if st.session_state.google_api_key:
        st.caption("🟢 **API Key Configured**")
    else:
        st.caption("🔴 **API Key Required** for Analysis")

    model_choice = st.selectbox(
        "Gemini Multimodal Model",
        options=AVAILABLE_MODELS,
        index=AVAILABLE_MODELS.index(st.session_state.selected_model) if st.session_state.selected_model in AVAILABLE_MODELS else 0
    )
    st.session_state.selected_model = model_choice

    st.markdown("---")
    st.markdown("### 🥗 About NutriGuide")
    st.caption(
        "NutriGuide leverages Gemini multimodal AI to recognize food items, estimate portion-based calories, "
        "analyze macronutrient balance, and deliver tailored clinical dietary suggestions."
    )


# ── Main Banner ───────────────────────────────────────────────────────────────
st.markdown("""
<div class="nutri-banner">
    <h1 class="nutri-banner-title">AI Food Calorie & Nutrition Analyzer</h1>
    <div class="nutri-banner-subtitle">Instant Multimodal Meal Analysis, Calorie Estimation & Dietary Health Guidance</div>
    <div class="nutri-banner-badges">
        <span class="banner-pill">⚡ Powered by Gemini Multimodal AI</span>
        <span class="banner-pill">🥗 Itemized Calorie Estimation</span>
        <span class="banner-pill">📊 Macronutrient Breakdown</span>
        <span class="banner-pill">💡 Clinical Dietary Swaps</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Instructions ──────────────────────────────────────────────────────────────
with st.expander("📖 How to Use & Analysis Guide", expanded=False):
    st.markdown("""
<style>
.guide-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; margin-bottom: 18px; }
.guide-step {
    background: rgba(16, 185, 129, 0.07);
    border: 1px solid rgba(52, 211, 153, 0.2);
    border-radius: 14px;
    padding: 16px 18px;
}
.guide-step-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px; height: 28px;
    background: linear-gradient(135deg, #10b981, #059669);
    color: #fff;
    font-weight: 800;
    font-size: 0.82rem;
    border-radius: 8px;
    margin-bottom: 10px;
}
.guide-step-title { font-size: 0.9rem; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }
.guide-step-desc { font-size: 0.82rem; color: #94a3b8; line-height: 1.5; }

.guide-output-section { margin-top: 6px; }
.guide-output-title { font-size: 0.88rem; font-weight: 700; color: #34d399; margin-bottom: 10px; }
.guide-output-grid { display: flex; flex-wrap: wrap; gap: 10px; }
.guide-output-pill {
    background: #0c180e;
    border: 1px solid rgba(52, 211, 153, 0.2);
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 0.82rem;
    color: #a7f3d0;
    display: flex; align-items: center; gap: 8px;
}
.guide-output-pill strong { color: #f1f5f9; display: block; font-size: 0.8rem; }
.guide-output-pill span { color: #64748b; font-size: 0.76rem; }

.guide-tip-box {
    background: rgba(234, 179, 8, 0.07);
    border: 1px solid rgba(234, 179, 8, 0.2);
    border-radius: 12px;
    padding: 14px 18px;
    margin-top: 14px;
    font-size: 0.82rem;
    color: #fde68a;
    line-height: 1.6;
}
.guide-tip-box strong { color: #fbbf24; }
</style>

<div class="guide-grid">
    <div class="guide-step">
        <div class="guide-step-num">1</div>
        <div class="guide-step-title">🔑 Configure API Key</div>
        <div class="guide-step-desc">Open the sidebar and paste your <b>Google Gemini API Key</b>. Get one free at <a href="https://aistudio.google.com" target="_blank" style="color:#34d399;">aistudio.google.com</a>.</div>
    </div>
    <div class="guide-step">
        <div class="guide-step-num">2</div>
        <div class="guide-step-title">📸 Upload a Meal Photo</div>
        <div class="guide-step-desc">Upload a clear photo of your meal (JPG, PNG, WEBP, JPEG). For best accuracy, use a <b>top-down angle</b> with good lighting so all items are visible.</div>
    </div>
    <div class="guide-step">
        <div class="guide-step-num">3</div>
        <div class="guide-step-title">💬 Add Context (Optional)</div>
        <div class="guide-step-desc">Use the <b>Quick Prompt Presets</b> or type a custom query — e.g., portion sizes, dietary restrictions, or specific macro questions.</div>
    </div>
    <div class="guide-step">
        <div class="guide-step-num">4</div>
        <div class="guide-step-title">⚡ Run Analysis</div>
        <div class="guide-step-desc">Click <b>"🥗 Analyze & Calculate Calories"</b>. Gemini Multimodal AI will detect each food item and generate a full nutritional report.</div>
    </div>
</div>

<div class="guide-output-section">
    <div class="guide-output-title">📊 What You'll Get in the Report</div>
    <div class="guide-output-grid">
        <div class="guide-output-pill">🥗 <div><strong>Itemized Calorie Count</strong><span>Per food item + total estimate</span></div></div>
        <div class="guide-output-pill">📊 <div><strong>Macronutrient Split</strong><span>Carbs, Protein, Fats, Fiber, Sugar %</span></div></div>
        <div class="guide-output-pill">💚 <div><strong>Health Rating</strong><span>🟢 Nutritious / 🟡 Moderate / 🔴 High-Cal</span></div></div>
        <div class="guide-output-pill">💡 <div><strong>Dietary Swaps</strong><span>Healthier alternatives & tips</span></div></div>
        <div class="guide-output-pill">📥 <div><strong>Export Report</strong><span>Download as Markdown or Text</span></div></div>
    </div>
</div>

<div class="guide-tip-box">
    <strong>📸 Photo Tips for Best Accuracy:</strong><br>
    • Use natural lighting and avoid shadows covering items.<br>
    • Spread food items apart so each one is clearly distinguishable.<br>
    • Include everyday items (spoons, plate) for scale references.<br>
    • Avoid blurry, dark, or heavily filtered images.
</div>
""", unsafe_allow_html=True)




# ── Main Layout ───────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 1], gap="medium")

with col1:
    st.markdown("### 📸 Upload & Meal Prompt")
    
    # Preset Sample Prompt Chips
    st.caption("💡 Quick Prompt Presets:")
    chip_col1, chip_col2 = st.columns(2)
    with chip_col1:
        if st.button("🥗 Healthy Salad Bowl", key="chip1", use_container_width=True):
            st.session_state.prompt_input_val = "Identify items in this salad bowl and estimate total calories."
            st.rerun()
        if st.button("🥑 Keto Breakfast", key="chip3", use_container_width=True):
            st.session_state.prompt_input_val = "Calculate keto macros (healthy fats vs carbs) for this breakfast."
            st.rerun()
    with chip_col2:
        if st.button("🍗 High-Protein Meal", key="chip2", use_container_width=True):
            st.session_state.prompt_input_val = "Focus on protein content and total energy for workout recovery."
            st.rerun()
        if st.button("🍔 Fast Food Check", key="chip4", use_container_width=True):
            st.session_state.prompt_input_val = "Estimate calories, sodium, and unhealthy fats in this fast food meal."
            st.rerun()

    with st.form("input_form"):
        input_text = st.text_input(
            "Meal Prompt / Context (Optional)",
            value=st.session_state.prompt_input_val,
            placeholder="e.g. Grilled chicken bowl with brown rice and avocado..."
        )
        uploaded_file = st.file_uploader(
            "Upload Food Image",
            type=["jpg", "jpeg", "png", "webp"]
        )
        submit = st.form_submit_button("🥗 Analyze & Calculate Calories")

    # Image Preview
    current_img = None
    if uploaded_file is not None:
        try:
            current_img = Image.open(uploaded_file)
            st.session_state.analyzed_image = current_img
            st.image(current_img, caption="Uploaded Meal Photo", use_container_width=True)
        except Exception as e:
            st.error("Error loading image: " + str(e))
    elif st.session_state.analyzed_image is not None:
        st.image(st.session_state.analyzed_image, caption="Analyzed Meal Photo", use_container_width=True)

    if submit:
        if uploaded_file is None and st.session_state.analyzed_image is None:
            st.warning("Please upload a food image first before submitting.")
        elif not st.session_state.google_api_key:
            st.error("⚠️ Please configure your Google Gemini API Key in the sidebar.")
        else:
            with st.spinner("Analyzing image with Gemini Multimodal AI..."):
                image_parts = input_image_setup(uploaded_file)
                if image_parts:
                    res_text = get_gemini_response(
                        input_text=input_text,
                        image_data=image_parts,
                        prompt=SYSTEM_NUTRITION_PROMPT,
                        model_name=st.session_state.selected_model
                    )
                    if res_text:
                        st.session_state.analysis_result = res_text
                        st.rerun()

with col2:
    st.markdown("### 📊 Nutritional Analysis & Report")
    
    if st.session_state.analysis_result:
        tab_breakdown, tab_export = st.tabs([
            "🥗 Comprehensive Report",
            "📥 Export Data"
        ])
        
        with tab_breakdown:
            st.markdown(f'<div class="result-card">{st.session_state.analysis_result}</div>', unsafe_allow_html=True)

        with tab_export:
            st.markdown("#### 📥 Download Nutritional Analysis")
            st.caption("Export your meal assessment for dietary logs or consultations.")
            
            report_text = f"# NutriGuide Food Analysis Report\n\n{st.session_state.analysis_result}\n\n---\n*Generated by NutriGuide AI*"
            
            st.download_button(
                "📄 Download Markdown Report (.md)",
                data=report_text,
                file_name="nutriguide_report.md",
                mime="text/markdown",
                use_container_width=True
            )
            st.download_button(
                "📝 Download Text Report (.txt)",
                data=report_text,
                file_name="nutriguide_report.txt",
                mime="text/plain",
                use_container_width=True
            )
    else:
        st.markdown("""
        <div class="empty-state-card">
            <div class="empty-state-icon">🥗</div>
            <div class="empty-state-title">Ready for Food Analysis</div>
            <div class="empty-state-text">
                Upload a meal photo on the left and click <b>Analyze & Calculate Calories</b> to generate a full itemized nutritional breakdown, calorie estimate, and diet advice.
            </div>
            <div class="empty-state-tips">
                <strong>💡 Tips for best results:</strong>
                <ul>
                    <li>Ensure good lighting and a clear top-down view of all food items.</li>
                    <li>Use preset prompt chips to target specific nutrition goals (Keto, Protein, Salad).</li>
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
