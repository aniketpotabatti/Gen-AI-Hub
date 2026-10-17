"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import Link from "next/link";
import Logo from "@/components/Logo";

const SAMPLE_CODE_PREVIEW = `from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Payment Gateway API")

class ChargeRequest(BaseModel):
    amount: float
    currency: str = "USD"
    customer_id: str

@app.post("/v1/charges")
async def create_charge(req: ChargeRequest):
    """Processes idempotently charged transactions."""
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    return {"status": "succeeded", "charge_id": "ch_98412"}`;

const SAMPLE_DOC_PREVIEW = `# Payment Gateway API Reference

Processes idempotently charged transactions across global currencies.

### Endpoints

#### \`POST /v1/charges\`
Initiates a payment charge for an authenticated customer.

**Request Schema:**
- \`amount\` *(float, required)*: Non-negative charge amount.
- \`currency\` *(string, optional)*: ISO currency code (default: \`USD\`).
- \`customer_id\` *(string, required)*: Identifier of the target customer account.

**Example Request:**
\`\`\`bash
curl -X POST https://api.service.io/v1/charges \\
  -H "Content-Type: application/json" \\
  -d '{"amount": 49.99, "customer_id": "cust_123"}'
\`\`\`
`;

const PIPELINE_STEPS = [
  {
    step: "01",
    title: "Code AST Ingestion",
    desc: "Parses your Python, TypeScript, Go, or Rust source code into structured Abstract Syntax Trees without hallucinating parameters.",
    icon: "🔬",
    pill: "Deterministic",
  },
  {
    step: "02",
    title: "Doc Architecture Planner",
    desc: "Analyzes project type (API, library, CLI) and organizes an interactive multi-section documentation blueprint for review.",
    icon: "📐",
    pill: "Interactive Agent",
  },
  {
    step: "03",
    title: "Token Stream & Export",
    desc: "Streams documentation section-by-section via Server-Sent Events with instant export to Markdown or dark HTML.",
    icon: "⚡",
    pill: "Real-time SSE",
  },
];

const FEATURES = [
  {
    icon: "🔍",
    title: "Code-Aware Parsing",
    description:
      "Reads your actual AST — never hallucinates function signatures, argument defaults, or return types.",
    color: "from-violet-500/20 to-violet-600/5",
    border: "border-violet-500/20",
  },
  {
    icon: "🗺️",
    title: "Doc Architecture Planner",
    description:
      "Plans the documentation hierarchy before writing a word. Reorder, add custom sections, or regenerate anytime.",
    color: "from-cyan-500/20 to-cyan-600/5",
    border: "border-cyan-500/20",
  },
  {
    icon: "⚡",
    title: "Real-Time Streaming",
    description:
      "Watch your technical documentation materialize token by token via Server-Sent Events with zero lag.",
    color: "from-amber-500/20 to-amber-600/5",
    border: "border-amber-500/20",
  },
  {
    icon: "🔑",
    title: "BYOK & Model Control",
    description:
      "Bring your own Gemini or OpenAI API keys stored safely in browser cache, with support for fast and reasoning models.",
    color: "from-emerald-500/20 to-emerald-600/5",
    border: "border-emerald-500/20",
  },
  {
    icon: "🎯",
    title: "Tone & Audience Tuner",
    description:
      "Switch tone (Concise, Tutorial, In-depth) and audience depth (Beginner to Senior Architect) with one click.",
    color: "from-pink-500/20 to-pink-600/5",
    border: "border-pink-500/20",
  },
  {
    icon: "📦",
    title: "Multi-Format Export",
    description:
      "Download production documentation formatted as clean Markdown (.md) or dark-mode styled HTML (.html).",
    color: "from-indigo-500/20 to-indigo-600/5",
    border: "border-indigo-500/20",
  },
];

const LANGUAGES = ["Python", "JavaScript", "TypeScript", "Go", "Java", "Rust"];

