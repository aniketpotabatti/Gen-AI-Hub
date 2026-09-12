# OpsAgent Alert Analyzer

A Streamlit‑powered dashboard that uses LLMs  to analyze system alerts, output a severity level and a concise summary, and keep a history of past analyses.

***Created** on Jan 2025*

---

## Features

- **Provider selection** – Switch between OpenAI and Gemini models from the sidebar.  
- **Secure API key handling** – Keys are stored only in the current Streamlit session.  
- **Example alerts** – One‑click buttons to load sample JSON payloads (High CPU, Disk Full, Login Failures).  
- **LLM analysis** – Sends the alert JSON to the selected model and extracts `severity` (info/warning/error/critical) and a one‑sentence `summary`.  
- **Severity‑colored output** – Results are displayed with a color‑coded badge.  
- **Analysis history** – Keeps the last 10 analyses with timestamps; history can be cleared.  
- **Safe input clearing** – Uses a rerun pattern to avoid Streamlit’s “widget cannot be modified after instantiation” error.  

---

## Installation

```bash
# Clone the repository
git clone https://github.com/<your‑username>/OpsAgent.git
cd OpsAgent

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

> **requirements.txt**  
> ```
> streamlit>=1.30
> openai>=1.0
> google-generativeai>=0.3.0
> ```

---

## Usage

1. **Start the app**

   ```bash
   streamlit run app.py
   ```

   The dashboard will open at <http://localhost:8501> (or the URL shown in the terminal).

2. **Configure the LLM**

   - In the sidebar, choose **OpenAI** or **Gemini**.  
   - Enter the corresponding API key (the key is kept only for the current session).

3. **Load or paste an alert**

   - Click one of the example buttons (High CPU, Disk Full, Login Failures) to fill the JSON editor, **or** paste your own alert JSON directly into the text area.

4. **Analyze**

   - Press the **🔍 Analyze Alert** button.  
   - While the request is in flight, a spinner appears.  
   - The result shows a severity badge and a summary underneath.

5. **History**

   - Each successful analysis is added to the history panel (most recent first).  
   - Use **🗑️ Clear History** to remove all entries.  
   - Use **🗑️ Clear Input** to reset the JSON editor and result.

---

## Project Structure

```
OpsAgent/
│
├─ app.py               # Main Streamlit application
├─ requirements.txt     # Python dependencies
└─ README.md            # This file
```

---

## How It Works (Brief)

1. The user supplies an alert JSON string.  
2. On clicking **Analyze Alert**, the app builds a prompt instructing the LLM to return a JSON object with `severity` and `summary`.  
3. The selected LLM (OpenAI GPT‑3.5‑turbo or Gemini 2.5‑flash) is called via its official SDK.  
4. The response is parsed; if the model returns plain text, a simple regex extracts the two fields.  
5. The result is stored in `st.session_state`, displayed with a severity‑based colour, and appended to the analysis history.  

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `st.session_state.alert_json cannot be modified after the widget with key alert_json is instantiated` | Direct assignment to `alert_json` after the `st.text_area` widget was rendered. | The clear‑input logic now uses a temporary flag (`_clear_alert`) and `st.rerun()` to mutate state **before** the widget is drawn. |
| API key errors (`ValueError: API key missing`) | No key entered in the sidebar. | Enter a valid OpenAI or Gemini key before analyzing. |
| LLM returns unexpected format | Model didn’t follow the JSON‑only instruction. | The app falls back to regex extraction; if that fails, it defaults to `severity: "info"` and uses the raw text as summary. |
| `streamlit` command not found | Streamlit not installed or not in PATH. | Ensure you installed dependencies via `pip install -r requirements.txt` and that your virtual environment is activated. |

---

## Contributing

1. Fork the repository.  
2. Create a feature branch (`git checkout -b feature/awesome‑thing`).  
3. Commit your changes (`git commit -m "Add awesome thing"`).  
4. Push to the branch (`git push origin feature/awesome‑thing`).  
5. Open a Pull Request.

Please follow the existing code style and add tests for any new functionality.

---

## License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- [Streamlit](https://streamlit.io) for the rapid UI framework.  
- OpenAI and Google for their LLM APIs.  
- The open‑source community for the example alert payloads.

--- 

*Happy alert‑hacking!* 🚨🤖