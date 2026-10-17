"use client";

import { useState, useRef, useCallback } from "react";
import type { CodeContext, CodeFileEntry } from "@/lib/api";

interface CodeUploaderProps {
  onCodeReady: (code: string, filename: string, files?: CodeFileEntry[]) => void;
  isLoading?: boolean;
  codeContext?: CodeContext | null;
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
  ".cpp": "cpp",
  ".c": "c",
};

const SAMPLE_TEMPLATES = [
  {
    name: "FastAPI Auth",
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
    name: "TS Cache Client",
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
  {
    name: "Go CLI Router",
    filename: "router.go",
    code: `package router

import (
	"context"
	"errors"
	"net/http"
	"time"
)

type RouteHandler func(ctx context.Context, w http.ResponseWriter, r *http.Request) error

type Router struct {
	routes  map[string]RouteHandler
	timeout time.Duration
}

func NewRouter(timeout time.Duration) *Router {
	return &Router{
		routes:  make(map[string]RouteHandler),
		timeout: timeout,
	}
}

func (r *Router) Register(pattern string, handler RouteHandler) {
	r.routes[pattern] = handler
}

func (r *Router) ServeHTTP(w http.ResponseWriter, req *http.Request) {
	handler, exists := r.routes[req.URL.Path]
	if !exists {
		http.NotFound(w, req)
		return
	}
	ctx, cancel := context.WithTimeout(req.Context(), r.timeout)
	defer cancel()

	if err := handler(ctx, w, req); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}
`,
  },
];

function detectLanguage(filename: string): string {
  const ext = "." + filename.split(".").pop()?.toLowerCase();
  return EXTENSION_MAP[ext] || "text";
}

const SUPPORTED_EXTS = new Set([
  ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rs", ".cpp", ".c", ".h", ".hpp", ".cs", ".php", ".rb", ".json", ".yaml", ".yml", ".md"
]);

function isSupportedFile(name: string): boolean {
  const dotIdx = name.lastIndexOf(".");
  if (dotIdx === -1) return false;
  const ext = name.slice(dotIdx).toLowerCase();
  return SUPPORTED_EXTS.has(ext);
}

export default function CodeUploader({ onCodeReady, isLoading, codeContext }: CodeUploaderProps) {
  const [activeTab, setActiveTab] = useState<"code" | "files" | "ast">("code");
  const [code, setCode] = useState(SAMPLE_TEMPLATES[0].code);
  const [filename, setFilename] = useState(SAMPLE_TEMPLATES[0].filename);
  const [uploadedFiles, setUploadedFiles] = useState<CodeFileEntry[]>([]);
  const [selectedFileIdx, setSelectedFileIdx] = useState<number>(0);
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const language = detectLanguage(filename);
  const langColor = LANGUAGE_COLORS[language] || "bg-white/10 text-white/60 border-white/20";

  // Process multiple loaded files into CodeFileEntry list
  const processFiles = useCallback(async (fileList: FileList | File[]) => {
    const validFiles: File[] = [];
    for (let i = 0; i < fileList.length; i++) {
      const f = fileList[i];
      // Ignore git and hidden files
      if (f.name.startsWith(".") || f.name.includes("node_modules")) continue;
      if (isSupportedFile(f.name)) {
        validFiles.push(f);
      }
    }

    if (validFiles.length === 0) return;

    if (validFiles.length === 1) {
      const file = validFiles[0];
      const text = await file.text();
      setFilename(file.name);
      setCode(text);
      setUploadedFiles([]);
      setActiveTab("code");
    } else {
      // Multi-file or folder
      const entries: CodeFileEntry[] = [];
      for (const file of validFiles) {
        try {
          const text = await file.text();
          // Use webkitRelativePath if available for directory hierarchy
          const relName = (file as any).webkitRelativePath || file.name;
          entries.push({ filename: relName, code: text });
        } catch (e) {
          console.error("Failed to read file", file.name, e);
        }
      }

      setUploadedFiles(entries);
      setSelectedFileIdx(0);
      setFilename(`project_${entries.length}_files`);
      setCode(entries[0].code);
      setActiveTab("files");
    }
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      if (e.dataTransfer.items) {
        const fileList: File[] = [];
        for (let i = 0; i < e.dataTransfer.items.length; i++) {
          const item = e.dataTransfer.items[i];
          if (item.kind === "file") {
            const f = item.getAsFile();
            if (f) fileList.push(f);
          }
        }
        await processFiles(fileList);
      } else if (e.dataTransfer.files) {
        await processFiles(e.dataTransfer.files);
      }
    },
    [processFiles]
  );

  const handleAnalyze = () => {
    if (uploadedFiles.length > 0) {
      onCodeReady(code, filename, uploadedFiles);
    } else {
      if (!code.trim()) return;
      onCodeReady(code, filename);
    }
  };

  const lineCount = code.split("\n").length;
  const charCount = code.length;

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* Top Header with Tab Switcher */}
      <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
        <div className="flex items-center gap-1.5 bg-white/[0.03] p-1 rounded-xl border border-white/[0.08]">
          <button
            type="button"
            onClick={() => setActiveTab("code")}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
              activeTab === "code"
                ? "bg-violet-600/30 text-white border border-violet-500/30 shadow-sm"
                : "text-white/50 hover:text-white"
            }`}
          >
            💻 Code
          </button>

          {uploadedFiles.length > 0 && (
            <button
              type="button"
              onClick={() => setActiveTab("files")}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                activeTab === "files"
                  ? "bg-violet-600/30 text-white border border-violet-500/30 shadow-sm"
                  : "text-white/50 hover:text-white"
              }`}
            >
              <span>📁 Project ({uploadedFiles.length})</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setActiveTab("ast")}
            className={`px-3 py-1 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
              activeTab === "ast"
                ? "bg-cyan-600/30 text-white border border-cyan-500/30 shadow-sm"
                : "text-white/50 hover:text-white"
            }`}
          >
            <span>🌳 AST Symbols</span>
            {codeContext && (
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
            )}
          </button>
        </div>

        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium font-mono ${langColor}`}>
          <span className="w-1.5 h-1.5 rounded-full bg-current" />
          {language}
        </div>
      </div>

      {/* Filename & Quick Presets Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.06]">
        <div className="flex items-center gap-2 flex-1">
          <span className="text-white/40 text-xs">📄</span>
          <input
            type="text"
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            className="w-full bg-transparent text-xs text-white/80 border-b border-white/10 focus:border-violet-500 outline-none pb-0.5 transition-colors placeholder:text-white/20 font-mono"
            placeholder="filename.py"
            id="filename-input"
          />
        </div>

        {/* Quick presets */}
        {uploadedFiles.length === 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] text-white/40 uppercase tracking-wider font-semibold">Presets:</span>
            {SAMPLE_TEMPLATES.map((tmpl) => (
              <button
                key={tmpl.name}
                type="button"
                onClick={() => {
                  setFilename(tmpl.filename);
                  setCode(tmpl.code);
                  setUploadedFiles([]);
                }}
                className="text-[11px] px-2 py-0.5 rounded-md bg-white/5 hover:bg-violet-500/20 text-white/70 hover:text-violet-300 border border-white/5 hover:border-violet-500/30 transition-all font-mono"
              >
                {tmpl.name}
              </button>
            ))}
          </div>
        )}

        {uploadedFiles.length > 0 && (
          <button
            type="button"
            onClick={() => {
              setUploadedFiles([]);
              setFilename(SAMPLE_TEMPLATES[0].filename);
              setCode(SAMPLE_TEMPLATES[0].code);
              setActiveTab("code");
            }}
            className="text-[11px] text-white/40 hover:text-red-400 transition-colors"
          >
            Clear Project Files
          </button>
        )}
      </div>

      {/* MAIN VIEW AREA */}
      {activeTab === "files" && uploadedFiles.length > 0 ? (
        /* Multi-File Explorer & Preview */
        <div className="flex-1 grid grid-cols-1 md:grid-cols-[200px_1fr] gap-2 rounded-xl border border-white/[0.08] bg-[#0b0b13] overflow-hidden">
          {/* File sidebar */}
          <div className="border-r border-white/[0.06] p-2 overflow-y-auto space-y-1 max-h-[340px] scrollbar-thin">
            <div className="text-[10px] uppercase tracking-wider text-white/40 font-semibold px-2 py-1 font-mono">
              Project Files ({uploadedFiles.length})
            </div>
            {uploadedFiles.map((f, idx) => (
              <button
                key={f.filename}
                type="button"
                onClick={() => {
                  setSelectedFileIdx(idx);
                  setCode(f.code);
                  setFilename(f.filename.split("/").pop() || f.filename);
                }}
                className={`w-full text-left px-2.5 py-1.5 rounded-lg text-xs truncate transition-all font-mono flex items-center justify-between ${
                  selectedFileIdx === idx
                    ? "bg-violet-500/20 text-violet-200 border border-violet-500/30"
                    : "text-white/60 hover:text-white hover:bg-white/[0.02]"
                }`}
              >
                <span className="truncate">{f.filename}</span>
                <span className="text-[10px] text-white/30 font-mono ml-1">
                  {f.code.split("\n").length}L
                </span>
              </button>
            ))}
          </div>

          {/* Active file code viewer */}
          <div className="flex flex-col overflow-hidden">
            <textarea
              id="project-code-input"
              value={code}
              onChange={(e) => {
                const newCode = e.target.value;
                setCode(newCode);
                const updated = [...uploadedFiles];
                updated[selectedFileIdx].code = newCode;
                setUploadedFiles(updated);
              }}
              className="w-full flex-1 min-h-[260px] bg-transparent text-xs text-white/80 font-mono p-3 resize-none outline-none leading-relaxed scrollbar-thin"
              spellCheck={false}
            />
            <div className="px-3 py-1 bg-[#0e0e18] border-t border-white/[0.06] flex items-center justify-between text-[11px] text-white/40 font-mono">
              <span>{uploadedFiles[selectedFileIdx]?.filename} · {lineCount} lines</span>
            </div>
          </div>
        </div>
      ) : activeTab === "code" ? (
        /* Single Code Editor View */
        <div
          className={`relative flex-1 rounded-xl border transition-all duration-200 overflow-hidden flex flex-col ${
            isDragging
              ? "border-violet-500 bg-violet-500/10"
              : "border-white/[0.08] bg-[#0b0b13]"
          }`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
        >
          {isDragging ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 pointer-events-none">
              <span className="text-4xl">⬇️</span>
              <p className="text-violet-300 font-medium text-sm">Drop file(s) or folder to load</p>
            </div>
          ) : (
            <textarea
              id="code-input"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="w-full h-full min-h-[300px] bg-transparent text-xs text-white/80 font-mono p-4 resize-none outline-none placeholder:text-white/20 leading-relaxed scrollbar-thin"
              placeholder={`# Paste source code here, or drop multiple files / project folder...`}
              spellCheck={false}
            />
          )}

          {/* Code metrics footer */}
          <div className="px-3 py-1.5 bg-[#0e0e18] border-t border-white/[0.06] flex items-center justify-between text-[11px] text-white/40 font-mono">
            <span>{lineCount} lines · {charCount} chars</span>
            <button
              type="button"
              onClick={() => setCode("")}
              className="hover:text-red-400 transition-colors"
            >
              Clear
            </button>
          </div>
        </div>
      ) : (
        /* AST Inspector View */
        <div className="flex-1 rounded-xl border border-white/[0.08] bg-[#0b0b13] p-4 overflow-y-auto space-y-4 scrollbar-thin">
          {!codeContext ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-10 gap-2">
              <span className="text-2xl">🔍</span>
              <p className="text-white/50 text-xs">No AST data parsed yet</p>
              <p className="text-white/30 text-[11px]">Click &ldquo;Parse AST & Plan Docs&rdquo; below to extract symbols</p>
            </div>
          ) : (
            <div className="space-y-4 text-xs">
              {/* Context Summary Cards */}
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                  <div className="text-violet-400 font-bold font-mono text-sm">{codeContext.functions.length}</div>
                  <div className="text-[10px] text-white/40">Functions</div>
                </div>
                <div className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                  <div className="text-cyan-400 font-bold font-mono text-sm">{codeContext.classes.length}</div>
                  <div className="text-[10px] text-white/40">Classes</div>
                </div>
                <div className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                  <div className="text-emerald-400 font-bold font-mono text-sm">{codeContext.imports.length}</div>
                  <div className="text-[10px] text-white/40">Imports</div>
                </div>
              </div>

              {/* Functions List */}
              {codeContext.functions.length > 0 && (
                <div>
                  <h4 className="text-[11px] font-semibold text-white/60 uppercase tracking-wider mb-2 font-mono">
                    Functions & Methods ({codeContext.functions.length})
                  </h4>
                  <div className="space-y-1.5">
                    {codeContext.functions.map((fn) => (
                      <div
                        key={fn.name + Math.random()}
                        className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.06] font-mono text-[11px]"
                      >
                        <div className="text-violet-300 font-semibold truncate">
                          def {fn.name}({fn.params.join(", ")}) ➔ {fn.return_type || "None"}
                        </div>
                        {fn.docstring && (
                          <div className="text-white/40 font-sans text-[11px] mt-1 italic">
                            &quot;{fn.docstring}&quot;
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Classes List */}
              {codeContext.classes.length > 0 && (
                <div>
                  <h4 className="text-[11px] font-semibold text-white/60 uppercase tracking-wider mb-2 font-mono">
                    Classes & Structures ({codeContext.classes.length})
                  </h4>
                  <div className="space-y-1.5">
                    {codeContext.classes.map((cls) => (
                      <div
                        key={cls.name + Math.random()}
                        className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.06] font-mono text-[11px]"
                      >
                        <div className="text-cyan-300 font-semibold">
                          class {cls.name}({cls.base_classes.join(", ")})
                        </div>
                        {cls.methods.length > 0 && (
                          <div className="text-white/40 text-[10px] mt-1 pl-2 border-l border-white/10">
                            Methods: {cls.methods.map((m) => m.name).join(", ")}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Actions Toolbar */}
      <div className="flex items-center gap-2 pt-1">
        {/* Upload Multiple Files Button */}
        <button
          id="upload-files-btn"
          type="button"
          onClick={() => fileInputRef.current?.click()}
          title="Select one or multiple code files"
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-white/10 text-xs font-medium text-white/70 hover:text-white hover:border-white/20 transition-all bg-white/[0.02]"
        >
          📄 Files
        </button>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          accept=".py,.js,.jsx,.ts,.tsx,.go,.java,.rs,.cpp,.c,.h,.hpp,.cs,.php,.rb,.json,.yaml,.yml"
          onChange={(e) => e.target.files && processFiles(e.target.files)}
        />

        {/* Upload Entire Folder Button */}
        <button
          id="upload-folder-btn"
          type="button"
          onClick={() => folderInputRef.current?.click()}
          title="Upload an entire project directory"
          className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-white/10 text-xs font-medium text-white/70 hover:text-white hover:border-white/20 transition-all bg-white/[0.02]"
        >
          📁 Folder
        </button>
        <input
          ref={folderInputRef}
          type="file"
          {...({ webkitdirectory: "", directory: "" } as any)}
          multiple
          className="hidden"
          onChange={(e) => e.target.files && processFiles(e.target.files)}
        />

        {/* Primary Action Button */}
        <button
          id="analyze-btn"
          type="button"
          onClick={handleAnalyze}
          disabled={(!code.trim() && uploadedFiles.length === 0) || isLoading}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-600 text-white text-xs font-semibold
            hover:from-violet-500 hover:to-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-violet-500/20
            hover:shadow-violet-500/40 hover:-translate-y-0.5 disabled:hover:translate-y-0"
        >
          {isLoading ? (
            <>
              <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Parsing Codebase & Planning...</span>
            </>
          ) : (
            <>
              <span>
                🔍 Parse {uploadedFiles.length > 0 ? `Project (${uploadedFiles.length} files)` : "AST"} & Plan Docs
              </span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
