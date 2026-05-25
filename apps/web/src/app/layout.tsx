import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "../lib/providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: "UnQuest - Privacy-Respecting Search API",
  description: "Powerful web search and content scraping API with privacy at its core. Built for developers, powered by SearXNG.",
  keywords: ["search API", "web scraping", "privacy", "SearXNG", "developer tools"],
  authors: [{ name: "UnQuest Team" }],
  creator: "UnQuest",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://unquest.ai",
    title: "UnQuest - Privacy-Respecting Search API",
    description: "Powerful web search and content scraping API with privacy at its core.",
    siteName: "UnQuest",
  },
  twitter: {
    card: "summary_large_image",
    title: "UnQuest - Privacy-Respecting Search API",
    description: "Powerful web search and content scraping API with privacy at its core.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}
      >
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
