import Link from "next/link"
import {
  ArrowRight,
  Brain,
  Compass,
  Github,
  Replace,
  Search,
  ShieldCheck,
  Zap,
} from "lucide-react"

import { ThemeToggle } from "./_components/theme-toggle"
import { CopyButton } from "./_components/copy-button"

const CURL_SNIPPET = `curl https://api.unsearch.dev/api/v1/search \\
  -H "X-API-Key: $UNSEARCH_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "Cloudflare Workers in 2026"}'`

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <Header />
      <Hero />
      <Logos />
      <Features />
      <Pricing />
      <CTA />
      <Footer />
    </main>
  )
}

function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-border/60 bg-background/70 backdrop-blur-md supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 text-base font-semibold tracking-tight">
          <Logomark />
          UnSearch
        </Link>
        <nav className="hidden items-center gap-7 text-sm md:flex">
          <Link href="/#features" className="text-muted-foreground transition-colors hover:text-foreground">
            Features
          </Link>
          <Link href="/#pricing" className="text-muted-foreground transition-colors hover:text-foreground">
            Pricing
          </Link>
          <Link href="https://docs.unsearch.dev" className="text-muted-foreground transition-colors hover:text-foreground">
            Docs
          </Link>
          <Link
            href="https://github.com/Rakesh1002/unsearch"
            className="flex items-center gap-1.5 text-muted-foreground transition-colors hover:text-foreground"
          >
            <Github className="size-4" />
            GitHub
          </Link>
        </nav>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Link
            href="/login"
            className="hidden text-sm text-muted-foreground transition-colors hover:text-foreground sm:inline-flex"
          >
            Sign in
          </Link>
          <Link
            href="/signup"
            className="inline-flex h-9 items-center rounded-md bg-primary px-3.5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
          >
            Get started
            <ArrowRight className="ml-1.5 size-3.5" />
          </Link>
        </div>
      </div>
    </header>
  )
}

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="dotted-grid pointer-events-none absolute inset-0 -z-10 opacity-60" aria-hidden />
      <div className="mx-auto flex max-w-4xl flex-col items-center px-4 pt-20 pb-16 text-center sm:pt-28">
        <Link
          href="https://github.com/Rakesh1002/unsearch"
          className="group mb-7 inline-flex items-center gap-2 rounded-full border border-border bg-background px-3 py-1 text-xs font-medium text-muted-foreground shadow-sm transition-colors hover:bg-accent hover:text-foreground"
        >
          <span className="inline-flex size-1.5 rounded-full bg-emerald-500" />
          Open-source · Apache 2.0
          <ArrowRight className="size-3 transition-transform group-hover:translate-x-0.5" />
        </Link>
        <h1 className="max-w-3xl text-balance text-5xl font-semibold tracking-tighter sm:text-6xl md:text-7xl">
          Search built for
          <span className="block bg-gradient-to-b from-foreground to-foreground/50 bg-clip-text pb-1 text-transparent">
            AI agents.
          </span>
        </h1>
        <p className="mt-6 max-w-2xl text-balance text-lg text-muted-foreground sm:text-xl">
          Real-time web search across 70+ engines, neural retrieval, fact verification, and
          deep-research agents. Drop-in replacement for Tavily and Exa — open source, edge-native,
          on Cloudflare.
        </p>
        <div className="mt-9 flex flex-col items-center gap-3 sm:flex-row">
          <Link
            href="/signup"
            className="inline-flex h-11 items-center rounded-md bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
          >
            Start for free
            <ArrowRight className="ml-1.5 size-4" />
          </Link>
          <Link
            href="https://docs.unsearch.dev"
            className="inline-flex h-11 items-center rounded-md border border-border bg-background px-5 text-sm font-medium transition-colors hover:bg-accent"
          >
            Read the docs
          </Link>
        </div>
        <div className="mt-14 w-full max-w-2xl">
          <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
            <div className="flex items-center justify-between border-b border-border bg-muted/40 px-4 py-2.5">
              <div className="flex items-center gap-1.5">
                <span className="size-2.5 rounded-full bg-red-400/70" />
                <span className="size-2.5 rounded-full bg-amber-400/70" />
                <span className="size-2.5 rounded-full bg-emerald-400/70" />
              </div>
              <span className="font-mono text-xs text-muted-foreground">curl</span>
              <CopyButton value={CURL_SNIPPET} />
            </div>
            <pre className="overflow-x-auto bg-card p-4 text-left font-mono text-[13px] leading-relaxed text-foreground">
{CURL_SNIPPET}
            </pre>
          </div>
        </div>
      </div>
    </section>
  )
}

