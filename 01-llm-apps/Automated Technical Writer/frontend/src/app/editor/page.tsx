"use client";

import { useState, useCallback } from "react";
import CodeUploader from "@/components/CodeUploader";
import DocArchitecture from "@/components/DocArchitecture";
import StreamingOutput from "@/components/StreamingOutput";
import ExportButton from "@/components/ExportButton";
import type { CodeContext, DocPlan, DocSection } from "@/lib/api";
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

  const handleCodeReady = useCallback(async (code: string, filename: string) => {
    setErrorMsg(null);
    setStage("parsing");

    try {
      const parseResult = await parseCode(code, filename);
      if (!parseResult.success || !parseResult.code_context) {
        throw new Error(parseResult.error || "Failed to parse code");
      }
      setCodeContext(parseResult.code_context);

      setStage("planning");
      const planResult = await planDoc(parseResult.code_context);
      if (!planResult.success || !planResult.doc_plan) {
        throw new Error(planResult.error || "Failed to plan documentation");
      }
      setDocPlan(planResult.doc_plan);
      setStage("ready");
    } catch (err) {
      setErrorMsg(String(err));
      setStage("idle");
    }
  }, []);

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
        }
      );
    },
    [codeContext, docPlan, generatingId, sectionsContent]
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
          }
        );
      });

      await runNext(rest);
    };

    await runNext(pendingSections);
  }, [codeContext, docPlan, generatingId, completedIds, sectionsContent]);

  const isStreaming = stage === "writing";

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0a0f]">
      {/* Top bar */}
      <div className="mt-16 border-b border-white/[0.06] bg-[#0d0d14]">
        <div className="max-w-[1600px] mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-sm font-medium text-white/60">Documentation Editor</h1>
            {codeContext && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-white/40 font-mono">
                {codeContext.filename}
              </span>
            )}
            {stage === "parsing" && (
              <span className="text-xs text-violet-400 flex items-center gap-1.5">
                <span className="w-3 h-3 border border-violet-400 border-t-transparent rounded-full animate-spin" />
                Parsing code...
              </span>
            )}
            {stage === "planning" && (
              <span className="text-xs text-cyan-400 flex items-center gap-1.5">
                <span className="w-3 h-3 border border-cyan-400 border-t-transparent rounded-full animate-spin" />
                Planning documentation...
              </span>
            )}
          </div>

          <ExportButton
            plan={docPlan}
            sectionsContent={sectionsContent}
            fullContent={outputContent}
          />
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
          <div className="glass-panel p-5 flex flex-col overflow-hidden">
            <CodeUploader
              onCodeReady={handleCodeReady}
              isLoading={stage === "parsing" || stage === "planning"}
            />
          </div>

          {/* Panel 2: Doc Architecture */}
          <div className="glass-panel p-5 flex flex-col overflow-hidden">
            <DocArchitecture
              plan={docPlan}
              generatingId={generatingId}
              completedIds={completedIds}
              onGenerateSection={handleGenerateSection}
              onGenerateAll={handleGenerateAll}
            />
          </div>

          {/* Panel 3: Streaming Output */}
          <div className="glass-panel p-5 flex flex-col overflow-hidden">
            <StreamingOutput
              content={outputContent}
              isStreaming={isStreaming}
              currentSection={currentSectionTitle}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
