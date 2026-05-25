"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { Search } from "lucide-react"
import { useState } from "react"

import { login } from "~/lib/api"
import { setStoredSession } from "~/lib/auth"
import { AuthField } from "~/app/_components/auth-field"

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const resp = await login({ email, password })
      setStoredSession({ token: resp.token, plan: resp.plan, userId: resp.user_id })
      router.push("/dashboard")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center px-4">
      <div className="dotted-grid pointer-events-none absolute inset-0 -z-10 opacity-50" aria-hidden />
      <div className="w-full max-w-sm">
        <Link href="/" className="mb-8 flex items-center justify-center gap-2 text-base font-semibold tracking-tight">
          <span className="inline-flex size-7 items-center justify-center rounded-md bg-gradient-to-br from-foreground to-foreground/70 text-background">
            <Search className="size-4" strokeWidth={2.5} />
          </span>
          UnSearch
        </Link>
        <div className="rounded-xl border border-border bg-card p-7 shadow-sm">
          <h1 className="text-xl font-semibold tracking-tight">Welcome back</h1>
          <p className="mt-1 text-sm text-muted-foreground">Sign in to your UnSearch account.</p>
          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <AuthField id="email" label="Email" type="email" value={email} onChange={setEmail} autoComplete="email" />
            <AuthField
              id="password"
              label="Password"
              type="password"
              value={password}
              onChange={setPassword}
              autoComplete="current-password"
            />
            {error && (
              <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={loading}
              className="inline-flex h-10 w-full items-center justify-center rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>
        <p className="mt-6 text-center text-sm text-muted-foreground">
          Don&apos;t have an account?{" "}
          <Link href="/signup" className="font-medium text-foreground underline-offset-4 hover:underline">
            Sign up
          </Link>
        </p>
      </div>
    </main>
  )
}
