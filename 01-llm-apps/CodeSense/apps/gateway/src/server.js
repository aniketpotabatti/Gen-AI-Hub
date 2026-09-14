import cors from "cors";
import express from "express";
import Anthropic from "@anthropic-ai/sdk";
import OpenAI from "openai";
import { buildPrompt, validateRequest } from "@codesense/core";

const app = express();
const requests = new Map();
const RATE_LIMIT = 30;
const WINDOW_MS = 60_000;
app.use(cors({ origin: process.env.WEB_ORIGIN || "http://localhost:5173" }));
app.use(express.json({ limit: "20kb" }));

function allowed(ip) {
  const now = Date.now();
  const hits = (requests.get(ip) || []).filter((time) => now - time < WINDOW_MS);
  if (hits.length >= RATE_LIMIT) return false;
  hits.push(now); requests.set(ip, hits); return true;
}
function sendError(res, status, error, message) {
  res.status(status).json({ error, message, retryAfter: status === 429 ? WINDOW_MS : undefined });
}
function sse(res, data) { res.write(`data: ${JSON.stringify(data)}\n\n`); }

async function streamAnthropic(prompt, maxTokens, emit, apiKey, model) {
  const client = new Anthropic({ apiKey });
  const stream = await client.messages.stream({ model: model || "claude-3-5-haiku-latest", max_tokens: maxTokens, messages: [{ role: "user", content: prompt }] });
  for await (const event of stream) if (event.type === "content_block_delta" && event.delta.type === "text_delta") emit(event.delta.text);
}
async function streamOpenAI(prompt, maxTokens, emit, apiKey, baseURL, model) {
  const client = new OpenAI({ apiKey, baseURL: baseURL || undefined });
  const stream = await client.chat.completions.create({ model: model || "gpt-4o-mini", max_tokens: maxTokens, stream: true, messages: [{ role: "system", content: "You are CodeSense, concise and accurate." }, { role: "user", content: prompt }] });
  for await (const chunk of stream) { const text = chunk.choices[0]?.delta?.content; if (text) emit(text); }
}

app.get("/health", (_req, res) => res.json({ status: "ok", authentication: "Bring your own API key" }));
app.post("/api/codesense", async (req, res) => {
  const invalid = validateRequest(req.body);
  if (invalid) return sendError(res, 400, "INVALID_REQUEST", invalid);
  if (!allowed(req.ip)) return sendError(res, 429, "RATE_LIMITED", "Too many requests. Try again shortly.");
  const suppliedKey = req.get("x-codesense-api-key");
  const suppliedUrl = req.get("x-codesense-api-url");
  const suppliedModel = req.get("x-codesense-model");
  const suppliedProvider = req.get("x-codesense-provider") || "openai-compatible";
  if (!suppliedKey) return sendError(res, 400, "API_KEY_REQUIRED", "Enter an API key in the CodeSense provider panel.");
  res.set({ "Content-Type": "text/event-stream", "Cache-Control": "no-cache", Connection: "keep-alive" }); res.flushHeaders();
  const prompt = buildPrompt(req.body); const maxTokens = req.body.mode === "review" ? 600 : 400;
  const emit = (delta) => sse(res, { delta });
  try {
    if (suppliedProvider === "anthropic") await streamAnthropic(prompt, maxTokens, emit, suppliedKey, suppliedModel);
    else {
      const baseURL = suppliedUrl || (suppliedProvider === "gemini" ? "https://generativelanguage.googleapis.com/v1beta/openai/" : undefined);
      await streamOpenAI(prompt, maxTokens, emit, suppliedKey, baseURL, suppliedModel || (suppliedProvider === "gemini" ? "gemini-2.0-flash" : undefined));
    }
    sse(res, "[DONE]"); res.end();
  } catch (error) {
    console.error("Provider failure", error.message);
    const providerStatus = Number(error?.status);
    const message = providerStatus === 401 || providerStatus === 403
      ? "Your provider rejected the API key. Check the key, base URL, and model name."
      : providerStatus === 404
        ? "The provider base URL or model was not found. Check both values."
        : providerStatus === 429
          ? "Your provider rate limit was reached. Please wait and retry."
          : `Provider request failed${providerStatus ? ` (${providerStatus})` : ""}: ${error?.message || "Unknown provider error"}`;
    sse(res, { error: "PROVIDER_REQUEST_FAILED", message }); res.end();
  }
});
app.listen(process.env.PORT || 8787, () => console.log(`CodeSense gateway on :${process.env.PORT || 8787}`));
