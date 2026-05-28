import Link from "next/link"
import {
  ArrowRight,
  FileCheck2,
  Fingerprint,
  Github,
  History,
  Layers,
  Lock,
  ScrollText,
  ShieldCheck,
  Terminal,
} from "lucide-react"

import { ThemeToggle } from "./_components/theme-toggle"
import { CopyButton } from "./_components/copy-button"

const MCP_SNIPPET = `claude mcp add unsearch
# or, in any MCP-compatible client:
npx @unsearch/mcp-server`

const VERIFY_SNIPPET = `curl https://api.unsearch.dev/api/v1/verify/claim \\
  -H "X-API-Key: $UNSEARCH_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "claim": "EU AI Act full enforcement begins August 2026",
    "source_url": "https://digital-strategy.ec.europa.eu/..."
  }'

# → { "supported": true, "confidence": 0.94, "evidence_spans": [...] }`

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <Header />
      <Hero />
      <ProblemStrip />
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
            How it works
          </Link>
          <Link href="/#pricing" className="text-muted-foreground transition-colors hover:text-foreground">
            Pricing
          </Link>
          <Link href="/eu-ai-act" className="text-muted-foreground transition-colors hover:text-foreground">
            EU AI Act
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
          Apache 2.0 · MCP-native · WACZ-aligned
          <ArrowRight className="size-3 transition-transform group-hover:translate-x-0.5" />
        </Link>
        <h1 className="max-w-3xl text-balance text-5xl font-semibold tracking-tighter sm:text-6xl md:text-7xl">
          Verifiable web retrieval
          <span className="block bg-gradient-to-b from-foreground to-foreground/50 bg-clip-text pb-1 text-transparent">
            for AI agents.
          </span>
        </h1>
        <p className="mt-6 max-w-2xl text-balance text-lg text-muted-foreground sm:text-xl">
          Every result signed, hashed, snapshotted, and replayable months later. Built for legal,
          medical, finance, and other regulated AI teams who can&apos;t ship native LLM search past
          their compliance review.
        </p>
        <div className="mt-9 flex flex-col items-center gap-3 sm:flex-row">
          <Link
            href="https://docs.unsearch.dev/quickstart#mcp"
            className="inline-flex h-11 items-center rounded-md bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
          >
            <Terminal className="mr-1.5 size-4" />
            Install via MCP
          </Link>
          <Link
            href="/eu-ai-act"
            className="inline-flex h-11 items-center rounded-md border border-border bg-background px-5 text-sm font-medium transition-colors hover:bg-accent"
          >
            EU AI Act readiness
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
              <span className="font-mono text-xs text-muted-foreground">mcp install</span>
              <CopyButton value={MCP_SNIPPET} />
            </div>
            <pre className="overflow-x-auto bg-card p-4 text-left font-mono text-[13px] leading-relaxed text-foreground">
{MCP_SNIPPET}
            </pre>
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Free tier 5,000 verified searches / month. No signup required to evaluate.
          </p>
        </div>
      </div>
    </section>
  )
}

