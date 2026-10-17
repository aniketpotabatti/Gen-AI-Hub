"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface StreamingOutputProps {
  content: string;
  isStreaming: boolean;
  currentSection?: string;
  isMaximized?: boolean;
  onToggleMaximize?: () => void;
}

export default function StreamingOutput({
  content,
  isStreaming,
  currentSection,
  isMaximized = false,
  onToggleMaximize,
}: StreamingOutputProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [viewMode, setViewMode] = useState<"rendered" | "raw">("rendered");
  const [copied, setCopied] = useState(false);

  // Auto-scroll to bottom while streaming
  useEffect(() => {
    if (isStreaming) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [content, isStreaming]);

  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0;
  const readTimeMin = Math.max(1, Math.ceil(wordCount / 200));

  const handleCopy = async () => {
    if (!content) return;
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!content && !isStreaming) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-center p-6">
        <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-2xl">
          📄
        </div>
        <div>
          <p className="text-white/60 text-xs font-medium">Output Preview Empty</p>
          <p className="text-white/30 text-[11px] mt-1 max-w-[220px]">
            Planned sections and synthesized markdown documentation will stream here live.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3.5 h-full">
      {/* Header Bar */}
      <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-semibold text-white/80 uppercase tracking-wider font-mono">
            03 — Documentation
          </h2>
          {isStreaming ? (
            <span className="flex items-center gap-1.5 text-[11px] text-violet-400 font-mono animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
              Writing: {currentSection || "section..."}
            </span>
          ) : (
            <span className="text-[11px] text-white/40 font-mono">
              {wordCount} words · ~{readTimeMin} min read
            </span>
          )}
        </div>

        {/* View mode toggle & Quick Copy */}
        <div className="flex items-center gap-1.5">
          <div className="flex items-center bg-white/[0.03] p-1 rounded-lg border border-white/[0.08]">
            <button
              type="button"
              onClick={() => setViewMode("rendered")}
              className={`px-2.5 py-0.5 rounded-md text-[11px] font-medium transition-all ${
                viewMode === "rendered"
                  ? "bg-violet-600/30 text-white border border-violet-500/30 shadow-sm"
                  : "text-white/40 hover:text-white"
              }`}
            >
              Preview
            </button>
            <button
              type="button"
              onClick={() => setViewMode("raw")}
              className={`px-2.5 py-0.5 rounded-md text-[11px] font-medium transition-all ${
                viewMode === "raw"
                  ? "bg-violet-600/30 text-white border border-violet-500/30 shadow-sm"
                  : "text-white/40 hover:text-white"
              }`}
            >
              Raw MD
            </button>
          </div>

          <button
            type="button"
            onClick={handleCopy}
            className="text-[11px] px-2.5 py-1 rounded-lg border border-white/10 hover:border-white/20 text-white/60 hover:text-white transition-all bg-white/[0.02]"
            title="Copy entire document"
          >
            {copied ? "✓ Copied" : "📋 Copy"}
          </button>

          {onToggleMaximize && (
            <button
              type="button"
              onClick={onToggleMaximize}
              title={isMaximized ? "Restore split layout" : "Large View (Maximize)"}
              className="w-7 h-7 rounded-lg border border-white/10 bg-white/[0.03] hover:bg-white/[0.08] hover:border-violet-500/40 text-white/60 hover:text-white flex items-center justify-center transition-all"
            >
              {isMaximized ? (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 9L4 4m0 0v5m0-5h5m6 6l5 5m0 0v-5m0 5h-5" />
                </svg>
              ) : (
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                </svg>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Output Content Area */}
      <div className="flex-1 overflow-y-auto rounded-xl border border-white/[0.08] bg-[#0c0c16] p-5 scrollbar-thin">
        {viewMode === "rendered" ? (
          <div className="doc-prose max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || "");
                  const isInline = !match;
                  return isInline ? (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  ) : (
                    <SyntaxHighlighter
                      style={oneDark}
                      language={match[1]}
                      PreTag="div"
                      customStyle={{
                        borderRadius: "10px",
                        border: "1px solid rgba(255,255,255,0.08)",
                        fontSize: "0.8rem",
                        margin: "1rem 0",
                        background: "#08080f",
                      }}
                    >
                      {String(children).replace(/\n$/, "")}
                    </SyntaxHighlighter>
                  );
                },
              }}
            >
              {content}
            </ReactMarkdown>

            {/* Blinking cursor while streaming */}
            {isStreaming && (
              <span className="inline-block w-0.5 h-4 bg-violet-400 ml-0.5 animate-pulse align-middle" />
            )}
          </div>
        ) : (
          <pre className="text-xs text-white/70 font-mono whitespace-pre-wrap leading-relaxed select-all">
            {content}
          </pre>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
