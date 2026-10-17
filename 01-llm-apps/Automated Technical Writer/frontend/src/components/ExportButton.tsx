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
      {/* Export dropdown */}
      <div className="relative">
        <button
          id="export-docs-btn"
          onClick={() => setShowMenu((p) => !p)}
          disabled={!hasContent || isExporting || !plan}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 text-white text-xs font-semibold
            hover:from-emerald-500 hover:to-teal-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md shadow-emerald-500/20 active:translate-y-0"
        >
          {isExporting ? (
            <span className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          )}
          <span>Export</span>
          <svg className="w-3 h-3 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {showMenu && (
          <div className="absolute right-0 top-full mt-2 w-48 rounded-xl border border-white/10 bg-[#12121d] shadow-2xl shadow-black/60 overflow-hidden z-50 animate-fade-in">
            <button
              id="export-markdown-btn"
              onClick={handleExportMd}
              className="w-full text-left px-3.5 py-2.5 text-xs text-white/80 hover:bg-white/5 hover:text-white transition-colors flex items-center gap-2"
            >
              <span>📝</span>
              <div>
                <div className="font-medium text-white">Markdown File</div>
                <div className="text-[10px] text-white/40">Clean GitHub-flavored (.md)</div>
              </div>
            </button>
            <button
              id="export-html-btn"
              onClick={handleExportHtml}
              className="w-full text-left px-3.5 py-2.5 text-xs text-white/80 hover:bg-white/5 hover:text-white transition-colors flex items-center gap-2 border-t border-white/[0.06]"
            >
              <span>🌐</span>
              <div>
                <div className="font-medium text-white">Styled HTML</div>
                <div className="text-[10px] text-white/40">Standalone dark mode (.html)</div>
              </div>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
