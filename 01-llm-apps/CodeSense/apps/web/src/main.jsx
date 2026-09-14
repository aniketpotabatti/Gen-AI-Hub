import React, { useCallback, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import Editor from "@monaco-editor/react";
import { extractContext } from "@codesense/core";
import "./styles.css";

const starter = `function findFirstMatch(items, predicate) {
  for (const item of items) {
    if (predicate(item)) return item;
  }
  return undefined;
}
`;
const API = import.meta.env.VITE_CODESENSE_API_URL || "http://localhost:8787";

function Icon({ children }) { return <span className="icon" aria-hidden="true">{children}</span>; }
function languageFor(name) { const extension = name.split(".").pop()?.toLowerCase(); return ({ js: "javascript", jsx: "javascript", ts: "typescript", tsx: "typescript", py: "python", go: "go" })[extension] || "plaintext"; }

function App() {
  const [code, setCode] = useState(starter);
  const [language, setLanguage] = useState("javascript");
  const [output, setOutput] = useState("Select an action to get a focused code insight.");
  const [apiKey, setApiKey] = useState("");
  const [provider, setProvider] = useState("openai-compatible");
  const [apiUrl, setApiUrl] = useState("");
  const [model, setModel] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeMode, setActiveMode] = useState(null);
  const [files, setFiles] = useState([]);
  const [activeFile, setActiveFile] = useState(null);
  const editor = useRef(null);
  const filePicker = useRef(null);
  const folderPicker = useRef(null);

  const importFiles = useCallback(async (event) => {
    const selected = Array.from(event.target.files || []).filter((file) => file.size <= 1_000_000 && !file.type.startsWith("image/"));
    const imported = await Promise.all(selected.map(async (file) => ({ name: file.name, path: file.webkitRelativePath || file.name, content: await file.text() })));
    setFiles((current) => {
      const next = [...current]; imported.forEach((file) => { const index = next.findIndex((item) => item.path === file.path); if (index >= 0) next[index] = file; else next.push(file); }); return next;
    });
    if (imported[0]) { setActiveFile(imported[0].path); setCode(imported[0].content); setLanguage(languageFor(imported[0].name)); }
    event.target.value = "";
  }, []);
  const openFile = useCallback((file) => { setActiveFile(file.path); setCode(file.content); setLanguage(languageFor(file.name)); }, []);

  const run = useCallback(async (mode) => {
    const position = editor.current?.getPosition() || { lineNumber: 1, column: 1 };
    const snippet = extractContext(code, position.lineNumber);
    const headers = { "Content-Type": "application/json" };
    if (apiKey.trim()) headers["x-codesense-api-key"] = apiKey.trim();
    headers["x-codesense-provider"] = provider;
    if (apiUrl.trim()) headers["x-codesense-api-url"] = apiUrl.trim();
    if (model.trim()) headers["x-codesense-model"] = model.trim();

    setLoading(true); setActiveMode(mode); setOutput("");
    try {
      const response = await fetch(`${API}/api/codesense`, { method: "POST", headers, body: JSON.stringify({ mode, language, snippet, cursorLine: position.lineNumber, cursorCol: position.column }) });
      if (!response.ok) { const error = await response.json(); throw new Error(error.message); }
      const reader = response.body?.getReader();
      if (!reader) throw new Error("The gateway returned an empty response.");
      const decoder = new TextDecoder(); let buffer = "";
      for (;;) {
        const { value, done } = await reader.read(); if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n"); buffer = events.pop() || "";
        for (const event of events) {
          const line = event.split("\n").find((item) => item.startsWith("data: "));
          if (!line) continue;
          const data = JSON.parse(line.slice(6));
          if (data === "[DONE]") continue;
          if (data.error) throw new Error(data.message);
          setOutput((current) => current + data.delta);
        }
      }
    } catch (error) { setOutput(`Unable to analyse code: ${error.message}`); }
    finally { setLoading(false); }
  }, [apiKey, apiUrl, code, language, model, provider]);

  const status = useMemo(() => loading ? "Analysing" : "Ready", [loading]);
  const actionLabel = activeMode ? `${activeMode[0].toUpperCase()}${activeMode.slice(1)} result` : "Code insight";

  return <main className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-mark">&lt;&gt;</span><div><h1>CodeSense</h1><p>Realtime source code analyzer</p></div></div>
      <div className="topbar-right"><span className="shortcut">⌘ ↵ to analyse</span><span className={`status ${loading ? "is-loading" : ""}`}><i />{status}</span></div>
    </header>
    <section className="workspace">
      <div className="editor-pane">
        <div className="editor-header"><div className="file-meta"><span className="file-dot" /><span>{activeFile || `untitled.${language === "javascript" ? "js" : language}`}</span><span className="muted">Local workspace</span></div><span className="cursor-location">Ln 1, Col 1</span></div>
        <div className="toolbar">
          <label className="language-select"><span>Language</span><select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="javascript">JavaScript</option><option value="typescript">TypeScript</option><option value="python">Python</option><option value="go">Go</option></select></label>
          <div className="actions"><button className="action-button import-button" onClick={() => filePicker.current?.click()}><Icon>＋</Icon> Files</button><button className="action-button import-button" onClick={() => folderPicker.current?.click()}><Icon>⊞</Icon> Folder</button><button className="action-button" disabled={loading} onClick={() => run("explain")}><Icon>✦</Icon> Explain</button><button className="action-button" disabled={loading} onClick={() => run("review")}><Icon>✓</Icon> Review</button><button className="action-button primary" disabled={loading} onClick={() => run("suggest")}><Icon>↳</Icon> Suggest</button></div>
        </div>
        <input ref={filePicker} className="file-picker" type="file" multiple onChange={importFiles} /><input ref={folderPicker} className="file-picker" type="file" webkitdirectory="" directory="" multiple onChange={importFiles} />
        {files.length > 0 && <div className="workspace-files"><span className="workspace-label">WORKSPACE · {files.length} FILE{files.length === 1 ? "" : "S"}</span><div className="file-list">{files.map((file) => <button className={`workspace-file ${activeFile === file.path ? "active" : ""}`} key={file.path} title={file.path} onClick={() => openFile(file)}><Icon>⌘</Icon>{file.path}</button>)}</div></div>}
        <Editor height="calc(100vh - 185px)" language={language} theme="vs-dark" value={code} onChange={(value) => setCode(value || "")} onMount={(instance) => { editor.current = instance; }} options={{ minimap: { enabled: false }, fontSize: 14, lineHeight: 22, fontFamily: "JetBrains Mono, Cascadia Code, Consolas, monospace", padding: { top: 20, bottom: 20 }, scrollBeyondLastLine: false, renderLineHighlight: "all" }} />
      </div>
      <aside className="insight-pane">
        <section className="provider-card"><div className="section-heading"><div><span className="eyebrow">PROVIDER</span><h2>Connection</h2></div><span className="connection-badge">Required</span></div><label>Provider<select value={provider} onChange={(event) => setProvider(event.target.value)}><option value="openai-compatible">OpenAI or compatible</option><option value="anthropic">Anthropic Claude</option><option value="gemini">Google Gemini</option></select></label><label>API key<input type="password" placeholder="Paste a provider key" value={apiKey} onChange={(event) => setApiKey(event.target.value)} autoComplete="off" required /></label>{provider !== "anthropic" && <label>Base URL <span className="optional">optional</span><input type="url" placeholder={provider === "gemini" ? "https://generativelanguage.googleapis.com/v1beta/openai/" : "https://api.provider.com/v1"} value={apiUrl} onChange={(event) => setApiUrl(event.target.value)} /></label>}<label>Model <span className="optional">optional</span><input type="text" placeholder={provider === "anthropic" ? "claude-3-5-haiku-latest" : provider === "gemini" ? "gemini-2.0-flash" : "gpt-4o-mini"} value={model} onChange={(event) => setModel(event.target.value)} /></label><p className="privacy-note"><Icon>⌁</Icon> Enter your own key. It is used for this request only and never stored.</p></section>
        <section className="insight-card"><div className="section-heading"><div><span className="eyebrow">{loading ? "STREAMING" : "ANALYSIS"}</span><h2>{actionLabel}</h2></div>{loading && <span className="streaming-dot">Live</span>}</div><div className={`insight-output ${loading ? "is-streaming" : ""}`}><pre>{output || <span className="caret">▋</span>}</pre></div></section>
        <footer className="sidebar-footer">Code is sent only when you run an action.</footer>
      </aside>
    </section>
  </main>;
}

createRoot(document.getElementById("root")).render(<App />);
