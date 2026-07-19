"use client";

import { useState } from "react";
import type { DocPlan, DocSection } from "@/lib/api";

interface DocArchitectureProps {
  plan: DocPlan | null;
  generatingId: string | null;
  completedIds: Set<string>;
  onGenerateSection: (sectionId: string) => void;
  onGenerateAll: () => void;
}

const STATUS_ICON: Record<string, string> = {
  pending: "○",
  generating: "◌",
  done: "✓",
  error: "✕",
};

const STATUS_COLOR: Record<string, string> = {
  pending: "text-white/30",
  generating: "text-violet-400 animate-pulse",
  done: "text-emerald-400",
  error: "text-red-400",
};

function SectionRow({
  section,
  generatingId,
  completedIds,
  onGenerate,
  depth = 0,
}: {
  section: DocSection;
  generatingId: string | null;
  completedIds: Set<string>;
  onGenerate: (id: string) => void;
  depth?: number;
}) {
  const [expanded, setExpanded] = useState(true);
  const isGenerating = generatingId === section.id;
  const isDone = completedIds.has(section.id);
  const status = isGenerating ? "generating" : isDone ? "done" : "pending";

  return (
    <div className={depth > 0 ? "ml-4 border-l border-white/5 pl-3" : ""}>
      <div
        className={`group flex items-center gap-3 py-2 px-3 rounded-lg transition-all cursor-default ${
          isGenerating
            ? "bg-violet-500/10 border border-violet-500/20"
            : isDone
            ? "bg-emerald-500/5 border border-emerald-500/10"
            : "hover:bg-white/[0.03] border border-transparent"
        }`}
      >
        {/* Expand toggle */}
        {section.subsections.length > 0 && (
          <button
            onClick={() => setExpanded((p) => !p)}
            className="text-white/20 hover:text-white/50 transition-colors text-xs w-4"
          >
            {expanded ? "▾" : "▸"}
          </button>
        )}

        {/* Status icon */}
        <span className={`font-mono text-xs w-4 ${STATUS_COLOR[status]}`}>
          {STATUS_ICON[status]}
        </span>

        {/* Title */}
        <span className={`flex-1 text-sm ${isDone ? "text-white/70" : "text-white/60"}`}>
          {section.title}
        </span>

        {/* Word count */}
        <span className="text-xs text-white/20 font-mono mr-2">
          ~{section.estimated_words}w
        </span>

        {/* Generate button */}
        {!isDone && !isGenerating && (
          <button
            id={`generate-section-${section.id}`}
            onClick={() => onGenerate(section.id)}
            className="opacity-0 group-hover:opacity-100 text-xs px-2.5 py-1 rounded-md bg-violet-500/20 text-violet-300 hover:bg-violet-500/30 transition-all border border-violet-500/20"
          >
            Write
          </button>
        )}

        {isGenerating && (
          <span className="text-xs text-violet-400 font-mono animate-pulse">writing...</span>
        )}
      </div>

      {expanded && section.subsections.length > 0 && (
        <div className="mt-1">
          {section.subsections.map((sub) => (
            <SectionRow
              key={sub.id}
              section={sub}
              generatingId={generatingId}
              completedIds={completedIds}
              onGenerate={onGenerate}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DocArchitecture({
  plan,
  generatingId,
  completedIds,
  onGenerateSection,
  onGenerateAll,
}: DocArchitectureProps) {
  if (!plan) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
        <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-3xl">
          🗺️
        </div>
        <div>
          <p className="text-white/40 text-sm">Doc architecture will appear here</p>
          <p className="text-white/20 text-xs mt-1">Parse your code first</p>
        </div>
      </div>
    );
  }

  const doneCount = completedIds.size;
  const totalCount = plan.sections.length;
  const progress = totalCount > 0 ? (doneCount / totalCount) * 100 : 0;

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white/70 uppercase tracking-wider">
          02 — Doc Architecture
        </h2>
        <span className="text-xs text-white/30 font-mono">
          {doneCount}/{totalCount} sections
        </span>
      </div>

      {/* Project summary */}
      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.07]">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 border border-violet-500/20 font-mono uppercase">
            {plan.project_type}
          </span>
          <span className="text-sm font-medium text-white/80">{plan.project_name}</span>
        </div>
        <p className="text-xs text-white/40 leading-relaxed">{plan.reasoning}</p>
      </div>

      {/* Progress bar */}
      {doneCount > 0 && (
        <div className="h-1 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-violet-500 to-cyan-500 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Sections list */}
      <div className="flex-1 overflow-y-auto space-y-0.5 pr-1 scrollbar-thin">
        {plan.sections.map((section) => (
          <SectionRow
            key={section.id}
            section={section}
            generatingId={generatingId}
            completedIds={completedIds}
            onGenerate={onGenerateSection}
          />
        ))}
      </div>

      {/* Generate All button */}
      <button
        id="generate-all-btn"
        onClick={onGenerateAll}
        disabled={!!generatingId || doneCount === totalCount}
        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-600 text-white text-sm font-semibold
          hover:from-violet-500 hover:to-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-violet-500/20
          hover:shadow-violet-500/40 hover:-translate-y-0.5 disabled:hover:translate-y-0"
      >
        {generatingId ? (
          <>
            <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            Writing sections...
          </>
        ) : doneCount === totalCount && totalCount > 0 ? (
          "✅ All sections complete!"
        ) : (
          "⚡ Generate All Sections"
        )}
      </button>
    </div>
  );
}
