import type { Metadata, Viewport } from "next"
import type { ReactNode } from "react"
import { GeistSans } from "geist/font/sans"
import { GeistMono } from "geist/font/mono"
import { ThemeProvider } from "next-themes"

import "./globals.css"

export const metadata: Metadata = {
  title: { default: "UnSearch — Search built for AI agents", template: "%s · UnSearch" },
  description: "Open-source search API for AI agents, RAG pipelines, and LLM applications. Real-time web search across 70+ engines, neural search, fact verification, deep research.",
  metadataBase: new URL("https://unsearch.dev"),
  openGraph: {
    title: "UnSearch — Search built for AI agents",
    description: "Open-source search API for AI agents. Real-time web search, neural retrieval, deep research.",
    url: "https://unsearch.dev",
    siteName: "UnSearch",
    type: "website",
  },
  twitter: { card: "summary_large_image", title: "UnSearch", description: "Open-source search API for AI agents." },
}

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0a0a" },
  ],
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${GeistSans.variable} ${GeistMono.variable}`}
    >
      <body>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
