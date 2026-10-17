import React from "react";

interface LogoProps {
  size?: "sm" | "md" | "lg";
  showText?: boolean;
  className?: string;
}

export default function Logo({ size = "md", showText = true, className = "" }: LogoProps) {
  const iconDimensions = {
    sm: "w-6 h-6",
    md: "w-8 h-8",
    lg: "w-10 h-10",
  }[size];

  const svgDimensions = {
    sm: 14,
    md: 18,
    lg: 22,
  }[size];

  const textSize = {
    sm: "text-xs tracking-tight",
    md: "text-sm tracking-tight",
    lg: "text-lg tracking-tight",
  }[size];

  return (
    <div className={`flex items-center gap-2.5 group cursor-pointer select-none ${className}`}>
      {/* Precision Engineered Tech Glyph */}
      <div
        className={`relative ${iconDimensions} rounded-xl bg-gradient-to-b from-[#181829] to-[#0c0c16] border border-white/[0.14] p-0.5 shadow-lg shadow-violet-950/40 group-hover:border-violet-500/50 group-hover:shadow-violet-500/25 transition-all duration-300 flex items-center justify-center overflow-hidden`}
      >
        {/* Subtle inner radial glow */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(139,92,246,0.35),transparent_70%)] pointer-events-none" />

        {/* Vector SVG: Stylized Code Bracket merging with Precision Quill Tip */}
        <svg
          width={svgDimensions}
          height={svgDimensions}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="relative z-10 transition-transform duration-300 group-hover:scale-105"
        >
          <defs>
            <linearGradient id="aw-brand-grad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
              <stop stopColor="#818cf8" />
              <stop offset="0.5" stopColor="#a78bfa" />
              <stop offset="1" stopColor="#38bdf8" />
            </linearGradient>
            <linearGradient id="aw-accent-grad" x1="10" y1="6" x2="21" y2="17" gradientUnits="userSpaceOnUse">
              <stop stopColor="#c084fc" />
              <stop offset="1" stopColor="#06b6d4" />
            </linearGradient>
          </defs>

          {/* Code Ingestion Angle */}
          <path
            d="M8.5 7L3.5 12L8.5 17"
            stroke="url(#aw-brand-grad)"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Architectural Quill Pen Body */}
          <path
            d="M19.5 4.5L12 12V15.5H15.5L21.5 9.5C22.1 8.9 22.1 7.9 21.5 7.3L19.5 5.3C18.9 4.7 17.9 4.7 17.3 5.3"
            stroke="url(#aw-accent-grad)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Ink / AST Synthesis Spark */}
          <circle cx="12" cy="15.5" r="1.2" fill="#38bdf8" />
        </svg>
      </div>

      {showText && (
        <div className="flex items-baseline">
          <span className={`font-bold font-sans text-white/95 group-hover:text-white transition-colors ${textSize}`}>
            AutoWriter
          </span>
          <span className="font-mono text-violet-400 font-semibold text-[11px] ml-0.5 tracking-normal">
            .ai
          </span>
          {/* <span className="ml-2 hidden sm:inline-block px-1.5 py-0.2 text-[9px] font-mono uppercase tracking-wider rounded border border-violet-500/30 bg-violet-500/10 text-violet-300">
            PRO
          </span> */}
        </div>
      )}
    </div>
  );
}
