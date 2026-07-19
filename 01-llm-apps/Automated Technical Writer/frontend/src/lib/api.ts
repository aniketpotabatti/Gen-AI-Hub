/**
 * API client for the Automated Technical Writer backend.
 * Handles parse, plan, and streaming write requests.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface FunctionInfo {
  name: string;
  params: string[];
  return_type?: string;
  docstring?: string;
  start_line: number;
  end_line: number;
}

export interface ClassInfo {
  name: string;
  methods: FunctionInfo[];
  docstring?: string;
  base_classes: string[];
}

export interface CodeContext {
  language: string;
  filename: string;
  raw_code: string;
  functions: FunctionInfo[];
  classes: ClassInfo[];
  imports: string[];
  module_docstring?: string;
  total_lines: number;
}

export interface DocSection {
  id: string;
  title: string;
  description: string;
  estimated_words: number;
  subsections: DocSection[];
  status: "pending" | "generating" | "done" | "error";
}

export interface DocPlan {
  project_type: string;
  project_name: string;
  sections: DocSection[];
  reasoning: string;
}

// ── API Calls ─────────────────────────────────────────────────────────────────

export async function parseCode(
  code: string,
  filename: string
): Promise<{ success: boolean; code_context?: CodeContext; error?: string }> {
  const res = await fetch(`${API_BASE}/api/generate/parse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code, filename }),
  });
  if (!res.ok) throw new Error(`Parse failed: ${res.statusText}`);
  return res.json();
}

export async function planDoc(
  code_context: CodeContext
): Promise<{ success: boolean; doc_plan?: DocPlan; error?: string }> {
  const res = await fetch(`${API_BASE}/api/generate/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code_context }),
  });
  if (!res.ok) throw new Error(`Planning failed: ${res.statusText}`);
  return res.json();
}

/**
 * Streams a single documentation section via SSE.
 * Calls onChunk with each token, onDone when complete, onError on failure.
 */
export function writeSection(
  code_context: CodeContext,
  doc_plan: DocPlan,
  section_id: string,
  onChunk: (chunk: string) => void,
  onDone: () => void,
  onError: (error: string) => void
): () => void {
  let cancelled = false;

  const run = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/generate/write`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code_context, doc_plan, section_id }),
      });

      if (!res.ok || !res.body) {
        onError(`Write request failed: ${res.statusText}`);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (!cancelled) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data:")) {
            const data = line.slice(5).trim();
            if (data && data !== "[DONE]") {
              onChunk(data);
            }
          } else if (line.startsWith("event: done")) {
            onDone();
            return;
          } else if (line.startsWith("event: error")) {
            // next data line has the error
          }
        }
      }
      onDone();
    } catch (err) {
      if (!cancelled) onError(String(err));
    }
  };

  run();
  return () => { cancelled = true; };
}

export async function exportMarkdown(
  doc_plan: DocPlan,
  sections_content: Record<string, string>
): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/export/markdown`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ doc_plan, sections_content, format: "markdown" }),
  });
  if (!res.ok) throw new Error(`Export failed: ${res.statusText}`);
  return res.blob();
}

export async function exportHtml(
  doc_plan: DocPlan,
  sections_content: Record<string, string>
): Promise<Blob> {
  const res = await fetch(`${API_BASE}/api/export/html`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ doc_plan, sections_content, format: "html" }),
  });
  if (!res.ok) throw new Error(`Export failed: ${res.statusText}`);
  return res.blob();
}
