"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import { useEffect, type ReactNode } from "react"

import { clearSession, getStoredToken } from "~/lib/auth"

const NAV = [
  { href: "/dashboard", label: "Overview" },
  { href: "/api-keys", label: "API keys" },
  { href: "/playground", label: "Playground" },
  { href: "/billing", label: "Billing" },
  { href: "/team", label: "Team" },
  { href: "/settings", label: "Settings" },
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
    <div className="flex min-h-screen">
      <aside className="w-56 border-r p-4">
        <Link href="/" className="block px-2 py-2 text-base font-semibold">UnSearch</Link>
        <nav className="mt-4 space-y-1">
          {NAV.map((item) => {
            const active = pathname === item.href
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`block rounded-md px-3 py-2 text-sm ${active ? "bg-[color:var(--color-accent)] font-medium" : "text-[color:var(--color-muted-foreground)] hover:bg-[color:var(--color-accent)]"}`}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>
        <button
          onClick={signOut}
          className="mt-8 w-full rounded-md border px-3 py-2 text-sm hover:bg-[color:var(--color-accent)]"
        >
          Sign out
        </button>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  )
}
