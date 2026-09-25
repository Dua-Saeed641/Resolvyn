import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });

export const metadata: Metadata = {
  title: "Resolvyn: autonomous customer support",
  description: "AI support agents that resolve issues by voice, chat and email, with humans in the loop.",
  openGraph: { title: "Resolvyn", description: "The AI support team that resolves issues, not just answers questions.", images: ["/resolvyn-banner.png"] },
};

// Runs before the first paint: apply the saved theme (default: the system preference).
const THEME_SCRIPT = `try{var t=localStorage.getItem("theme");var d=t?t==="dark":window.matchMedia("(prefers-color-scheme: dark)").matches;document.documentElement.classList.toggle("dark",d)}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
