"use client";

import { useState, useEffect } from "react";
import type { LLMConfig } from "@/lib/api";

interface ApiKeyModalProps {
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

export default function ApiKeyModal({ isOpen, onClose, config, onSave }: ApiKeyModalProps) {
  const [provider, setProvider] = useState<"gemini" | "openai">(config.provider || "gemini");
  const [apiKey, setApiKey] = useState(config.apiKey || "");
  const [model, setModel] = useState(config.model || "gemini-2.5-flash");
  const [showKey, setShowKey] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    setProvider(config.provider || "gemini");
    setApiKey(config.apiKey || "");
    setModel(config.model || (config.provider === "openai" ? "gpt-4o" : "gemini-2.5-flash"));
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
    });
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
      onClose();
    }, 800);
  };

  const handleClear = () => {
    setApiKey("");
    onSave({
      provider,
      apiKey: undefined,
      model,
    });
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
      onClose();
    }, 600);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-lg rounded-2xl border border-white/10 bg-[#0f0f17] p-6 shadow-2xl shadow-violet-500/10">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-lg">
              🔑
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">LLM & API Key Settings</h2>
              <p className="text-xs text-white/50">Configure your model & personal API key</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg text-white/40 hover:text-white hover:bg-white/5 flex items-center justify-center transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="py-5 space-y-5">
          {/* Provider Selection */}
          <div>
            <label className="block text-xs font-semibold text-white/70 uppercase tracking-wider mb-2">
              AI Provider
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => handleProviderChange("gemini")}
                className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-sm font-medium transition-all ${
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
                className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-sm font-medium transition-all ${
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
              Model
            </label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full bg-[#151522] border border-white/10 rounded-xl px-3.5 py-2.5 text-sm text-white/90 focus:border-violet-500 focus:outline-none transition-colors"
            >
              {PROVIDER_MODELS[provider].map((m) => (
                <option key={m.id} value={m.id} className="bg-[#151522] text-white">
                  {m.name}
                </option>
              ))}
            </select>
          </div>

          {/* API Key Input */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-white/70 uppercase tracking-wider">
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
                className="w-full bg-[#151522] border border-white/10 rounded-xl px-3.5 py-2.5 pr-10 text-sm text-white placeholder:text-white/20 focus:border-violet-500 focus:outline-none transition-colors font-mono"
              />
              <button
                type="button"
                onClick={() => setShowKey((p) => !p)}
                className="absolute right-3 top-2.5 text-xs text-white/40 hover:text-white/80 transition-colors"
              >
                {showKey ? "Hide" : "Show"}
              </button>
            </div>

            <p className="text-[11px] text-white/40 mt-1.5 leading-relaxed">
              🔒 Key is stored locally in your browser. Leave blank if your backend server already has the <code className="text-white/60">.env</code> configured.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between pt-4 border-t border-white/10">
          <button
            type="button"
            onClick={handleClear}
            className="text-xs text-white/40 hover:text-red-400 transition-colors px-2 py-1"
          >
            Clear Stored Key
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-medium text-white/60 hover:text-white hover:bg-white/5 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              id="save-api-key-btn"
              onClick={handleSave}
              className="px-5 py-2 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-600 text-white text-xs font-semibold hover:from-violet-500 hover:to-cyan-500 transition-all shadow-lg shadow-violet-500/20"
            >
              {savedSuccess ? "✓ Saved!" : "Save Configuration"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
