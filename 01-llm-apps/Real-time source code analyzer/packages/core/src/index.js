export const MODES = ["explain", "review", "suggest"];

export function extractContext(code, cursorLine, before = 30, after = 10) {
  const lines = code.split(/\r?\n/);
  const line = Math.max(1, Math.min(Number(cursorLine) || 1, lines.length));
  return lines.slice(Math.max(0, line - 1 - before), line - 1 + after).join("\n");
}

export function buildPrompt({ mode, language, snippet, cursorLine, cursorCol }) {
  const base = `You are CodeSense, a precise and concise code assistant embedded in a developer editor. Never invent APIs or behavior. Detected language: ${language}. Mode: ${mode}.`;
  if (mode === "explain") return `${base}\nExplain this code in 2-4 sentences, focusing on intent rather than syntax.\n\n${snippet}`;
  if (mode === "review") return `${base}\nReview this code in under 200 words. Use exactly these headings: ✅ What's good, ⚠️ What to improve, 💡 Optional refactor. Be actionable.\n\n${snippet}`;
  return `${base}\nComplete the code at line ${cursorLine}, column ${cursorCol}. Return ONLY the completion with no markdown fences. Stop at a logical boundary.\n\n${snippet}`;
}

export function validateRequest(body) {
  if (!body || !MODES.includes(body.mode)) return "mode must be explain, review, or suggest";
  if (typeof body.language !== "string" || !body.language.trim()) return "language is required";
  if (typeof body.snippet !== "string" || !body.snippet.trim()) return "snippet is required";
  if (body.snippet.length > 12000) return "snippet exceeds the 12,000 character limit";
  return null;
}
