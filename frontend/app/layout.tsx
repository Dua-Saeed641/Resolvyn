import type { Metadata } from "next";
import { Inter } from "next/font/google";
import localFont from "next/font/local";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });

// Neue Machina: the display face of the Resolvyn brand (banner, headlines, numbers, titles).
const machina = localFont({
  src: [
    { path: "../public/fonts/neuemachina-light.otf", weight: "300", style: "normal" },
    { path: "../public/fonts/neuemachina-regular.otf", weight: "400", style: "normal" },
    { path: "../public/fonts/neuemachina-ultrabold.otf", weight: "800", style: "normal" },
  ],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Resolvyn: autonomous customer support",
  description: "AI support agents that resolve issues by voice, chat and email, with humans in the loop.",
  openGraph: { title: "Resolvyn", description: "The AI support team that resolves issues, not just answers questions.", images: ["/resolvyn-banner.png"] },
};

// Runs before the first paint: apply the saved theme (default: the system preference).
const THEME_SCRIPT = `try{var t=localStorage.getItem("theme");var d=t?t==="dark":window.matchMedia("(prefers-color-scheme: dark)").matches;document.documentElement.classList.toggle("dark",d)}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${machina.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
