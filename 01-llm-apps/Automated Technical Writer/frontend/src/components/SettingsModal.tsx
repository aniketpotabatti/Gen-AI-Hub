"use client";

import { useState, useEffect } from "react";
import type { LLMConfig } from "@/lib/api";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: LLMConfig;
  onSave: (config: LLMConfig) => void;
}

const PROVIDER_MODELS = {
  gemini: [
    { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash (Recommended - Ultra Fast)" },
    { id: "gemini-1.5-pro", name: "Gemini 1.5 Pro (Deep Code Reasoning)" },
    { id: "gemini-1.5-flash", name: "Gemini 1.5 Flash (Fast)" },
  ],
  openai: [
    { id: "gpt-4o", name: "GPT-4o (Flagship Omni)" },
    { id: "gpt-4o-mini", name: "GPT-4o Mini (Fast & Cost Effective)" },
  ],
};

const TONE_OPTIONS = [
  { id: "balanced", label: "Balanced", desc: "Professional, clear, standard tech docs" },
  { id: "concise", label: "Concise", desc: "Short bullet points, minimal prose, direct" },
  { id: "tutorial", label: "Tutorial", desc: "Step-by-step guidance and detailed walkthroughs" },
  { id: "in-depth", label: "In-Depth", desc: "Deep architectural context and edge cases" },
] as const;

const AUDIENCE_OPTIONS = [
  { id: "beginner", label: "Beginner", desc: "Gentle concepts, clear explanations" },
  { id: "intermediate", label: "Intermediate", desc: "Standard developer-level depth" },
  { id: "expert", label: "Senior / Architect", desc: "Internal mechanics, concurrency, performance" },
] as const;

export default function SettingsModal({ isOpen, onClose, config, onSave }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<"api" | "style" | "about">("api");
  const [provider, setProvider] = useState<"gemini" | "openai">(config.provider || "gemini");
  const [apiKey, setApiKey] = useState(config.apiKey || "");
  const [model, setModel] = useState(config.model || "gemini-2.5-flash");
  const [tone, setTone] = useState<"balanced" | "concise" | "tutorial" | "in-depth">(
    config.tone || "balanced"
  );
  const [audience, setAudience] = useState<"beginner" | "intermediate" | "expert">(
    config.audience || "intermediate"
  );
  const [showKey, setShowKey] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    setProvider(config.provider || "gemini");
    setApiKey(config.apiKey || "");
    setModel(config.model || (config.provider === "openai" ? "gpt-4o" : "gemini-2.5-flash"));
    setTone(config.tone || "balanced");
    setAudience(config.audience || "intermediate");
  }, [config, isOpen]);

  if (!isOpen) return null;

  const handleProviderChange = (p: "gemini" | "openai") => {
    setProvider(p);
    setModel(p === "gemini" ? "gemini-2.5-flash" : "gpt-4o");
  };

  const handleSave = () => {
    onSave({
      provider,
      apiKey: apiKey.trim() || undefined,
      model,
      tone,
      audience,
    });
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
      onClose();
    }, 700);
  };

  const handleClearKey = () => {
    setApiKey("");
    onSave({
      provider,
      apiKey: undefined,
      model,
      tone,
      audience,
    });
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
    }, 1000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-2xl rounded-2xl border border-white/10 bg-[#0d0d16] shadow-2xl shadow-violet-500/10 flex flex-col max-h-[90vh] overflow-hidden">
        
        {/* Top Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.08] bg-[#11111d]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-violet-500/15 border border-violet-500/30 flex items-center justify-center text-lg text-violet-300">
              ⚙️
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Editor Settings & Functionalities</h2>
              <p className="text-xs text-white/50">Manage AI credentials, documentation tone, and features</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-white/40 hover:text-white hover:bg-white/5 flex items-center justify-center transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-2 px-6 pt-3 border-b border-white/[0.06] bg-[#0f0f1a]">
          <button
            type="button"
            onClick={() => setActiveTab("api")}
            className={`pb-2.5 px-3 text-xs font-medium border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === "api"
                ? "border-violet-400 text-white"
                : "border-transparent text-white/50 hover:text-white/80"
            }`}
          >
            <span>🔑</span> AI & API Keys
            {apiKey && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />}
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("style")}
            className={`pb-2.5 px-3 text-xs font-medium border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === "style"
                ? "border-violet-400 text-white"
                : "border-transparent text-white/50 hover:text-white/80"
            }`}
          >
            <span>🎯</span> Tone & Audience
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("about")}
            className={`pb-2.5 px-3 text-xs font-medium border-b-2 transition-all flex items-center gap-1.5 ${
              activeTab === "about"
                ? "border-violet-400 text-white"
                : "border-transparent text-white/50 hover:text-white/80"
            }`}
          >
            <span>ℹ️</span> System & Roadmap
          </button>
        </div>

        {/* Tab Content Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1 scrollbar-thin">
          
          {/* TAB 1: API KEYS & MODEL */}
          {activeTab === "api" && (
            <div className="space-y-5 animate-fade-in">
              {/* Provider Selection */}
              <div>
                <label className="block text-xs font-semibold text-white/70 uppercase tracking-wider mb-2">
                  AI Model Provider
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => handleProviderChange("gemini")}
                    className={`flex items-center justify-center gap-2.5 p-3 rounded-xl border text-sm font-medium transition-all ${
                      provider === "gemini"
                        ? "bg-violet-500/20 border-violet-500/50 text-white shadow-lg shadow-violet-500/10"
                        : "bg-white/[0.02] border-white/10 text-white/60 hover:border-white/20 hover:text-white"
                    }`}
                  >
                    <span>✨</span> Google Gemini
                  </button>
                  <button
                    type="button"
                    onClick={() => handleProviderChange("openai")}
                    className={`flex items-center justify-center gap-2.5 p-3 rounded-xl border text-sm font-medium transition-all ${
                      provider === "openai"
                        ? "bg-emerald-500/20 border-emerald-500/50 text-white shadow-lg shadow-emerald-500/10"
                        : "bg-white/[0.02] border-white/10 text-white/60 hover:border-white/20 hover:text-white"
                    }`}
                  >
                    <span>🤖</span> OpenAI GPT-4o
                  </button>
                </div>
              </div>

              {/* Model Selection */}
              <div>
                <label className="block text-xs font-semibold text-white/70 uppercase tracking-wider mb-2">
                  Target Model
                </label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full bg-[#151524] border border-white/10 rounded-xl px-3.5 py-2.5 text-sm text-white focus:border-violet-500 focus:outline-none transition-colors"
                >
                  {PROVIDER_MODELS[provider].map((m) => (
                    <option key={m.id} value={m.id} className="bg-[#151524] text-white">
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* API Key Input */}
              <div className="p-4 rounded-xl border border-white/[0.07] bg-white/[0.02]">
                <div className="flex items-center justify-between mb-2">
                  <label className="text-xs font-semibold text-white/80 uppercase tracking-wider">
                    {provider === "gemini" ? "Google Gemini API Key" : "OpenAI API Key"}
                  </label>
                  <a
                    href={
                      provider === "gemini"
                        ? "https://aistudio.google.com/app/apikey"
                        : "https://platform.openai.com/api-keys"
                    }
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs text-violet-400 hover:text-violet-300 underline"
                  >
                    Get API key ↗
                  </a>
                </div>

                <div className="relative">
                  <input
                    type={showKey ? "text" : "password"}
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    placeholder={
                      provider === "gemini"
                        ? "AIzaSy... (leave blank to use server .env)"
                        : "sk-... (leave blank to use server .env)"
                    }
                    className="w-full bg-[#151524] border border-white/10 rounded-xl px-3.5 py-2.5 pr-12 text-sm text-white placeholder:text-white/20 focus:border-violet-500 focus:outline-none transition-colors font-mono"
                  />
                  <button
                    type="button"
                    onClick={() => setShowKey((p) => !p)}
                    className="absolute right-3 top-2.5 text-xs text-white/40 hover:text-white/80 transition-colors"
                  >
                    {showKey ? "Hide" : "Show"}
                  </button>
                </div>

                <div className="flex items-center justify-between mt-2.5">
                  <p className="text-[11px] text-white/40 leading-relaxed">
                    🔒 Stored locally in your browser cache. Fallback applies when blank.
                  </p>
                  {apiKey && (
                    <button
                      type="button"
                      onClick={handleClearKey}
                      className="text-[11px] text-red-400/80 hover:text-red-300 underline transition-colors"
                    >
                      Clear key
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: STYLE & AUDIENCE */}
          {activeTab === "style" && (
            <div className="space-y-5 animate-fade-in">
              {/* Tone selection */}
              <div>
                <label className="block text-xs font-semibold text-white/70 uppercase tracking-wider mb-2">
                  Documentation Tone
                </label>
                <div className="grid grid-cols-2 gap-2.5">
                  {TONE_OPTIONS.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setTone(t.id)}
                      className={`text-left p-3 rounded-xl border transition-all ${
                        tone === t.id
                          ? "bg-violet-500/20 border-violet-500/50 shadow-md shadow-violet-500/10"
                          : "bg-white/[0.02] border-white/10 hover:border-white/20"
                      }`}
                    >
                      <div className="text-xs font-semibold text-white">{t.label}</div>
                      <div className="text-[11px] text-white/40 mt-0.5">{t.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Target Audience selection */}
              <div>
                <label className="block text-xs font-semibold text-white/70 uppercase tracking-wider mb-2">
                  Target Audience
                </label>
                <div className="grid grid-cols-3 gap-2.5">
                  {AUDIENCE_OPTIONS.map((a) => (
                    <button
                      key={a.id}
                      type="button"
                      onClick={() => setAudience(a.id)}
                      className={`text-left p-3 rounded-xl border transition-all ${
                        audience === a.id
                          ? "bg-cyan-500/20 border-cyan-500/50 shadow-md shadow-cyan-500/10"
                          : "bg-white/[0.02] border-white/10 hover:border-white/20"
                      }`}
                    >
                      <div className="text-xs font-semibold text-white">{a.label}</div>
                      <div className="text-[11px] text-white/40 mt-0.5">{a.desc}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: ABOUT & FUTURE EXTENSIONS */}
          {activeTab === "about" && (
            <div className="space-y-4 animate-fade-in text-xs text-white/70">
              <div className="p-4 rounded-xl border border-white/10 bg-white/[0.02] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white">AutoWriter AI Engine</span>
                  <span className="px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 font-mono text-[10px]">
                    v0.2.0 (AST + Stream)
                  </span>
                </div>
                <p className="text-white/50 text-[11px] leading-relaxed">
                  AST code-aware parsing directly drives section planning and streaming documentation synthesis token-by-token.
                </p>
              </div>

              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-white/80 uppercase tracking-wider">
                  Future Functionalities Coming to this Panel:
                </h4>
                <ul className="space-y-1.5 text-white/50 text-[11px]">
                  <li className="flex items-center gap-2">
                    <span>🧬</span> <strong>Style DNA Upload</strong>: Upload existing markdown docs to mirror team phrasing.
                  </li>
                  <li className="flex items-center gap-2">
                    <span>🔁</span> <strong>GitHub Living Docs</strong>: Webhook syncing for continuous PR documentation.
                  </li>
                  <li className="flex items-center gap-2">
                    <span>📦</span> <strong>Direct Export</strong>: 1-click sync to Notion, Confluence, and GitBook.
                  </li>
                </ul>
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-white/[0.08] bg-[#11111d]">
          <span className="text-[11px] text-white/40 font-mono">
            {provider.toUpperCase()} · {model.replace("gemini-", "").replace("gpt-", "")} · {tone}
          </span>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-medium text-white/60 hover:text-white hover:bg-white/5 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              id="save-settings-btn"
              onClick={handleSave}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-600 text-white text-xs font-semibold hover:from-violet-500 hover:to-cyan-500 transition-all shadow-lg shadow-violet-500/20"
            >
              {savedSuccess ? "✓ Settings Saved!" : "Save Settings"}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
}
