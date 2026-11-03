import "@fontsource-variable/bricolage-grotesque";
import "@fontsource-variable/instrument-sans";
import "@fontsource-variable/jetbrains-mono";
import { Analytics } from "@vercel/analytics/next";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import Toaster from "@/components/Toaster";
import "./globals.css";

export const metadata = {
  metadataBase: new URL("https://code-atlas-nine.vercel.app"),
  title: {
    default: "CodeAtlas — map the risks in any codebase",
    template: "%s · CodeAtlas",
  },
  description:
    "Point CodeAtlas at a GitHub repo or ZIP and get a report of hardcoded secrets, risky code patterns, complexity hot spots and an AI-written summary.",
  openGraph: {
    title: "CodeAtlas",
    description: "Find hardcoded secrets, risky patterns and complexity hot spots in any repository.",
    type: "website",
  },
};

export const viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#eef1ec" },
    { media: "(prefers-color-scheme: dark)", color: "#10181c" },
  ],
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-dvh flex flex-col antialiased">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded focus:bg-surface focus:px-3 focus:py-2"
        >
          Skip to content
        </a>
        <SiteHeader />
        <main id="main" className="flex-1">
          {children}
        </main>
        <SiteFooter />
        <Toaster />
        <Analytics />
      </body>
    </html>
  );
}