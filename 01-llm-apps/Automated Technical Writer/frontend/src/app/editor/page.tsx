"use client";

import { useState, useCallback, useEffect } from "react";
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

  const isStreaming = stage === "writing";

  return (
    <div className="min-h-screen flex flex-col bg-[#08080d]">
      {/* Top bar */}
      <div className="mt-16 border-b border-white/[0.06] bg-[#0c0c14]/90 backdrop-blur-md">
        <div className="max-w-[1600px] mx-auto px-6 py-2.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xs text-white/40 hover:text-white/60 transition-colors cursor-pointer">
              Workspace
            </span>
            <span className="text-white/20 text-xs">/</span>
            <span className="text-xs font-semibold text-white/90 font-mono">
              {codeContext ? codeContext.filename : "draft_project"}
            </span>

            {/* Pipeline Stage Badge */}
            {stage === "parsing" && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-violet-500/10 border border-violet-500/30 text-violet-300 flex items-center gap-1.5 font-mono">
                <span className="w-2 h-2 border border-violet-400 border-t-transparent rounded-full animate-spin" />
                Parsing AST...
              </span>
            )}
            {stage === "planning" && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 flex items-center gap-1.5 font-mono">
                <span className="w-2 h-2 border border-cyan-400 border-t-transparent rounded-full animate-spin" />
                Planning Architecture...
              </span>
            )}
            {stage === "writing" && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 flex items-center gap-1.5 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                Streaming SSE...
              </span>
            )}
            {stage === "ready" && (
              <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 font-mono">
                ● Studio Ready
              </span>
            )}
          </div>

          <div className="flex items-center gap-2.5">
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
        <div className="max-w-[1600px] mx-auto px-6 pt-4 w-full">
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

      {/* 3-panel editor */}
      <div className="flex-1 max-w-[1600px] mx-auto w-full px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px_1fr] gap-4 h-[calc(100vh-160px)]">

          {/* Panel 1: Code Uploader */}
          <div className="glass-panel p-4 flex flex-col overflow-hidden">
            <CodeUploader
              onCodeReady={handleCodeReady}
              isLoading={stage === "parsing" || stage === "planning"}
              codeContext={codeContext}
            />
          </div>

          {/* Panel 2: Doc Architecture */}
          <div className="glass-panel p-4 flex flex-col overflow-hidden">
            <DocArchitecture
              plan={docPlan}
              generatingId={generatingId}
              completedIds={completedIds}
              onGenerateSection={handleGenerateSection}
              onGenerateAll={handleGenerateAll}
              onUpdatePlan={(updated) => setDocPlan(updated)}
            />
          </div>

          {/* Panel 3: Streaming Output */}
          <div className="glass-panel p-4 flex flex-col overflow-hidden">
            <StreamingOutput
              content={outputContent}
              isStreaming={isStreaming}
              currentSection={currentSectionTitle}
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