export default function HomePage() {
  const router = useRouter();
  const [previewTab, setPreviewTab] = useState<"code" | "doc">("doc");

  return (
    <main className="relative overflow-hidden bg-[#08080d]">
      {/* Background grid + ambient glow */}
      <div className="fixed inset-0 pointer-events-none" aria-hidden>
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff05_1px,transparent_1px),linear-gradient(to_bottom,#ffffff05_1px,transparent_1px)] bg-[size:44px_44px]" />
        <div className="absolute top-[-15%] left-[-10%] w-[650px] h-[650px] rounded-full bg-violet-600/15 blur-[140px]" />
        <div className="absolute top-[20%] right-[-15%] w-[550px] h-[550px] rounded-full bg-cyan-600/15 blur-[140px]" />
        <div className="absolute bottom-[10%] left-[25%] w-[450px] h-[450px] rounded-full bg-indigo-600/10 blur-[120px]" />
      </div>

      {/* Hero Section */}
      <section className="relative min-h-[92vh] flex flex-col items-center justify-center text-center px-6 pt-28 pb-16 max-w-6xl mx-auto">
        {/* Release / Tech Badge */}
        <div className="mb-6 inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-violet-500/30 bg-violet-500/10 text-xs text-violet-300 shadow-sm shadow-violet-500/10">
          <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
          <span>AST Code Parser + Gemini 2.5 Flash Streaming</span>
        </div>

        {/* Hero Title */}
        <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight leading-[1.1] mb-6 max-w-4xl text-white">
          Developer documentation that{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-violet-400 via-purple-300 to-cyan-400">
            truly understands code
          </span>
        </h1>

        {/* Subtitle */}
        <p className="text-base sm:text-lg md:text-xl text-white/55 max-w-2xl leading-relaxed mb-10">
          Stop writing documentation by hand. AutoWriter parses your source code as an Abstract Syntax Tree, generates a structured doc plan, and streams production-ready technical guides.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center gap-4 mb-16 w-full sm:w-auto">
          <button
            id="hero-cta-btn"
            onClick={() => router.push("/editor")}
            className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-600 text-white font-semibold text-base
              hover:from-violet-500 hover:to-cyan-500 transition-all shadow-xl shadow-violet-500/25
              hover:shadow-violet-500/40 hover:-translate-y-0.5 active:translate-y-0 flex items-center justify-center gap-2"
          >
            <span>Launch Studio Free</span>
            <span className="text-white/70">→</span>
          </button>

          <a
            href="#architecture"
            className="w-full sm:w-auto px-7 py-3.5 rounded-xl border border-white/10 text-white/70 font-semibold text-base hover:bg-white/5 hover:text-white hover:border-white/20 transition-all flex items-center justify-center gap-2"
          >
            <span>Explore Architecture</span>
            <span className="text-white/40">↓</span>
          </a>
        </div>

        {/* Interactive Live Code-to-Doc Preview Window */}
        <div className="w-full max-w-4xl text-left rounded-2xl border border-white/10 bg-[#0c0c16] shadow-2xl shadow-violet-500/10 overflow-hidden">
          {/* Window Topbar */}
          <div className="px-4 py-3 bg-[#11111d] border-b border-white/[0.08] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-red-500/70 inline-block" />
              <span className="w-3 h-3 rounded-full bg-yellow-500/70 inline-block" />
              <span className="w-3 h-3 rounded-full bg-green-500/70 inline-block" />
              <span className="text-xs text-white/40 font-mono ml-2">charges_api.py ➔ docs.md</span>
            </div>

            {/* Toggle view tabs */}
            <div className="flex items-center gap-1 bg-white/5 p-1 rounded-lg border border-white/10">
              <button
                type="button"
                onClick={() => setPreviewTab("code")}
                className={`px-3 py-1 text-xs rounded-md font-medium transition-all ${
                  previewTab === "code"
                    ? "bg-violet-600/40 text-violet-200 border border-violet-500/30"
                    : "text-white/50 hover:text-white"
                }`}
              >
                Input Code (AST)
              </button>
              <button
                type="button"
                onClick={() => setPreviewTab("doc")}
                className={`px-3 py-1 text-xs rounded-md font-medium transition-all ${
                  previewTab === "doc"
                    ? "bg-cyan-600/40 text-cyan-200 border border-cyan-500/30"
                    : "text-white/50 hover:text-white"
                }`}
              >
                Synthesized Docs
              </button>
            </div>
          </div>

          {/* Window Code/Doc View */}
          <div className="p-6 font-mono text-xs overflow-x-auto min-h-[260px] bg-[#0c0c16] leading-relaxed">
            {previewTab === "code" ? (
              <pre className="text-violet-300">
                <code>{SAMPLE_CODE_PREVIEW}</code>
              </pre>
            ) : (
              <div className="text-white/80 space-y-2 whitespace-pre-wrap font-sans text-sm">
                <div className="font-mono text-xs text-cyan-400 font-semibold mb-2">
                  // Generated in 4.2s with Zero Parameter Hallucinations
                </div>
                <pre className="font-mono text-xs text-white/70 whitespace-pre-wrap">
                  {SAMPLE_DOC_PREVIEW}
                </pre>
              </div>
            )}
          </div>
        </div>

        {/* Supported Languages Badges */}
        <div className="flex flex-wrap items-center gap-2 justify-center mt-12">
          <span className="text-xs text-white/40 mr-2 font-mono">Supported Runtimes:</span>
          {LANGUAGES.map((lang) => (
            <span
              key={lang}
              className="px-3 py-1 rounded-full border border-white/[0.08] bg-white/[0.02] text-xs text-white/50 font-mono hover:border-violet-500/30 hover:text-white transition-colors"
            >
              {lang}
            </span>
          ))}
        </div>
      </section>

      {/* Visual Pipeline Section: How It Works */}
      <section id="architecture" className="relative max-w-6xl mx-auto px-6 py-20 border-t border-white/[0.06] scroll-mt-20">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-3">
            How AutoWriter Works
          </h2>
          <p className="text-white/50 text-base max-w-lg mx-auto">
            A deterministic Code-to-Doc architecture built specifically to eliminate AI hallucinations.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {PIPELINE_STEPS.map((s) => (
            <div
              key={s.step}
              className="p-6 rounded-2xl border border-white/[0.08] bg-white/[0.02] relative hover:border-violet-500/30 transition-all group"
            >
              <div className="flex items-center justify-between mb-4">
                <span className="text-2xl">{s.icon}</span>
                <span className="text-xs font-mono px-2 py-0.5 rounded-md bg-white/5 text-violet-300 border border-white/5">
                  {s.pill}
                </span>
              </div>
              <div className="text-xs text-white/30 font-mono mb-1">Step {s.step}</div>
              <h3 className="text-lg font-semibold text-white mb-2">{s.title}</h3>
              <p className="text-white/50 text-xs leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="relative max-w-6xl mx-auto px-6 py-20 border-t border-white/[0.06] scroll-mt-20">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-3">
            Engineered for Production Codebases
          </h2>
          <p className="text-white/50 text-base max-w-xl mx-auto">
            Every feature is structured around clean developer ergonomics and accurate API specifications.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((feat) => (
            <div
              key={feat.title}
              className={`p-6 rounded-2xl border bg-gradient-to-br ${feat.color} ${feat.border}
                hover:scale-[1.01] transition-transform duration-200 group overflow-hidden`}
            >
              <span className="text-3xl mb-4 block">{feat.icon}</span>
              <h3 className="text-base font-semibold text-white mb-2">{feat.title}</h3>
              <p className="text-white/50 text-xs leading-relaxed">{feat.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Final CTA Banner */}
      <section className="relative max-w-5xl mx-auto px-6 py-20">
        <div className="relative p-10 sm:p-14 rounded-3xl border border-violet-500/25 bg-gradient-to-br from-violet-600/15 via-[#0d0d18] to-cyan-600/10 text-center overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,#7c3aed15_0%,transparent_70%)]" />
          <h2 className="relative text-3xl sm:text-4xl font-bold text-white mb-4">
            Transform your code into live documentation
          </h2>
          <p className="relative text-white/50 text-base mb-8 max-w-lg mx-auto">
            Upload your file or paste your code snippet to get a full interactive documentation suite in seconds.
          </p>
          <button
            id="bottom-cta-btn"
            onClick={() => router.push("/editor")}
            className="inline-flex items-center gap-2 px-8 py-3.5 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-600 text-white font-semibold text-base
              hover:from-violet-500 hover:to-cyan-500 transition-all shadow-xl shadow-violet-500/25 hover:shadow-violet-500/40 hover:-translate-y-0.5"
          >
            Launch Editor Studio ✍️
          </button>
        </div>
      </section>

      {/* Professional Developer Footer */}
      <footer className="border-t border-white/[0.08] bg-[#07070b] py-10 px-6 text-xs text-white/40">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Logo size="sm" showText={false} />
            <span className="font-semibold text-white/80">AutoWriter<span className="text-violet-400">.ai</span></span>
            <span>— Code-to-Doc Generation Pipeline</span>
          </div>

          <div className="flex items-center gap-6">
            <Link href="/editor" className="hover:text-white transition-colors">
              Editor Studio
            </Link>
            <a href="#features" className="hover:text-white transition-colors">
              Features
            </a>
            <a href="#architecture" className="hover:text-white transition-colors">
              Architecture
            </a>
            <span className="text-white/20">|</span>
            <span className="text-white/30">Production Ready</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