function Logos() {
  const items = ["Tavily-compatible", "Exa-compatible", "OpenAI", "LangChain", "LlamaIndex", "Cloudflare"]
  return (
    <section aria-label="Compatible with" className="border-y border-border/60 bg-muted/20">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-10 gap-y-4 px-4 py-8 text-xs font-medium tracking-wide text-muted-foreground uppercase">
        <span className="text-[10px]">Plays nicely with</span>
        {items.map((i) => (
          <span key={i}>{i}</span>
        ))}
      </div>
    </section>
  )
}

function Features() {
  const features = [
    {
      icon: Search,
      title: "70+ search engines",
      body: "SearXNG-powered aggregation with sane defaults, per-engine routing, and intelligent fallback. One query, every source.",
      size: "lg",
    },
    {
      icon: Brain,
      title: "Neural search",
      body: "Semantic retrieval via Workers AI + Vectorize. Auto-prompting, highlights, similar-page lookup.",
      size: "lg",
    },
    {
      icon: Compass,
      title: "Deep research",
      body: "Multi-step research agents backed by Durable Objects — stateful, resumable, citation-grounded.",
      size: "lg",
    },
    {
      icon: ShieldCheck,
      title: "Fact verification",
      body: "Claim checks, source credibility scoring, batch verification for entire reports.",
    },
    {
      icon: Replace,
      title: "Tavily / Exa drop-in",
      body: "API compatibility with both — change the base URL, keep your code.",
    },
    {
      icon: Zap,
      title: "Edge-native",
      body: "Cloudflare Workers + Containers. <50ms p95 from anywhere on the planet.",
    },
  ] as const
  return (
    <section id="features" className="mx-auto max-w-6xl px-4 py-24">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-balance text-3xl font-semibold tracking-tighter sm:text-4xl">
          Everything an agent needs to know about the web.
        </h2>
        <p className="mt-3 text-balance text-muted-foreground">
          A composable search stack — primitives for retrieval, ranking, scraping, verification, and research.
        </p>
      </div>
      <div className="mt-14 grid grid-cols-1 gap-4 md:grid-cols-3">
        {features.map((f) => (
          <FeatureCard key={f.title} {...f} />
        ))}
      </div>
    </section>
  )
}

function FeatureCard({
  icon: Icon,
  title,
  body,
}: {
  icon: typeof Search
  title: string
  body: string
  size?: "lg"
}) {
  return (
    <div className="group relative overflow-hidden rounded-xl border border-border bg-card p-6 transition-all hover:border-foreground/20 hover:shadow-sm">
      <div className="mb-4 inline-flex size-9 items-center justify-center rounded-lg bg-muted text-foreground ring-1 ring-border">
        <Icon className="size-4" />
      </div>
      <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{body}</p>
    </div>
  )
}

function Pricing() {
  const plans = [
    { name: "Free", price: "$0", queries: "5,000 / mo", cta: "Start free", note: "For hobby projects and evaluation." },
    { name: "Pro", price: "$19", queries: "25,000 / mo", cta: "Upgrade to Pro", note: "For solo builders shipping production." },
    { name: "Growth", price: "$49", queries: "100,000 / mo", cta: "Upgrade to Growth", note: "For teams running real agent workloads.", highlight: true },
    { name: "Scale", price: "$149", queries: "500,000 / mo", cta: "Talk to sales", note: "For high-volume RAG and research pipelines." },
  ]
  return (
    <section id="pricing" className="mx-auto max-w-6xl px-4 py-24">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-balance text-3xl font-semibold tracking-tighter sm:text-4xl">Honest pricing.</h2>
        <p className="mt-3 text-balance text-muted-foreground">
          5× more free queries than the competition. Or self-host for unlimited — it&apos;s open source.
        </p>
      </div>
      <div className="mt-14 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {plans.map((p) => (
          <div
            key={p.name}
            className={`relative flex flex-col rounded-xl border bg-card p-6 transition-all hover:-translate-y-0.5 ${
              p.highlight
                ? "border-foreground/30 shadow-md ring-1 ring-foreground/10"
                : "border-border hover:border-foreground/20"
            }`}
          >
            {p.highlight && (
              <span className="absolute -top-2.5 right-4 inline-flex items-center rounded-full bg-foreground px-2.5 py-0.5 text-[10px] font-medium tracking-wide text-background uppercase">
                Most popular
              </span>
            )}
            <h3 className="text-sm font-semibold">{p.name}</h3>
            <p className="mt-1 text-xs text-muted-foreground">{p.note}</p>
            <div className="mt-5 text-4xl font-semibold tracking-tighter">
              {p.price}
              <span className="text-sm font-normal text-muted-foreground">/mo</span>
            </div>
            <p className="mt-1.5 text-xs text-muted-foreground">{p.queries}</p>
            <Link
              href="/signup"
              className={`mt-6 inline-flex h-9 items-center justify-center rounded-md px-3 text-sm font-medium transition-colors ${
                p.highlight
                  ? "bg-primary text-primary-foreground hover:bg-primary/90"
                  : "border border-border bg-background hover:bg-accent"
              }`}
            >
              {p.cta}
            </Link>
          </div>
        ))}
      </div>
    </section>
  )
}

