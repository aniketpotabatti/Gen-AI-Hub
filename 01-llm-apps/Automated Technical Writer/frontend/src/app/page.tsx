import Link from "next/link";

const FEATURES = [
  {
    icon: "🔍",
    title: "Code-Aware",
    description:
      "Reads your actual AST — never hallucinates function signatures or parameter types.",
    color: "from-violet-500/20 to-violet-600/5",
    border: "border-violet-500/20",
  },
  {
    icon: "🗺️",
    title: "Doc Architect",
    description:
      "Plans the full documentation hierarchy before writing a single word. You approve, then generation begins.",
    color: "from-cyan-500/20 to-cyan-600/5",
    border: "border-cyan-500/20",
  },
  {
    icon: "⚡",
    title: "Real-Time Streaming",
    description:
      "Watch your documentation materialize token by token — no waiting for a wall of text.",
    color: "from-amber-500/20 to-amber-600/5",
    border: "border-amber-500/20",
  },
  {
    icon: "🧬",
    title: "Style DNA",
    description:
      "Upload existing docs and the AI mirrors your team's tone, vocabulary, and formatting style.",
    color: "from-emerald-500/20 to-emerald-600/5",
    border: "border-emerald-500/20",
  },
  {
    icon: "🔁",
    title: "Living Docs",
    description:
      "Connect your GitHub repo and auto-regenerate only the sections affected by each code change.",
    color: "from-pink-500/20 to-pink-600/5",
    border: "border-pink-500/20",
  },
  {
    icon: "🎯",
    title: "Audience Switcher",
    description:
      "One click rewrites for Beginner, Intermediate, or Expert — same content, different depths.",
    color: "from-indigo-500/20 to-indigo-600/5",
    border: "border-indigo-500/20",
  },
];

const LANGUAGES = ["Python", "JavaScript", "TypeScript", "Go", "Java", "Rust"];

export default function HomePage() {
  return (
    <main className="relative overflow-hidden">
      {/* Background grid + gradient orbs */}
      <div className="fixed inset-0 pointer-events-none" aria-hidden>
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff08_1px,transparent_1px),linear-gradient(to_bottom,#ffffff08_1px,transparent_1px)] bg-[size:40px_40px]" />
        <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-violet-600/20 blur-[120px]" />
        <div className="absolute top-[10%] right-[-15%] w-[500px] h-[500px] rounded-full bg-cyan-600/15 blur-[120px]" />
        <div className="absolute bottom-[10%] left-[20%] w-[400px] h-[400px] rounded-full bg-indigo-600/10 blur-[100px]" />
      </div>

      {/* Hero */}
      <section className="relative min-h-screen flex flex-col items-center justify-center text-center px-6 pt-20">
        {/* Badge */}
        <div className="mb-6 inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-violet-500/30 bg-violet-500/10 text-sm text-violet-300">
          <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
          Powered by Gemini 1.5 Pro + LangChain
        </div>

        <h1 className="text-5xl md:text-7xl font-bold tracking-tight leading-[1.1] mb-6 max-w-4xl">
          Documentation that{" "}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-violet-400 via-purple-400 to-cyan-400">
            understands your code
          </span>
        </h1>

        <p className="text-lg md:text-xl text-white/50 max-w-2xl leading-relaxed mb-10">
          AutoWriter.ai parses your source code as an Abstract Syntax Tree, then writes
          production-quality technical docs — accurate, styled, and streaming in real time.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mb-16">
          <Link
            href="/editor"
            id="hero-cta-btn"
            className="px-8 py-4 rounded-xl bg-gradient-to-r from-violet-600 to-violet-500 text-white font-semibold text-lg
              hover:from-violet-500 hover:to-violet-400 transition-all shadow-2xl shadow-violet-500/30
              hover:shadow-violet-500/50 hover:-translate-y-1"
          >
            Start Writing for Free →
          </Link>
          <a
            href="https://github.com/aniketpotabatti/GenAIHub/tree/main/01-llm-apps/Automated%20Technical%20Writer"
            target="_blank"
            rel="noopener noreferrer"
            className="px-8 py-4 rounded-xl border border-white/10 text-white/70 font-semibold text-lg hover:bg-white/5 hover:text-white transition-all"
          >
            View on GitHub
          </a>
        </div>

        {/* Language pills */}
        <div className="flex flex-wrap gap-2 justify-center mb-20">
          {LANGUAGES.map((lang) => (
            <span
              key={lang}
              className="px-3 py-1 rounded-full border border-white/10 bg-white/[0.03] text-sm text-white/40 font-mono"
            >
              {lang}
            </span>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="relative max-w-7xl mx-auto px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-white mb-4">
            Not just another text generator
          </h2>
          <p className="text-white/50 text-lg max-w-xl mx-auto">
            Every feature is designed to solve a real documentation problem engineers face.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((feat) => (
            <div
              key={feat.title}
              className={`relative p-6 rounded-2xl border bg-gradient-to-br ${feat.color} ${feat.border}
                hover:scale-[1.02] transition-transform duration-200 group overflow-hidden`}
            >
              <div className="absolute inset-0 bg-gradient-to-br from-white/[0.03] to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
              <span className="text-3xl mb-4 block">{feat.icon}</span>
              <h3 className="text-lg font-semibold text-white mb-2">{feat.title}</h3>
              <p className="text-white/50 text-sm leading-relaxed">{feat.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA Banner */}
      <section className="relative max-w-5xl mx-auto px-6 pb-32">
        <div className="relative p-12 rounded-3xl border border-violet-500/20 bg-gradient-to-br from-violet-600/10 to-cyan-600/5 text-center overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,#7c3aed15_0%,transparent_70%)]" />
          <h2 className="relative text-4xl font-bold text-white mb-4">
            Ready to write better docs?
          </h2>
          <p className="relative text-white/50 text-lg mb-8 max-w-lg mx-auto">
            Paste your code, get a complete, accurate documentation suite in seconds.
          </p>
          <Link
            href="/editor"
            id="bottom-cta-btn"
            className="inline-flex items-center gap-2 px-10 py-4 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-600 text-white font-semibold text-lg
              hover:from-violet-500 hover:to-cyan-500 transition-all shadow-2xl shadow-violet-500/30 hover:shadow-violet-500/50 hover:-translate-y-1"
          >
            Open Editor ✍️
          </Link>
        </div>
      </section>
    </main>
  );
}
