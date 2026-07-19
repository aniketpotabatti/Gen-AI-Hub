"use client";

import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

interface StreamingOutputProps {
  content: string;
  isStreaming: boolean;
  currentSection?: string;
}

export default function StreamingOutput({
  content,
  isStreaming,
  currentSection,
}: StreamingOutputProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom while streaming
  useEffect(() => {
    if (isStreaming) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [content, isStreaming]);

  if (!content && !isStreaming) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
        <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-3xl">
          📄
        </div>
        <div>
          <p className="text-white/40 text-sm">Generated documentation will appear here</p>
          <p className="text-white/20 text-xs mt-1">Plan your docs and click &ldquo;Generate All Sections&rdquo;</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          03 — Generated Docs
        </h2>
        {isStreaming && (
          <span className="flex items-center gap-1.5 text-xs text-violet-400">
            <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
            Writing {currentSection || "..."}
          </span>
        )}
      </div>

      {/* Markdown output */}
      <div className="flex-1 overflow-y-auto rounded-xl border border-white/[0.07] bg-white/[0.02] p-5 scrollbar-thin">
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
                      border: "1px solid rgba(255,255,255,0.07)",
                      fontSize: "0.8rem",
                      margin: "1rem 0",
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

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
