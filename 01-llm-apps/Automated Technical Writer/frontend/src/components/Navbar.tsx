"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import Logo from "@/components/Logo";

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled
        ? "bg-[#08080d]/90 backdrop-blur-xl border-b border-white/5 shadow-lg shadow-black/20"
        : "bg-transparent"
        }`}
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center">
          <Logo size="md" />
        </Link>

        {/* Nav links */}
        <div className="flex items-center gap-6">
          <Link
            href="/#features"
            className="text-xs font-medium text-white/60 hover:text-white transition-colors"
          >
            Features
          </Link>
          <Link
            href="/#architecture"
            className="text-xs font-medium text-white/60 hover:text-white transition-colors"
          >
            Architecture
          </Link>
          <Link
            href="/editor"
            className="text-xs px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-violet-600 to-indigo-600 hover:from-violet-500 hover:to-indigo-500 text-white font-medium shadow-md shadow-violet-600/20 border border-violet-400/20 transition-all hover:shadow-violet-600/35"
          >
            Open Studio →
          </Link>
        </div>
      </div>
    </nav>
  );
}
