import Link from "next/link"

export default function LandingPage() {
  return (
    <main className="min-h-screen">
      <Header />
      <Hero />
      <Features />
      <Pricing />
      <Footer />
    </main>
  )
}

function Header() {
  return (
    <header className="border-b">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="text-base font-semibold tracking-tight">UnSearch</Link>
        <nav className="flex items-center gap-6 text-sm">
          <Link href="https://docs.unsearch.dev" className="text-[color:var(--color-muted-foreground)] hover:text-[color:var(--color-foreground)]">Docs</Link>
          <Link href="/#pricing" className="text-[color:var(--color-muted-foreground)] hover:text-[color:var(--color-foreground)]">Pricing</Link>
          <Link href="https://github.com/Rakesh1002/unsearch" className="text-[color:var(--color-muted-foreground)] hover:text-[color:var(--color-foreground)]">GitHub</Link>
          <Link href="/login" className="text-[color:var(--color-muted-foreground)] hover:text-[color:var(--color-foreground)]">Sign in</Link>
          <Link href="/signup" className="rounded-md bg-[color:var(--color-primary)] px-3 py-1.5 text-[color:var(--color-primary-foreground)] hover:opacity-90">Get started</Link>
        </nav>
      </div>
    </header>
  )
}

function Hero() {
  return (
    <section className="mx-auto flex max-w-4xl flex-col items-center px-4 py-24 text-center">
      <h1 className="text-balance text-5xl font-semibold tracking-tight sm:text-6xl">
        Search built for AI agents.
      </h1>
      <p className="mt-6 max-w-2xl text-lg text-[color:var(--color-muted-foreground)]">
        Real-time web search across 70+ engines, neural search, fact verification, and deep-research agents.
        Drop-in replacement for Tavily and Exa. Open source, edge-native, deployed on Cloudflare.
      </p>
      <div className="mt-10 flex gap-3">
        <Link href="/signup" className="rounded-md bg-[color:var(--color-primary)] px-5 py-2.5 text-sm font-medium text-[color:var(--color-primary-foreground)] hover:opacity-90">Start for free</Link>
        <Link href="https://docs.unsearch.dev" className="rounded-md border px-5 py-2.5 text-sm font-medium hover:bg-[color:var(--color-accent)]">Read the docs</Link>
      </div>
      <pre className="mt-12 w-full max-w-2xl overflow-x-auto rounded-lg border bg-[color:var(--color-muted)] p-4 text-left text-sm">
{`curl https://api.unsearch.dev/api/v1/search \\
  -H "X-API-Key: $UNSEARCH_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "Cloudflare Workers in 2026"}'`}
      </pre>
    </section>
  )
}

function Features() {
  const features = [
    { title: "70+ search engines", body: "SearXNG-powered aggregation with sane defaults and per-engine routing." },
    { title: "Neural search", body: "Semantic search via Workers AI + Vectorize. Auto-prompting, highlights, similar." },
    { title: "Deep research", body: "Multi-step research agents backed by Durable Objects." },
    { title: "Fact verification", body: "Claim checks, source credibility scoring, batch verification." },
    { title: "Tavily / Exa drop-in", body: "API compatibility with both — change the base URL, keep your code." },
    { title: "Edge-native", body: "Runs on Cloudflare Workers + Containers. <50ms p95 from anywhere." },
  ]
  return (
    <section id="features" className="mx-auto max-w-6xl px-4 py-20">
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {features.map((f) => (
          <div key={f.title} className="rounded-lg border p-6">
            <h3 className="text-base font-semibold">{f.title}</h3>
            <p className="mt-2 text-sm text-[color:var(--color-muted-foreground)]">{f.body}</p>
          </div>
        ))}
      </div>
    </section>
  )
}

function Pricing() {
  const plans = [
    { name: "Free", price: "$0", queries: "5,000 / mo", cta: "Start free" },
    { name: "Pro", price: "$19", queries: "25,000 / mo", cta: "Upgrade" },
    { name: "Growth", price: "$49", queries: "100,000 / mo", cta: "Upgrade", highlight: true },
    { name: "Scale", price: "$149", queries: "500,000 / mo", cta: "Talk to sales" },
  ]
  return (
    <section id="pricing" className="mx-auto max-w-6xl px-4 py-20">
      <h2 className="text-center text-3xl font-semibold tracking-tight">Pricing</h2>
      <p className="mt-2 text-center text-[color:var(--color-muted-foreground)]">5x more free queries than competitors. Self-host for unlimited.</p>
      <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {plans.map((p) => (
          <div key={p.name} className={`rounded-lg border p-6 ${p.highlight ? "ring-2 ring-[color:var(--color-primary)]" : ""}`}>
            <h3 className="text-base font-semibold">{p.name}</h3>
            <div className="mt-4 text-3xl font-semibold">{p.price}<span className="text-sm font-normal text-[color:var(--color-muted-foreground)]">/mo</span></div>
            <p className="mt-2 text-sm text-[color:var(--color-muted-foreground)]">{p.queries}</p>
            <Link href="/signup" className="mt-6 block rounded-md bg-[color:var(--color-primary)] px-3 py-2 text-center text-sm text-[color:var(--color-primary-foreground)] hover:opacity-90">{p.cta}</Link>
          </div>
        ))}
      </div>
    </section>
  )
}

function Footer() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-8 text-sm text-[color:var(--color-muted-foreground)]">
        <span>© {new Date().getFullYear()} UnSearch. Apache-2.0.</span>
        <div className="flex gap-4">
          <Link href="https://github.com/Rakesh1002/unsearch">GitHub</Link>
          <Link href="https://docs.unsearch.dev">Docs</Link>
          <Link href="mailto:support@unsearch.dev">Support</Link>
        </div>
      </div>
    </footer>
  )
}
