import streamlit as st
import json
import time

def get_severity_color(severity):
    if not severity:
        return "#757575"
    severity = severity.lower()
    return {
        "critical": "#d32f2f",
        "error":    "#f57c00",
        "warning":  "#fbc02d",
        "info":     "#1976d2",
    }.get(severity, "#757575")

st.set_page_config(page_title="OpsAgent Dashboard", layout="centered")
st.title("🚨 OpsAgent Alert Analyzer")

with st.sidebar:
    st.header("🔑 API Settings")
    provider = st.radio("Select LLM Provider", ["OpenAI", "Gemini"], index=0)
    if provider == "OpenAI":
        api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    else:
        api_key = st.text_input("Gemini API Key", type="password", placeholder="AI...")
    st.caption("Keys are session-only.")

if "alert_json" not in st.session_state:
    st.session_state.alert_json = ""
if "result" not in st.session_state:
    st.session_state.result = None
if "history" not in st.session_state:
    st.session_state.history = []
if "loading" not in st.session_state:
    st.session_state.loading = False

EXAMPLES = {
    "High CPU": {"metric":"cpu_utilization","value":98,"unit":"percent","host":"web-01.example.com","timestamp":"2026-09-12T10:15:00Z"},
    "Disk Full": {"metric":"disk_usage","value":95,"unit":"percent","mount":"/var/log","host":"db-02.example.com","timestamp":"2026-09-12T09:45:00Z"},
    "Login Failures": {"metric":"failed_logins","value":20,"unit":"count","host":"auth-03.example.com","window_minutes":5,"timestamp":"2026-09-12T10:00:00Z"},
}
def load_example(k):
    st.session_state.alert_json = json.dumps(EXAMPLES[k], indent=2)

st.subheader("Alert JSON")
c1,c2,c3 = st.columns(3)
with c1:
    if st.button("High CPU", use_container_width=True):
        load_example("High CPU")
with c2:
    if st.button("Disk Full", use_container_width=True):
        load_example("Disk Full")
with c3:
    if st.button("Login Failures", use_container_width=True):
        load_example("Login Failures")
# Handle clear input via rerun to avoid widget modification conflict
if st.session_state.get("_clear_alert", False):
    st.session_state.alert_json = ""
    st.session_state.result = None
    st.session_state._clear_alert = False
st.text_area("", value=st.session_state.alert_json, height=200, key="alert_json")
if st.button("🗑️ Clear Input", use_container_width=True):
    st.session_state._clear_alert = True
    st.rerun()
def call_llm(prompt):
    if not api_key:
        raise ValueError("API key missing")
    if provider == "OpenAI":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role":"user","content":prompt}],
            temperature=0,
            max_tokens=150,
        )
        return resp.choices[0].message.content.strip()
    else:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        return model.generate_content(prompt).text.strip()

if st.button("🔍 Analyze Alert", disabled=st.session_state.loading, use_container_width=True):
    txt = st.session_state.alert_json.strip()
    if not txt:
        st.warning("Enter alert JSON")
    else:
        st.session_state.loading = True
        with st.spinner("Calling LLM…"):
            prompt = f"""
You are an OpsAgent that analyzes system alerts.
Given the following alert JSON, output a JSON object with exactly two fields:
- severity: one of "info", "warning", "error", "critical"
- summary: a brief one-sentence summary of the alert

Do not include any extra text. Output valid JSON only.

Alert JSON:
```json
{txt}
```

Output JSON:
""".strip()
            try:
                raw = call_llm(prompt)
                try:
                    res = json.loads(raw)
                    if not ("severity" in res and "summary" in res):
                        raise ValueError
                except Exception:
                    import re
                    m1 = re.search(r'"severity"\s*:\s*"([^"]+)"', raw, re.I)
                    m2 = re.search(r'"summary"\s*:\s*"([^"]+)"', raw, re.I)
                    if m1 and m2:
                        res = {"severity": m1.group(1).lower(), "summary": m2.group(1)}
                    else:
                        res = {"severity":"info","summary":raw[:200]}
                st.session_state.result = res
                st.session_state.history = (
                    [{"alert":txt,"result":res,"timestamp":time.strftime("%H:%M:%S")}]
                    + st.session_state.history
                )[:10]
            except Exception as e:
                st.error(f"LLM error: {e}")
                st.session_state.result = {"error":str(e)}
            finally:
                st.session_state.loading = False

if st.session_state.result:
    r = st.session_state.result
    if "error" in r:
        st.error(f"❌ {r['error']}")
    else:
        sev = r.get("severity","")
        summ = r.get("summary","")
        col = get_severity_color(sev)
        st.markdown(f'''
<div style="display:flex;align-items:center;margin-bottom:0.5rem;">
<span style="background:{col};color:#fff;padding:0.25rem 0.5rem;border-radius:4px;font-weight:600;margin-right:0.5rem;">{sev.upper()}</span>
<span>{summ}</span>
</div>
''', unsafe_allow_html=True)

st.subheader("History")
if st.session_state.history:
    cols = st.columns([4,1])
    with cols[1]:
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.history = []
    for item in st.session_state.history:
        with st.container(border=True):
            st.caption(f"**Time:** {item['timestamp']}")
            st.json(item["alert"], expanded=False)
            res = item["result"]
            if "error" in res:
                st.error(res["error"])
            else:
                sev = res.get("severity","")
                summ = res.get("summary","")
                col = get_severity_color(sev)
                st.markdown(f'''
<div style="display:flex;align-items:center;">
<span style="background:{col};color:#fff;padding:0.15rem 0.3rem;border-radius:3px;font-size:0.85rem;margin-right:0.5rem;">{sev.upper()}</span>
<span style="font-size:0.9rem;">{summ}</span>
</div>
''', unsafe_allow_html=True)
else:
    st.info("No history yet.")

st.caption("OpsAgent Dashboard • Powered by Streamlit • Select provider and enter API key in sidebar.")