function CTA() {
  return (
    <section className="mx-auto max-w-6xl px-4 pb-24">
      <div className="relative overflow-hidden rounded-2xl border border-border bg-card p-10 text-center sm:p-16">
        <div className="dotted-grid pointer-events-none absolute inset-0 opacity-50" aria-hidden />
        <div className="relative">
          <h2 className="text-balance text-3xl font-semibold tracking-tighter sm:text-4xl">
            Stop paying per-query taxes.
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-balance text-muted-foreground">
            5,000 free queries every month. No card required. Migrate from Tavily or Exa in one line.
          </p>
          <div className="mt-7 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/signup"
              className="inline-flex h-11 items-center rounded-md bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
            >
              Start for free
              <ArrowRight className="ml-1.5 size-4" />
            </Link>
            <Link
              href="https://github.com/Rakesh1002/unsearch"
              className="inline-flex h-11 items-center rounded-md border border-border bg-background px-5 text-sm font-medium transition-colors hover:bg-accent"
            >
              <Github className="mr-2 size-4" />
              Star on GitHub
            </Link>
          </div>
        </div>
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t border-border/60">
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-8 px-4 py-12 sm:grid-cols-4">
        <div className="col-span-2 sm:col-span-1">
          <Link href="/" className="flex items-center gap-2 text-base font-semibold tracking-tight">
            <Logomark />
            UnSearch
          </Link>
          <p className="mt-3 max-w-xs text-sm text-muted-foreground">
            Open-source search infrastructure for the agentic era.
          </p>
        </div>
        <FooterCol
          title="Product"
          links={[
            { href: "/#features", label: "Features" },
            { href: "/#pricing", label: "Pricing" },
            { href: "https://docs.unsearch.dev", label: "Docs" },
            { href: "https://status.unsearch.dev", label: "Status" },
          ]}
        />
        <FooterCol
          title="Resources"
          links={[
            { href: "https://github.com/Rakesh1002/unsearch", label: "GitHub" },
            { href: "https://docs.unsearch.dev/changelog", label: "Changelog" },
            { href: "https://docs.unsearch.dev/migrate/tavily", label: "Migrate from Tavily" },
            { href: "https://docs.unsearch.dev/migrate/exa", label: "Migrate from Exa" },
          ]}
        />
        <FooterCol
          title="Company"
          links={[
            { href: "mailto:support@unsearch.dev", label: "Support" },
            { href: "https://github.com/Rakesh1002/unsearch/blob/main/LICENSE", label: "License" },
            { href: "https://github.com/Rakesh1002/unsearch/blob/main/SECURITY.md", label: "Security" },
          ]}
        />
      </div>
      <div className="border-t border-border/60">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-5 text-xs text-muted-foreground">
          <span>© {new Date().getFullYear()} UnSearch. Apache-2.0.</span>
          <span className="font-mono">unsearch.dev</span>
        </div>
      </div>
    </footer>
  )
}

function FooterCol({ title, links }: { title: string; links: Array<{ href: string; label: string }> }) {
  return (
    <div>
      <h4 className="text-xs font-semibold tracking-wide text-foreground uppercase">{title}</h4>
      <ul className="mt-3 space-y-2 text-sm">
        {links.map((l) => (
          <li key={l.href}>
            <Link href={l.href} className="text-muted-foreground transition-colors hover:text-foreground">
              {l.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

function Logomark() {
  return (
    <span
      aria-hidden
      className="relative inline-flex size-6 items-center justify-center rounded-md bg-gradient-to-br from-foreground to-foreground/70 text-background"
    >
      <Search className="size-3.5" strokeWidth={2.5} />
    </span>
  )
}
