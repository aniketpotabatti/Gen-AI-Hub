"use client";

import { useState, useRef, useCallback } from "react";

interface CodeUploaderProps {
  onCodeReady: (code: string, filename: string) => void;
  isLoading?: boolean;
}

const LANGUAGE_COLORS: Record<string, string> = {
  python: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  javascript: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  typescript: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
  go: "bg-teal-500/20 text-teal-300 border-teal-500/30",
  java: "bg-orange-500/20 text-orange-300 border-orange-500/30",
  rust: "bg-red-500/20 text-red-300 border-red-500/30",
};

const EXTENSION_MAP: Record<string, string> = {
  ".py": "python",
  ".js": "javascript",
  ".jsx": "javascript",
  ".ts": "typescript",
  ".tsx": "typescript",
  ".go": "go",
  ".java": "java",
  ".rs": "rust",
};

function detectLanguage(filename: string): string {
  const ext = "." + filename.split(".").pop()?.toLowerCase();
  return EXTENSION_MAP[ext] || "text";
}

export default function CodeUploader({ onCodeReady, isLoading }: CodeUploaderProps) {
  const [code, setCode] = useState("");
  const [filename, setFilename] = useState("main.py");
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const language = detectLanguage(filename);
  const langColor = LANGUAGE_COLORS[language] || "bg-white/10 text-white/60 border-white/20";

  const handleFile = useCallback((file: File) => {
    setFilename(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      setCode(text);
    };
    reader.readAsText(file);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) {
        handleFile(file);
      }
    },
    [handleFile]
  );

  const handleAnalyze = () => {
    if (!code.trim()) return;
    onCodeReady(code, filename);
  };

  const lineCount = code.split("\n").length;

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          01 — Source Code
        </h2>
        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${langColor}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          {language}
        </div>
      </div>

      {/* Filename input */}
      <div className="flex items-center gap-2">
        <span className="text-white/30 text-sm">📄</span>
        <input
          type="text"
          value={filename}
          onChange={(e) => setFilename(e.target.value)}
          className="flex-1 bg-transparent text-sm text-white/70 border-b border-white/10 focus:border-violet-500/50 outline-none pb-1 transition-colors placeholder:text-white/20"
          placeholder="filename.py"
          id="filename-input"
        />
      </div>

      {/* Drop zone / Textarea */}
      <div
        className={`relative flex-1 rounded-xl border transition-all duration-200 overflow-hidden ${isDragging
          ? "border-violet-500 bg-violet-500/10"
          : "border-white/10 bg-white/[0.03] hover:border-white/20"
          }`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        {isDragging ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 pointer-events-none">
            <span className="text-4xl">⬇️</span>
            <p className="text-violet-300 font-medium">Drop your file here</p>
          </div>
        ) : (
          <textarea
            id="code-input"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="w-full h-full min-h-[280px] bg-transparent text-sm text-white/80 font-mono p-4 resize-none outline-none placeholder:text-white/20 leading-relaxed"
            placeholder={`# Paste your code here, or drag & drop a file\n\ndef hello_world(name: str) -> str:\n    """Greet someone by name."""\n    return f"Hello, {name}!"`}
            spellCheck={false}
          />
        )}

        {code && (
          <div className="absolute bottom-3 right-3 text-xs text-white/20 font-mono">
            {lineCount} lines
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          id="upload-file-btn"
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border border-white/10 text-sm text-white/60 hover:text-white hover:border-white/20 transition-all"
        >
          📁 Open File
        </button>
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".py,.js,.jsx,.ts,.tsx,.go,.java,.rs,.cpp,.c"
          onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
        />

        <button
          id="analyze-btn"
          type="button"
          onClick={handleAnalyze}
          disabled={!code.trim() || isLoading}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-r from-violet-600 to-violet-500 text-white text-sm font-semibold
            hover:from-violet-500 hover:to-violet-400 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-violet-500/20
            hover:shadow-violet-500/40 hover:-translate-y-0.5 disabled:hover:translate-y-0"
        >
          {isLoading ? (
            <>
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              🔍 Parse & Analyze
            </>
          )}
        </button>
      </div>
    </div>
  );
}
