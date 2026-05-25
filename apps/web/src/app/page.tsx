'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Image from 'next/image';
import { motion } from 'framer-motion';
import { Search, ShieldCheck, Code2, Sparkles, Layers, Scale, Globe, Zap } from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ThemeToggle } from '@/components/theme-toggle';

const fadeUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.6 } },
};

const stagger = {
  animate: { transition: { staggerChildren: 0.08 } },
};

export default function Home() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="relative min-h-screen bg-background">
      {/* Decorative gradients */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute left-1/2 top-[-10%] h-[40rem] w-[40rem] -translate-x-1/2 rounded-full bg-primary/20 blur-3xl" />
        <div className="absolute right-[-10%] bottom-[-10%] h-[30rem] w-[30rem] rounded-full bg-muted/60 blur-3xl" />
      </div>

      {/* Header */}
      <header className="sticky top-0 z-20 border-b bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/40">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-primary/80" />
            <span className="text-lg font-semibold tracking-tight">UnQuest</span>
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <a href="https://docs.unquest.ai" target="_blank" rel="noopener noreferrer" className="hover:text-foreground">Docs</a>
            <Link href="/pricing" className="hover:text-foreground">Pricing</Link>
            <Link href="/changelog" className="hover:text-foreground">Changelog</Link>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="ghost" asChild>
              <Link href="/auth/login">Sign in</Link>
            </Button>
            <Button asChild>
              <Link href="/auth/register">Get started</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main className="container mx-auto px-4 pt-16 md:pt-24">
        <motion.section
          className="mx-auto max-w-5xl text-center"
          initial="initial"
          animate="animate"
          variants={stagger}
        >
          <motion.div variants={fadeUp}>
            <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs text-muted-foreground">
              <Sparkles className="h-3.5 w-3.5 text-primary" /> RAG Data Ingestion Layer
            </span>
          </motion.div>
          <motion.h1
            className="mt-6 text-5xl font-bold tracking-tight md:text-6xl"
            variants={fadeUp}
          >
            Unified Search + Scrape API for reliable, real-time RAG
          </motion.h1>
          <motion.p
            className="mx-auto mt-6 max-w-3xl text-lg text-muted-foreground"
            variants={fadeUp}
          >
            Replace brittle pipelines with one API call that finds, crawls, and cleans web content into LLM-ready Markdown—fast, compliant, and production-grade.
          </motion.p>
          <motion.div className="mt-8 flex items-center justify-center gap-3" variants={fadeUp}>
            <Button size="lg" asChild>
              <Link href="/auth/register">Start free</Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <a href="https://docs.unquest.ai" target="_blank" rel="noopener noreferrer">Read docs</a>
            </Button>
          </motion.div>
        </motion.section>

        {/* Logos */}
        <section className="mx-auto mt-14 max-w-5xl">
          <div className="grid grid-cols-2 items-center gap-8 opacity-70 sm:grid-cols-3 md:grid-cols-5">
            <Image src="/next.svg" alt="Next.js" width={120} height={24} className="mx-auto h-6 w-auto" />
            <Image src="/vercel.svg" alt="Vercel" width={120} height={24} className="mx-auto h-5 w-auto" />
            <Image src="/globe.svg" alt="Globe" width={120} height={24} className="mx-auto h-6 w-auto" />
            <Image src="/window.svg" alt="Window" width={120} height={24} className="mx-auto h-6 w-auto" />
            <Image src="/file.svg" alt="File" width={120} height={24} className="mx-auto h-6 w-auto" />
          </div>
        </section>

        {/* Features */}
        <section className="mt-20">
          <div className="mx-auto max-w-6xl">
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {[
                {
                  icon: <Search className="h-5 w-5 text-primary" />, title: 'Integrated semantic search',
                  desc: 'Embeddings-powered discovery for high-relevance results, optimized for RAG.',
                },
                {
                  icon: <Globe className="h-5 w-5 text-primary" />, title: 'Headless rendering',
                  desc: 'Modern websites supported via headless browsing and smart retries.',
                },
                {
                  icon: <Code2 className="h-5 w-5 text-primary" />, title: 'LLM-ready Markdown',
                  desc: 'Clean extraction that removes boilerplate and returns structured Markdown.',
                },
                {
                  icon: <ShieldCheck className="h-5 w-5 text-primary" />, title: 'Compliance-by-design',
                  desc: 'robots.txt adherence, polite crawling, and optional PII filtering.',
                },
                {
                  icon: <Scale className="h-5 w-5 text-primary" />, title: 'Predictable pricing',
                  desc: 'Simple tiers with generous limits—no surprise token or citation fees.',
                },
                {
                  icon: <Layers className="h-5 w-5 text-primary" />, title: 'SDKs and great DX',
                  desc: 'Official TypeScript and Python SDKs, examples, and copy-paste docs.',
                },
              ].map((f, i) => (
                <motion.div key={f.title} initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ duration: 0.4, delay: i * 0.06 }}>
                  <Card className="h-full">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-xl">
                        {f.icon}
                        {f.title}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <CardDescription>{f.desc}</CardDescription>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Code demo */}
        <section className="mt-20">
          <div className="mx-auto max-w-5xl">
            <div className="grid gap-6 lg:grid-cols-2">
              <Card className="overflow-hidden">
                <CardHeader>
                  <CardTitle className="text-xl flex items-center gap-2"><Zap className="h-5 w-5 text-primary" /> One call. Search → Scrape → Clean.</CardTitle>
                  <CardDescription>Return top results as clean Markdown chunks, ready for your LLM.</CardDescription>
                </CardHeader>
                <CardContent className="pt-0">
                  <pre className="rounded-md bg-muted p-4 text-sm overflow-x-auto">
{`# Python
from unquest import Client

client = Client(api_key="USK_...")
resp = client.unified.query(
  q="What is Retrieval-Augmented Generation?",
  k=5,
  output_format="markdown"
)

for doc in resp.documents:
  print(doc.title)
  print(doc.content[:300])
`}
                  </pre>
                </CardContent>
              </Card>

              <Card className="overflow-hidden">
                <CardHeader>
                  <CardTitle className="text-xl">TypeScript</CardTitle>
                  <CardDescription>Use in Node or edge runtimes with first-class TypeScript types.</CardDescription>
                </CardHeader>
                <CardContent className="pt-0">
                  <pre className="rounded-md bg-muted p-4 text-sm overflow-x-auto">
{`// TypeScript
import { Unquest } from "@unquest/sdk";

const client = new Unquest({ apiKey: process.env.UNQUEST_API_KEY! });
const { documents } = await client.unified.query({
  q: "Top 3 papers on hybrid RAG",
  k: 3,
  outputFormat: "markdown",
});

documents.forEach(d => console.log(d.title));
`}
                  </pre>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="mt-20">
          <div className="mx-auto max-w-4xl text-center rounded-xl border bg-card p-10">
            <h3 className="text-3xl font-semibold tracking-tight">Build grounded AI faster</h3>
            <p className="mt-3 text-muted-foreground">Join teams shipping reliable RAG with a unified ingestion layer.</p>
            <div className="mt-6 flex items-center justify-center gap-3">
              <Button size="lg" asChild>
                <Link href="/auth/register">Create free account</Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <a href="https://docs.unquest.ai/quickstart" target="_blank" rel="noopener noreferrer">Quickstart</a>
              </Button>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="mt-20 border-t bg-background/70 backdrop-blur supports-[backdrop-filter]:bg-background/40">
          <div className="container mx-auto px-4 py-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="text-sm text-muted-foreground">© {new Date().getFullYear()} UnQuest. All rights reserved.</div>
              <div className="flex items-center gap-6 text-sm">
                <Link href="/terms" className="hover:underline">Terms</Link>
                <Link href="/privacy" className="hover:underline">Privacy</Link>
                <a href="https://docs.unquest.ai" target="_blank" rel="noopener noreferrer" className="hover:underline">Docs</a>
              </div>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
}
