import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AutoWriter.ai — AI-Powered Technical Documentation",
  description:
    "Generate accurate, production-quality technical documentation from your source code using AI. Code-aware, hallucination-free, and beautifully formatted.",
  keywords: ["technical writing", "documentation", "AI", "LLM", "developer tools"],
  openGraph: {
    title: "AutoWriter.ai",
    description: "AI-powered documentation generator that understands your code.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-[#0a0a0f] text-white antialiased">
        <Navbar />
        {children}
      </body>
    </html>
  );
}
