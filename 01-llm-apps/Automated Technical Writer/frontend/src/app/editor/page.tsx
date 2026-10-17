"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import Link from "next/link";
import CodeUploader from "@/components/CodeUploader";
import DocArchitecture from "@/components/DocArchitecture";
import StreamingOutput from "@/components/StreamingOutput";
import ExportButton from "@/components/ExportButton";
import SettingsModal from "@/components/SettingsModal";
import type { CodeContext, DocPlan, DocSection, LLMConfig } from "@/lib/api";
import { parseCode, planDoc, writeSection } from "@/lib/api";

type Stage = "idle" | "parsing" | "planning" | "ready" | "writing";

export default function EditorPage() {
  const [stage, setStage] = useState<Stage>("idle");
  const [codeContext, setCodeContext] = useState<CodeContext | null>(null);
  const [docPlan, setDocPlan] = useState<DocPlan | null>(null);
  const [outputContent, setOutputContent] = useState("");
  const [sectionsContent, setSectionsContent] = useState<Record<string, string>>({});
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const [completedIds, setCompletedIds] = useState<Set<string>>(new Set());
  const [currentSectionTitle, setCurrentSectionTitle] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Settings & Functionalities modal state
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [llmConfig, setLlmConfig] = useState<LLMConfig>({
    provider: "gemini",
    model: "gemini-2.5-flash",
    tone: "balanced",
    audience: "intermediate",
  });

  // Load saved config on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("autowriter_llm_config");
      if (saved) {
        setLlmConfig(JSON.parse(saved));
      }
    } catch (e) {
      console.error("Failed to load llm config from local storage", e);
    }
  }, []);

  const handleSaveConfig = (newConfig: LLMConfig) => {
    setLlmConfig(newConfig);
    try {
      localStorage.setItem("autowriter_llm_config", JSON.stringify(newConfig));
    } catch (e) {
      console.error("Failed to save llm config to local storage", e);
    }
  };

  const handleCodeReady = useCallback(
    async (code: string, filename: string, files?: { filename: string; code: string }[]) => {
      setErrorMsg(null);
      setStage("parsing");

      try {
        const parseResult = await parseCode(code, filename, files);
        if (!parseResult.success || !parseResult.code_context) {
          throw new Error(parseResult.error || "Failed to parse code");
        }
        setCodeContext(parseResult.code_context);

        setStage("planning");
        const planResult = await planDoc(parseResult.code_context, llmConfig);
        if (!planResult.success || !planResult.doc_plan) {
          throw new Error(planResult.error || "Failed to plan documentation");
        }
        setDocPlan(planResult.doc_plan);
        setStage("ready");
      } catch (err) {
        setErrorMsg(String(err));
        setStage("idle");
      }
    },
    [llmConfig]
  );

  const handleGenerateSection = useCallback(
    (sectionId: string) => {
      if (!codeContext || !docPlan || generatingId) return;

      const section = docPlan.sections.find((s) => s.id === sectionId);
      if (!section) return;

      setGeneratingId(sectionId);
      setCurrentSectionTitle(section.title);
      setStage("writing");

      let sectionBuffer = "";

      writeSection(
        codeContext,
        docPlan,
        sectionId,
        (chunk) => {
          sectionBuffer += chunk;
          setSectionsContent((prev) => ({
            ...prev,
            [sectionId]: sectionBuffer,
          }));
          // Build combined output in section order
          setOutputContent(() => {
            const allContent = { ...sectionsContent, [sectionId]: sectionBuffer };
            return docPlan.sections
              .map((s) => allContent[s.id] || "")
              .filter(Boolean)
              .join("\n\n---\n\n");
          });
        },
        () => {
          setCompletedIds((prev) => new Set([...prev, sectionId]));
          setGeneratingId(null);
          setCurrentSectionTitle("");
          setStage("ready");
        },
        (error) => {
          setErrorMsg(`Error writing section "${section.title}": ${error}`);
          setGeneratingId(null);
          setStage("ready");
        },
        llmConfig
      );
    },
    [codeContext, docPlan, generatingId, sectionsContent, llmConfig]
  );

  const handleGenerateAll = useCallback(async () => {
    if (!codeContext || !docPlan || generatingId) return;

    // Generate sections sequentially
    const pendingSections = docPlan.sections.filter((s) => !completedIds.has(s.id));

    const runNext = async (sections: DocSection[]) => {
      if (sections.length === 0) return;
      const [current, ...rest] = sections;

      setGeneratingId(current.id);
      setCurrentSectionTitle(current.title);
      setStage("writing");

      let sectionBuffer = "";
      await new Promise<void>((resolve) => {
        writeSection(
          codeContext,
          docPlan,
          current.id,
          (chunk) => {
            sectionBuffer += chunk;
            setSectionsContent((prev) => ({
              ...prev,
              [current.id]: sectionBuffer,
            }));
            setOutputContent(() => {
              const allContent = { ...sectionsContent, [current.id]: sectionBuffer };
              return docPlan.sections
                .map((s) => allContent[s.id] || "")
                .filter(Boolean)
                .join("\n\n---\n\n");
            });
          },
          () => {
            setCompletedIds((prev) => new Set([...prev, current.id]));
            setGeneratingId(null);
            setStage("ready");
            resolve();
          },
          (error) => {
            setErrorMsg(`Error writing "${current.title}": ${error}`);
            setGeneratingId(null);
            setStage("ready");
            resolve();
          },
          llmConfig
        );
      });

      await runNext(rest);
    };

    await runNext(pendingSections);
  }, [codeContext, docPlan, generatingId, completedIds, sectionsContent, llmConfig]);

  // Resizable split panel state (percentages for left, middle, right)
  const [panelWidths, setPanelWidths] = useState<[number, number, number]>([38, 24, 38]);
  const [maximizedPanel, setMaximizedPanel] = useState<"code" | "arch" | "doc" | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const draggingDivider = useRef<1 | 2 | null>(null);

  // Load saved panel widths from localStorage
  useEffect(() => {
    try {
      const savedWidths = localStorage.getItem("autowriter_panel_widths");
      if (savedWidths) {
        const parsed = JSON.parse(savedWidths);
        if (Array.isArray(parsed) && parsed.length === 3) {
          setPanelWidths([parsed[0], parsed[1], parsed[2]]);
        }
      }
    } catch (e) {
      console.error("Failed to load panel widths", e);
    }
  }, []);

  const handleResetLayout = () => {
    setMaximizedPanel(null);
    const defaultWidths: [number, number, number] = [38, 24, 38];
    setPanelWidths(defaultWidths);
    try {
      localStorage.setItem("autowriter_panel_widths", JSON.stringify(defaultWidths));
    } catch (e) {
      console.error(e);
    }
  };

  const startDragging = (divider: 1 | 2) => (e: React.MouseEvent) => {
    e.preventDefault();
    draggingDivider.current = divider;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMouseMove = (moveEvent: MouseEvent) => {
      if (!containerRef.current || !draggingDivider.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const totalWidth = rect.width;
      if (totalWidth <= 0) return;

      const currentX = moveEvent.clientX - rect.left;
      const currentPct = (currentX / totalWidth) * 100;

      if (draggingDivider.current === 1) {
        // Divider between Code (P1) and Arch (P2)
        // Clamp P1 between 15% and 60%
        const minP1 = 15;
        const maxP1 = 60;
        const newP1 = Math.min(Math.max(currentPct, minP1), maxP1);

        // Adjust P2 while keeping P3 unchanged
        const currentP3 = panelWidths[2];
        const newP2 = Math.max(100 - newP1 - currentP3, 12);
        const actualP3 = 100 - newP1 - newP2;

        setPanelWidths([
          parseFloat(newP1.toFixed(1)),
          parseFloat(newP2.toFixed(1)),
          parseFloat(actualP3.toFixed(1)),
        ]);
      } else if (draggingDivider.current === 2) {
        // Divider between Arch (P2) and Docs (P3)
        // currentPct is the position of divider 2 from left
        const currentP1 = panelWidths[0];
        const minP2 = 12;
        const minP3 = 18;

        const availableFromP1 = currentPct - currentP1;
        const newP2 = Math.min(Math.max(availableFromP1, minP2), 65);
        const newP3 = Math.max(100 - currentP1 - newP2, minP3);
        const actualP2 = 100 - currentP1 - newP3;

        setPanelWidths([
          parseFloat(currentP1.toFixed(1)),
          parseFloat(actualP2.toFixed(1)),
          parseFloat(newP3.toFixed(1)),
        ]);
      }
    };

    const onMouseUp = () => {
      draggingDivider.current = null;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);

      setPanelWidths((current) => {
        try {
          localStorage.setItem("autowriter_panel_widths", JSON.stringify(current));
        } catch (e) {
          console.error(e);
        }
        return current;
      });
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
  };

  const isStreaming = stage === "writing";

  return (
    <div className="min-h-screen flex flex-col bg-[#08080d]">
      {/* Top bar */}
      <div className="mt-16 border-b border-white/[0.08] bg-[#0c0c14]/95 backdrop-blur-md">
        <div className="max-w-[1720px] mx-auto px-6 py-2.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-xs text-white/40 hover:text-violet-300 transition-colors flex items-center gap-1"
            >
              <span>←</span>
              <span>Home</span>
            </Link>
            <span className="text-white/20 text-xs">/</span>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-violet-400" />
              <span className="text-xs font-semibold text-white/90 font-mono">
                {codeContext ? codeContext.filename : "workspace"}
              </span>
            </div>

            {/* Pipeline Stage Badge */}
            {stage === "parsing" && (
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-violet-500/10 border border-violet-500/30 text-violet-300 flex items-center gap-1.5 font-mono">
                <span className="w-2 h-2 border border-violet-400 border-t-transparent rounded-full animate-spin" />
                Parsing AST...
              </span>
            )}
            {stage === "planning" && (
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 flex items-center gap-1.5 font-mono">
                <span className="w-2 h-2 border border-cyan-400 border-t-transparent rounded-full animate-spin" />
                Planning Architecture...
              </span>
            )}
            {stage === "writing" && (
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 flex items-center gap-1.5 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                Streaming Section...
              </span>
            )}
            {stage === "ready" && (
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-mono flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                Studio Ready
              </span>
            )}

            {/* Active Model Pill */}
            <span
              onClick={() => setIsSettingsOpen(true)}
              className="hidden sm:inline-flex items-center gap-1.5 text-[10px] px-2 py-0.5 rounded-md bg-white/[0.03] border border-white/10 text-white/50 hover:border-violet-500/30 hover:text-white/80 transition-colors font-mono cursor-pointer"
              title="Click to configure Model & API Key in Settings"
            >
              <span className="text-violet-400">⚡</span>
              {llmConfig.model}
            </span>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Split layout quick reset / preset button */}
            {(maximizedPanel || panelWidths[0] !== 38 || panelWidths[1] !== 24 || panelWidths[2] !== 38) && (
              <button
                type="button"
                onClick={handleResetLayout}
                className="text-[11px] px-2.5 py-1 rounded-lg border border-white/10 bg-white/[0.03] hover:bg-white/[0.08] hover:text-white text-white/60 transition-all font-mono flex items-center gap-1.5"
                title="Reset panels to default 3-column split view"
              >
                <span>↺</span>
                <span>Reset View</span>
              </button>
            )}

            <ExportButton
              plan={docPlan}
              sectionsContent={sectionsContent}
              fullContent={outputContent}
            />

            {/* Top-Right Settings & Functionalities Button (Icon-Only) */}
            <button
              id="editor-settings-btn"
              onClick={() => setIsSettingsOpen(true)}
              title="Settings & API Keys"
              aria-label="Settings & API Keys"
              className="relative flex items-center justify-center w-8 h-8 rounded-lg border border-white/10 bg-white/[0.03] text-white/70 hover:text-white hover:border-violet-500/50 hover:bg-violet-500/15 transition-all shadow-sm group"
            >
              <svg
                className="w-4 h-4 text-white/60 group-hover:text-violet-300 transition-colors"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
                />
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>

              {/* Status indicator dot */}
              <span
                className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full ${
                  llmConfig.apiKey
                    ? "bg-emerald-400 shadow-sm shadow-emerald-400 animate-pulse"
                    : "bg-violet-400/80"
                }`}
                title={llmConfig.apiKey ? "Custom API Key active" : "Using server environment"}
              />
            </button>
          </div>
        </div>
      </div>

      {/* Error banner */}
      {errorMsg && (
        <div className="max-w-[1720px] mx-auto px-6 pt-4 w-full">
          <div className="flex items-center gap-3 p-4 rounded-xl border border-red-500/20 bg-red-500/10 text-red-300 text-sm">
            <span>⚠️</span>
            <span className="flex-1">{errorMsg}</span>
            <button
              onClick={() => setErrorMsg(null)}
              className="text-red-400/60 hover:text-red-300"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* 3-panel Resizable Studio Container */}
      <div className="flex-1 max-w-[1720px] mx-auto w-full px-4 sm:px-6 py-4 flex flex-col min-h-0">
        <div
          ref={containerRef}
          className="relative flex-1 flex flex-col lg:flex-row gap-0 h-[calc(100vh-140px)] min-h-[550px] w-full"
        >
          {/* Panel 1: Code Uploader */}
          <div
            style={{
              flex: maximizedPanel === "code" ? "1 1 100%" : maximizedPanel ? "0 0 0%" : `0 0 ${panelWidths[0]}%`,
              display: maximizedPanel && maximizedPanel !== "code" ? "none" : "flex",
            }}
            className="glass-panel p-4 flex-col overflow-hidden min-w-[280px] transition-[flex] duration-150 relative"
          >
            <CodeUploader
              onCodeReady={handleCodeReady}
              isLoading={stage === "parsing" || stage === "planning"}
              codeContext={codeContext}
              isMaximized={maximizedPanel === "code"}
              onToggleMaximize={() => setMaximizedPanel(maximizedPanel === "code" ? null : "code")}
            />
          </div>

          {/* Divider Handle 1 (Between Panel 1 and Panel 2) */}
          {!maximizedPanel && (
            <div
              onMouseDown={startDragging(1)}
              className="hidden lg:flex w-2.5 hover:w-2.5 -mx-1 z-20 cursor-col-resize group items-center justify-center transition-all select-none"
              title="Drag to resize panels"
            >
              <div className="w-[1.5px] h-12 bg-white/10 group-hover:bg-violet-400 group-hover:h-24 group-hover:w-[2px] transition-all rounded-full flex flex-col items-center justify-center gap-1 shadow-sm">
                <span className="w-1 h-1 rounded-full bg-white/40 group-hover:bg-violet-300 inline-block" />
                <span className="w-1 h-1 rounded-full bg-white/40 group-hover:bg-violet-300 inline-block" />
              </div>
            </div>
          )}

          {/* Panel 2: Doc Architecture */}
          <div
            style={{
              flex: maximizedPanel === "arch" ? "1 1 100%" : maximizedPanel ? "0 0 0%" : `0 0 ${panelWidths[1]}%`,
              display: maximizedPanel && maximizedPanel !== "arch" ? "none" : "flex",
            }}
            className="glass-panel p-4 flex-col overflow-hidden min-w-[220px] transition-[flex] duration-150 relative"
          >
            <DocArchitecture
              plan={docPlan}
              generatingId={generatingId}
              completedIds={completedIds}
              onGenerateSection={handleGenerateSection}
              onGenerateAll={handleGenerateAll}
              onUpdatePlan={(updated) => setDocPlan(updated)}
              isMaximized={maximizedPanel === "arch"}
              onToggleMaximize={() => setMaximizedPanel(maximizedPanel === "arch" ? null : "arch")}
            />
          </div>

          {/* Divider Handle 2 (Between Panel 2 and Panel 3) */}
          {!maximizedPanel && (
            <div
              onMouseDown={startDragging(2)}
              className="hidden lg:flex w-2.5 hover:w-2.5 -mx-1 z-20 cursor-col-resize group items-center justify-center transition-all select-none"
              title="Drag to resize panels"
            >
              <div className="w-[1.5px] h-12 bg-white/10 group-hover:bg-violet-400 group-hover:h-24 group-hover:w-[2px] transition-all rounded-full flex flex-col items-center justify-center gap-1 shadow-sm">
                <span className="w-1 h-1 rounded-full bg-white/40 group-hover:bg-violet-300 inline-block" />
                <span className="w-1 h-1 rounded-full bg-white/40 group-hover:bg-violet-300 inline-block" />
              </div>
            </div>
          )}

          {/* Panel 3: Streaming Output */}
          <div
            style={{
              flex: maximizedPanel === "doc" ? "1 1 100%" : maximizedPanel ? "0 0 0%" : `0 0 ${panelWidths[2]}%`,
              display: maximizedPanel && maximizedPanel !== "doc" ? "none" : "flex",
            }}
            className="glass-panel p-4 flex-col overflow-hidden min-w-[280px] transition-[flex] duration-150 relative"
          >
            <StreamingOutput
              content={outputContent}
              isStreaming={isStreaming}
              currentSection={currentSectionTitle}
              isMaximized={maximizedPanel === "doc"}
              onToggleMaximize={() => setMaximizedPanel(maximizedPanel === "doc" ? null : "doc")}
            />
          </div>
        </div>
      </div>

      {/* Settings & Functionalities Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        config={llmConfig}
        onSave={handleSaveConfig}
      />
    </div>
  );
}
