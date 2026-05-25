"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import {
  BookOpen,
  CreditCard,
  Home,
  KeyRound,
  LogOut,
  Search,
  Settings,
  TerminalSquare,
  Users,
} from "lucide-react"
import { useEffect, type ReactNode } from "react"

import { cn } from "~/lib/cn"
import { clearSession, getStoredToken } from "~/lib/auth"
import { ThemeToggle } from "~/app/_components/theme-toggle"

const NAV = [
  { href: "/dashboard", label: "Overview", icon: Home },
  { href: "/api-keys", label: "API keys", icon: KeyRound },
  { href: "/playground", label: "Playground", icon: TerminalSquare },
  { href: "/billing", label: "Billing", icon: CreditCard },
  { href: "/team", label: "Team", icon: Users },
  { href: "/settings", label: "Settings", icon: Settings },
] as const

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()

  useEffect(() => {
    if (!getStoredToken()) router.push("/login")
  }, [router])

  function signOut() {
    clearSession()
    router.push("/login")
  }

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border bg-background/80 px-4 backdrop-blur-md">
        <Link href="/" className="flex items-center gap-2 text-sm font-semibold tracking-tight">
          <span className="inline-flex size-6 items-center justify-center rounded-md bg-gradient-to-br from-foreground to-foreground/70 text-background">
            <Search className="size-3.5" strokeWidth={2.5} />
          </span>
          UnSearch
        </Link>
        <div className="hidden flex-1 items-center justify-center md:flex">
          <div className="flex h-8 w-full max-w-md items-center gap-2 rounded-md border border-border bg-muted/40 px-3 text-xs text-muted-foreground">
            <Search className="size-3.5" />
            <span>Search docs, endpoints…</span>
            <span className="ml-auto inline-flex items-center gap-1">
              <kbd className="rounded border border-border bg-background px-1.5 py-0.5 font-mono text-[10px]">⌘K</kbd>
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="https://docs.unsearch.dev"
            className="hidden h-8 items-center gap-1.5 rounded-md px-2 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground sm:inline-flex"
          >
            <BookOpen className="size-3.5" />
            Docs
          </Link>
          <ThemeToggle />
          <button
            onClick={signOut}
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-background px-2.5 text-xs font-medium transition-colors hover:bg-accent"
            aria-label="Sign out"
          >
            <LogOut className="size-3.5" />
            <span className="hidden sm:inline">Sign out</span>
          </button>
        </div>
      </header>

      <div className="flex flex-1">
        <aside className="hidden w-56 shrink-0 border-r border-border md:block">
          <nav className="sticky top-14 space-y-0.5 p-3">
            {NAV.map((item) => {
              const active = pathname === item.href
              const Icon = item.icon
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "group relative flex items-center gap-2.5 rounded-md px-3 py-1.5 text-sm transition-colors",
                    active
                      ? "bg-accent font-medium text-foreground"
                      : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                  )}
                >
                  {active && (
                    <span
                      aria-hidden
                      className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-r bg-foreground"
                    />
                  )}
                  <Icon className="size-4" strokeWidth={active ? 2.25 : 1.75} />
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </aside>

        <main className="flex-1 px-4 py-8 sm:px-8 md:px-10">
          <div className="mx-auto max-w-5xl">{children}</div>
        </main>
      </div>
    </div>
  )
}
