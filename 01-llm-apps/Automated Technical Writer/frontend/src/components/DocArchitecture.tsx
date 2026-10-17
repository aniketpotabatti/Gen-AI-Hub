"use client";

import { useState } from "react";
import type { DocPlan, DocSection } from "@/lib/api";

interface DocArchitectureProps {
  plan: DocPlan | null;
  generatingId: string | null;
  completedIds: Set<string>;
  onGenerateSection: (sectionId: string) => void;
  onGenerateAll: () => void;
  onUpdatePlan?: (updatedPlan: DocPlan) => void;
}

const STATUS_ICON: Record<string, string> = {
  pending: "○",
  generating: "◌",
  done: "✓",
  error: "✕",
};

const STATUS_COLOR: Record<string, string> = {
  pending: "text-white/30",
  generating: "text-violet-400 animate-pulse font-bold",
  done: "text-emerald-400 font-bold",
  error: "text-red-400",
};

function SectionRow({
  section,
  generatingId,
  completedIds,
  onGenerate,
  onDelete,
  depth = 0,
}: {
  section: DocSection;
  generatingId: string | null;
  completedIds: Set<string>;
  onGenerate: (id: string) => void;
  onDelete?: (id: string) => void;
  depth?: number;
}) {
  const [expanded, setExpanded] = useState(true);
  const isGenerating = generatingId === section.id;
  const isDone = completedIds.has(section.id);
  const status = isGenerating ? "generating" : isDone ? "done" : "pending";

  return (
    <div className={depth > 0 ? "ml-4 border-l border-white/5 pl-3" : ""}>
      <div
        className={`group flex items-center gap-2.5 py-2 px-3 rounded-xl transition-all cursor-default ${
          isGenerating
            ? "bg-violet-500/15 border border-violet-500/30 shadow-sm shadow-violet-500/10"
            : isDone
            ? "bg-emerald-500/5 border border-emerald-500/15"
            : "hover:bg-white/[0.03] border border-transparent"
        }`}
      >
        {/* Expand toggle */}
        {section.subsections && section.subsections.length > 0 && (
          <button
            onClick={() => setExpanded((p) => !p)}
            className="text-white/30 hover:text-white/70 transition-colors text-xs w-3"
          >
            {expanded ? "▾" : "▸"}
          </button>
        )}

        {/* Status icon */}
        <span className={`font-mono text-xs w-4 flex items-center justify-center ${STATUS_COLOR[status]}`}>
          {STATUS_ICON[status]}
        </span>

        {/* Title & Description */}
        <div className="flex-1 min-w-0">
          <div className={`text-xs font-medium truncate ${isDone ? "text-white/80" : "text-white/70"}`}>
            {section.title}
          </div>
        </div>

        {/* Word count estimate */}
        <span className="text-[10px] text-white/30 font-mono">
          ~{section.estimated_words}w
        </span>

        {/* Action button */}
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          {!isDone && !isGenerating && (
            <button
              id={`generate-section-${section.id}`}
              onClick={() => onGenerate(section.id)}
              className="text-[11px] px-2 py-0.5 rounded-md bg-violet-600/30 text-violet-200 hover:bg-violet-600/50 transition-all border border-violet-500/30 font-medium"
            >
              Write
            </button>
          )}

          {onDelete && !isGenerating && (
            <button
              onClick={() => onDelete(section.id)}
              className="text-[11px] px-1.5 py-0.5 rounded-md text-white/30 hover:text-red-400 hover:bg-red-500/10 transition-colors"
              title="Delete section"
            >
              ✕
            </button>
          )}
        </div>

        {isGenerating && (
          <span className="text-[11px] text-violet-400 font-mono animate-pulse">writing...</span>
        )}
      </div>

      {expanded && section.subsections && section.subsections.length > 0 && (
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
  onUpdatePlan,
}: DocArchitectureProps) {
  const [newTitle, setNewTitle] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);

  if (!plan) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-center p-6">
        <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center text-2xl">
          🗺️
        </div>
        <div>
          <p className="text-white/60 text-xs font-medium">Architecture Plan Empty</p>
          <p className="text-white/30 text-[11px] mt-1 max-w-[200px]">
            Input your source code and click &ldquo;Parse AST & Plan Docs&rdquo;
          </p>
        </div>
      </div>
    );
  }

  const doneCount = completedIds.size;
  const totalCount = plan.sections.length;
  const progress = totalCount > 0 ? (doneCount / totalCount) * 100 : 0;

  const handleDeleteSection = (id: string) => {
    if (!onUpdatePlan) return;
    const updatedSections = plan.sections.filter((s) => s.id !== id);
    onUpdatePlan({ ...plan, sections: updatedSections });
  };

  const handleAddSection = () => {
    if (!newTitle.trim() || !onUpdatePlan) return;
    const id = newTitle.toLowerCase().replace(/\s+/g, "_") + "_" + Math.floor(Math.random() * 1000);
    const newSec: DocSection = {
      id,
      title: newTitle.trim(),
      description: `Comprehensive details for ${newTitle.trim()}`,
      estimated_words: 250,
      subsections: [],
      status: "pending",
    };
    onUpdatePlan({ ...plan, sections: [...plan.sections, newSec] });
    setNewTitle("");
    setShowAddForm(false);
  };

  return (
    <div className="flex flex-col gap-3.5 h-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-semibold text-white/80 uppercase tracking-wider font-mono">
            02 — Architecture Plan
          </h2>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-300 font-mono">
            {doneCount}/{totalCount}
          </span>
        </div>

        {onUpdatePlan && (
          <button
            type="button"
            onClick={() => setShowAddForm((p) => !p)}
            className="text-[11px] px-2 py-0.5 rounded-md bg-white/[0.04] hover:bg-violet-500/20 text-white/60 hover:text-violet-300 border border-white/5 transition-all"
          >
            {showAddForm ? "Cancel" : "+ Custom Section"}
          </button>
        )}
      </div>

      {/* Project Meta Card */}
      <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.07]">
        <div className="flex items-center gap-2 mb-1.5">
          <span className="text-[10px] px-2 py-0.5 rounded-md bg-cyan-500/20 text-cyan-300 border border-cyan-500/20 font-mono uppercase font-semibold">
            {plan.project_type}
          </span>
          <span className="text-xs font-semibold text-white/90 truncate">{plan.project_name}</span>
        </div>
        <p className="text-[11px] text-white/40 leading-relaxed line-clamp-2">{plan.reasoning}</p>
      </div>

      {/* Progress Bar */}
      {totalCount > 0 && (
        <div className="h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-violet-500 to-cyan-400 rounded-full transition-all duration-500 shadow-sm shadow-violet-500/50"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Add Custom Section Inline Form */}
      {showAddForm && (
        <div className="p-2.5 rounded-xl border border-violet-500/30 bg-violet-500/10 space-y-2 animate-fade-in">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Section Title (e.g. Configuration & Environment)"
            className="w-full bg-[#12121d] border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder:text-white/30 focus:border-violet-500 outline-none"
          />
          <div className="flex justify-end gap-1.5">
            <button
              onClick={() => setShowAddForm(false)}
              className="px-2.5 py-1 text-[11px] text-white/50 hover:text-white"
            >
              Cancel
            </button>
            <button
              onClick={handleAddSection}
              className="px-3 py-1 bg-violet-600 text-white rounded-md text-[11px] font-semibold hover:bg-violet-500"
            >
              Add Section
            </button>
          </div>
        </div>
      )}

      {/* Sections List */}
      <div className="flex-1 overflow-y-auto space-y-1 pr-1 scrollbar-thin">
        {plan.sections.map((section) => (
          <SectionRow
            key={section.id}
            section={section}
            generatingId={generatingId}
            completedIds={completedIds}
            onGenerate={onGenerateSection}
            onDelete={onUpdatePlan ? handleDeleteSection : undefined}
          />
        ))}
      </div>

      {/* Generate All Sections CTA */}
      <button
        id="generate-all-btn"
        onClick={onGenerateAll}
        disabled={!!generatingId || (doneCount === totalCount && totalCount > 0)}
        className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-600 text-white text-xs font-semibold
          hover:from-violet-500 hover:to-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-violet-500/20
          hover:shadow-violet-500/40 hover:-translate-y-0.5 disabled:hover:translate-y-0"
      >
        {generatingId ? (
          <>
            <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            <span>Streaming Sections...</span>
          </>
        ) : doneCount === totalCount && totalCount > 0 ? (
          "✓ All Sections Generated!"
        ) : (
          "⚡ Generate All Sections"
        )}
      </button>
    </div>
  );
}