function ProblemStrip() {
  const stats = [
    { number: "$145K", caption: "US court sanctions for AI-hallucinated citations in Q1 2026 alone" },
    { number: "1-in-6", caption: "Harvey AI ($8B valuation) queries still hallucinate" },
    { number: "40–60%", caption: "Medical RAG reference fabrication rate without retrieval" },
    { number: "Aug 2026", caption: "EU AI Act Article 12 full enforcement begins" },
  ]
  return (
    <section aria-label="The problem" className="border-y border-border/60 bg-muted/20">
      <div className="mx-auto max-w-6xl px-4 py-12">
        <p className="mb-7 text-center text-xs font-medium tracking-wide text-muted-foreground uppercase">
          The retrieval primitive that nobody owns — yet
        </p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-6 sm:grid-cols-4">
          {stats.map((s) => (
            <div key={s.number} className="text-center">
              <div className="text-3xl font-semibold tracking-tighter sm:text-4xl">{s.number}</div>
              <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{s.caption}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function Features() {
  const features = [
    {
      icon: Fingerprint,
      title: "Signed citation envelope",
      body: "Every result returns { url, sha256, fetched_at, snapshot_key, signature }. WACZ-aligned so the broader provenance ecosystem reads it natively.",
    },
    {
      icon: ScrollText,
      title: "Content-addressable snapshots",
      body: "Every retrieved page is hashed and pinned to R2 — yours on self-host, ours on hosted. URL rot and silent edits can't break your audit trail.",
    },
    {
      icon: FileCheck2,
      title: "Claim verification",
      body: "POST /verify/claim returns span-level evidence + confidence. Re-fetches the source, runs an LLM-graded NLI check. No homemade graders.",
    },
    {
      icon: History,
      title: "Replayable audit log",
      body: "Per-API-key audit log of every search, snapshot, and verification. Retain 7 days (Free) to 10 years (Enterprise / self-host) — meets EU AI Act Article 12.",
    },
    {
      icon: Terminal,
      title: "MCP-first distribution",
      body: "claude mcp add unsearch wires Claude Code, Codex CLI, Cursor, Continue.dev, Zed in one command. verify_claim exposed as a tool, not buried in an SDK.",
    },
    {
      icon: Lock,
      title: "Self-host on your Cloudflare",
      body: "wrangler deploy from a forked repo. Customer-controlled signing keys. Apache 2.0 + Cloudflare Containers GA — your data, your perimeter, your audit logs.",
    },
  ] as const
  return (
    <section id="features" className="mx-auto max-w-6xl px-4 py-24">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-balance text-3xl font-semibold tracking-tighter sm:text-4xl">
          The primitive your duct-tape stack is missing.
        </h2>
        <p className="mt-3 text-balance text-muted-foreground">
          Tavily + Firecrawl + Playwright + BART-MNLI + a Postgres provenance table is what you build
          today. UnSearch is what you reach for instead.
        </p>
      </div>
      <div className="mt-14 grid grid-cols-1 gap-4 md:grid-cols-3">
        {features.map((f) => (
          <FeatureCard key={f.title} {...f} />
        ))}
      </div>
      <div className="mt-12 overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <div className="flex items-center justify-between border-b border-border bg-muted/40 px-4 py-2.5">
          <div className="flex items-center gap-1.5">
            <span className="size-2.5 rounded-full bg-red-400/70" />
            <span className="size-2.5 rounded-full bg-amber-400/70" />
            <span className="size-2.5 rounded-full bg-emerald-400/70" />
          </div>
          <span className="font-mono text-xs text-muted-foreground">POST /api/v1/verify/claim</span>
          <CopyButton value={VERIFY_SNIPPET} />
        </div>
        <pre className="overflow-x-auto bg-card p-4 text-left font-mono text-[13px] leading-relaxed text-foreground">
{VERIFY_SNIPPET}
        </pre>
      </div>
    </section>
  )
}

function FeatureCard({
  icon: Icon,
  title,
  body,
}: {
  icon: typeof Fingerprint
  title: string
  body: string
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
    {
      name: "Free",
      price: "$0",
      searches: "5,000 searches / mo",
      verifications: "100 verifications / mo",
      retention: "7-day audit log",
      cta: "Start free",
      note: "For evaluation and ICP-3 research workflows.",
    },
    {
      name: "Pro",
      price: "$19",
      searches: "25,000 searches / mo",
      verifications: "1,000 verifications / mo",
      retention: "30-day audit log",
      cta: "Upgrade to Pro",
      note: "For solo builders shipping a real agent.",
    },
    {
      name: "Growth",
      price: "$49",
      searches: "100,000 searches / mo",
      verifications: "10,000 verifications / mo",
      retention: "90-day audit log",
      cta: "Upgrade to Growth",
      note: "For regulated-AI startups in production.",
      highlight: true,
    },
    {
      name: "Self-host",
      price: "$24K/yr",
      searches: "Unlimited",
      verifications: "Unlimited",
      retention: "10-year audit log",
      cta: "Talk to founder",
      note: "Runs in your own CF account; customer-controlled keys; BAA / DPA available on v2.",
    },
  ]
  return (
    <section id="pricing" className="mx-auto max-w-6xl px-4 py-24">
      <div className="mx-auto max-w-2xl text-center">
        <h2 className="text-balance text-3xl font-semibold tracking-tighter sm:text-4xl">
          Priced for signed and verified, not just SERP.
        </h2>
        <p className="mt-3 text-balance text-muted-foreground">
          Every tier signs and verifies. Free is not a crippled version of the wedge.
          12-month written notice on any price change to existing customers.
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
              {p.name !== "Self-host" && (
                <span className="text-sm font-normal text-muted-foreground">/mo</span>
              )}
            </div>
            <ul className="mt-4 space-y-1.5 text-xs text-muted-foreground">
              <li>{p.searches}</li>
              <li>{p.verifications}</li>
              <li>{p.retention}</li>
            </ul>
            <Link
              href={p.name === "Self-host" ? "/eu-ai-act" : "/signup"}
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
      <p className="mt-6 text-center text-xs text-muted-foreground">
        Full tier table including Scale ($149) and Enterprise (hosted, contact us) on the{" "}
        <Link href="https://docs.unsearch.dev/strategy/pricing" className="underline underline-offset-2">
          pricing strategy doc
        </Link>
        .
      </p>
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
            Stop rebuilding the same five-vendor duct-tape stack.
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-balance text-muted-foreground">
            One primitive. Signed, snapshotted, replayable. MCP-native. Self-hostable. Apache 2.0.
          </p>
          <div className="mt-7 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="https://docs.unsearch.dev/quickstart#mcp"
              className="inline-flex h-11 items-center rounded-md bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
            >
              <Terminal className="mr-1.5 size-4" />
              Install via MCP
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
            Verifiable web retrieval for AI agents. Apache 2.0, MCP-native, self-hostable on Cloudflare.
          </p>
        </div>
        <FooterCol
          title="Product"
          links={[
            { href: "/#features", label: "How it works" },
            { href: "/#pricing", label: "Pricing" },
            { href: "/eu-ai-act", label: "EU AI Act readiness" },
            { href: "https://docs.unsearch.dev", label: "Docs" },
            { href: "https://status.unsearch.dev", label: "Status" },
          ]}
        />
        <FooterCol
          title="Resources"
          links={[
            { href: "https://github.com/Rakesh1002/unsearch", label: "GitHub" },
            { href: "https://docs.unsearch.dev/citation-envelope", label: "Citation envelope" },
            { href: "https://docs.unsearch.dev/changelog", label: "Changelog" },
            { href: "https://docs.unsearch.dev/migration/from-tavily", label: "Migrate from Tavily" },
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
      <Layers className="size-3.5" strokeWidth={2.5} />
    </span>
  )
}
