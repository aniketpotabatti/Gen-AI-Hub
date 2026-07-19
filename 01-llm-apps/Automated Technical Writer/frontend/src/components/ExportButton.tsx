"use client";

import { useState } from "react";
import type { DocPlan } from "@/lib/api";
import { exportMarkdown, exportHtml } from "@/lib/api";

interface ExportButtonProps {
  plan: DocPlan | null;
  sectionsContent: Record<string, string>;
  fullContent: string;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ExportButton({ plan, sectionsContent, fullContent }: ExportButtonProps) {
  const [isExporting, setIsExporting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

  const hasContent = fullContent.trim().length > 0;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(fullContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExportMd = async () => {
    if (!plan) return;
    setIsExporting(true);
    setShowMenu(false);
    try {
      const blob = await exportMarkdown(plan, sectionsContent);
      downloadBlob(blob, `${plan.project_name.replace(/\s+/g, "_").toLowerCase()}_docs.md`);
    } catch (e) {
      console.error(e);
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportHtml = async () => {
    if (!plan) return;
    setIsExporting(true);
    setShowMenu(false);
    try {
      const blob = await exportHtml(plan, sectionsContent);
      downloadBlob(blob, `${plan.project_name.replace(/\s+/g, "_").toLowerCase()}_docs.html`);
    } catch (e) {
      console.error(e);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="flex items-center gap-2 relative">
      {/* Copy button */}
      <button
        id="copy-docs-btn"
        onClick={handleCopy}
        disabled={!hasContent}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 text-xs text-white/50 hover:text-white/80 hover:border-white/20 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
      >
        {copied ? "✅ Copied!" : "📋 Copy"}
      </button>

      {/* Export dropdown */}
      <div className="relative">
        <button
          id="export-docs-btn"
          onClick={() => setShowMenu((p) => !p)}
          disabled={!hasContent || isExporting || !plan}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 text-white text-xs font-semibold
            hover:from-emerald-500 hover:to-teal-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-emerald-500/20"
        >
          {isExporting ? (
            <span className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            "⬇️"
          )}
          Export
          <svg className="w-3 h-3 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {showMenu && (
          <div className="absolute right-0 top-full mt-2 w-44 rounded-xl border border-white/10 bg-[#13131a] shadow-xl shadow-black/40 overflow-hidden z-50">
            <button
              id="export-markdown-btn"
              onClick={handleExportMd}
              className="w-full text-left px-4 py-3 text-sm text-white/70 hover:bg-white/5 hover:text-white transition-colors flex items-center gap-2"
            >
              <span>📝</span> Markdown (.md)
            </button>
            <button
              id="export-html-btn"
              onClick={handleExportHtml}
              className="w-full text-left px-4 py-3 text-sm text-white/70 hover:bg-white/5 hover:text-white transition-colors flex items-center gap-2 border-t border-white/5"
            >
              <span>🌐</span> HTML (.html)
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
