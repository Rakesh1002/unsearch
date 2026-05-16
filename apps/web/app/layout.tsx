import type { Metadata } from "next"
import type { ReactNode } from "react"

import "./globals.css"

export const metadata: Metadata = {
  title: { default: "UnSearch", template: "%s · UnSearch" },
  description: "Open-source search API for AI agents, RAG pipelines, and LLM applications.",
  metadataBase: new URL("https://unsearch.dev"),
  openGraph: {
    title: "UnSearch",
    description: "Open-source search API for AI agents.",
    url: "https://unsearch.dev",
    siteName: "UnSearch",
    type: "website",
  },
  twitter: { card: "summary_large_image", title: "UnSearch" },
}

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>{children}</body>
    </html>
  )
}
