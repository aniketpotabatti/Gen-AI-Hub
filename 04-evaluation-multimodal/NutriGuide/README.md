<p align="center">
  <img src="assets/nutriguide logo.png" alt="NutriGuide Logo" width="320" />
</p>

<p align="center">
  <b>AI-Powered Multimodal Food Calorie Estimation & Nutritional Health Assessment</b><br>
  <sub>Powered by Google Gemini Multimodal AI · Built with Streamlit</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white" />
  <img src="https://img.shields.io/badge/Gemini%20AI-4285F4?logo=google&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-22c55e" />
</p>

---

## ✨ Features

- 📸 **Upload food images** for instant multimodal AI analysis
- 🔢 **Itemized calorie estimation** per food item with portion size detection
- 📊 **Macronutrient breakdown** — Carbs, Proteins, Fats, Fiber, Sugars
- 💚 **Health Rating** — 🟢 Nutritious / 🟡 Moderate / 🔴 High Calorie
- 💡 **Clinical dietary swaps** & personalized meal balancing advice
- ⚡ **Quick Prompt Presets** — Keto, High-Protein, Salad, Fast Food
- 📥 **Export reports** as Markdown or Text
- 🎨 **Modern glassmorphism dark theme** UI with emerald accents

## 🧰 Technologies Used

| Technology | Purpose |
|---|---|
| Python 3.9+ | Core language |
| Streamlit | Web application framework |
| Google Gemini AI | Multimodal image + text analysis |
| PIL (Pillow) | Image processing |
| python-dotenv | Environment variable management |

## ⚙️ Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/aniketpotabatti/Gen-AI-Hub.git
   cd Gen-AI-Hub/04-evaluation-multimodal/NutriGuide
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure your Google API key** — create a `.env` file:
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```
   > Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com)

4. **Run the application:**
   ```bash
   streamlit run NutriGuide_app.py
   ```

## 🚀 Usage

1. Open the app in your browser at `http://localhost:8501`
2. Paste your **Google Gemini API Key** in the sidebar
3. Select a **Quick Prompt Preset** or type a custom meal query
4. **Upload a food image** (JPG, PNG, WEBP)
5. Click **"🥗 Analyze & Calculate Calories"**
6. Review your detailed nutritional report and export if needed

## 📦 Requirements

See [`requirements.txt`](requirements.txt) for a complete list of dependencies.

## 🤝 Contributing

Feel free to fork the repository and submit pull requests for any improvements.

## 📄 License

This project is open source and available under the **MIT License**.

## 👤 Author

Created by [@aniketpotabatti](https://github.com/aniketpotabatti)
