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

const SAMPLE_TEMPLATES = [
  {
    name: "Python FastAPI",
    filename: "auth_service.py",
    code: `"""
Authentication and JWT token management service.
Provides user verification, token generation, and password hashing.
"""
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr

class TokenPayload(BaseModel):
    user_id: str
    email: EmailStr
    role: str = "member"
    exp: datetime

class AuthService:
    """Manages secure authentication lifecycles and token validation."""

    def __init__(self, secret_key: str, token_ttl_minutes: int = 60):
        self.secret_key = secret_key
        self.ttl = timedelta(minutes=token_ttl_minutes)

    def hash_password(self, plain_password: str) -> str:
        """Hash a plaintext password using a salt and hash algorithm."""
        # Simulated secure hashing
        return f"hashed_{plain_password}_secure"

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify that the supplied plaintext password matches the stored hash."""
        return self.hash_password(plain_password) == hashed_password

    def generate_token(self, user_id: str, email: str, role: str = "member") -> str:
        """Issue a signed JWT token valid for the configured TTL."""
        expiry = datetime.utcnow() + self.ttl
        payload = TokenPayload(user_id=user_id, email=email, role=role, exp=expiry)
        return f"jwt.{payload.user_id}.signature"

    def validate_token(self, token: str) -> Optional[TokenPayload]:
        """Decode and validate a token's integrity and expiration."""
        if not token.startswith("jwt."):
            return None
        return TokenPayload(user_id="user_123", email="user@example.com", role="member", exp=datetime.utcnow() + timedelta(hours=1))
`,
  },
  {
    name: "TypeScript Client",
    filename: "cacheClient.ts",
    code: `/**
 * Resilient In-Memory LRU Cache with TTL expiry support.
 */

export interface CacheEntry<T> {
  value: T;
  expiresAt: number;
}

export class LRUCache<T> {
  private capacity: number;
  private defaultTtlMs: number;
  private store: Map<string, CacheEntry<T>>;

  constructor(capacity: number = 100, defaultTtlMs: number = 60000) {
    this.capacity = capacity;
    this.defaultTtlMs = defaultTtlMs;
    this.store = new Map();
  }

  public get(key: string): T | null {
    const entry = this.store.get(key);
    if (!entry) return null;
    if (Date.now() > entry.expiresAt) {
      this.store.delete(key);
      return null;
    }
    // Re-insert to refresh LRU order
    this.store.delete(key);
    this.store.set(key, entry);
    return entry.value;
  }

  public set(key: string, value: T, ttlMs?: number): void {
    if (this.store.has(key)) {
      this.store.delete(key);
    } else if (this.store.size >= this.capacity) {
      const oldestKey = this.store.keys().next().value;
      if (oldestKey) this.store.delete(oldestKey);
    }
    const expiresAt = Date.now() + (ttlMs ?? this.defaultTtlMs);
    this.store.set(key, { value, expiresAt });
  }

  public clear(): void {
    this.store.clear();
  }
}
`,
  },
];

function detectLanguage(filename: string): string {
  const ext = "." + filename.split(".").pop()?.toLowerCase();
  return EXTENSION_MAP[ext] || "text";
}

export default function CodeUploader({ onCodeReady, isLoading }: CodeUploaderProps) {
  const [code, setCode] = useState("");
  const [filename, setFilename] = useState("auth_service.py");
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

      {/* Filename input & Quick Templates */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-1">
          <span className="text-white/30 text-sm">📄</span>
          <input
            type="text"
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            className="w-full bg-transparent text-sm text-white/70 border-b border-white/10 focus:border-violet-500/50 outline-none pb-1 transition-colors placeholder:text-white/20 font-mono"
            placeholder="filename.py"
            id="filename-input"
          />
        </div>

        {/* Quick presets */}
        <div className="flex items-center gap-1.5 self-end sm:self-auto">
          <span className="text-[11px] text-white/40">Presets:</span>
          {SAMPLE_TEMPLATES.map((tmpl) => (
            <button
              key={tmpl.name}
              type="button"
              onClick={() => {
                setFilename(tmpl.filename);
                setCode(tmpl.code);
              }}
              className="text-[11px] px-2 py-0.5 rounded-md bg-white/5 hover:bg-violet-500/20 text-white/60 hover:text-violet-300 border border-white/5 hover:border-violet-500/20 transition-all font-medium"
            >
              {tmpl.name}
            </button>
          ))}
        </div>
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
