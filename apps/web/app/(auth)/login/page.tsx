"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"

import { login } from "~/lib/api"
import { setStoredSession } from "~/lib/auth"

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
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold">Sign in to UnSearch</h1>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <Field label="Email" type="email" value={email} onChange={setEmail} />
          <Field label="Password" type="password" value={password} onChange={setPassword} />
          {error && <p className="text-sm text-[color:var(--color-destructive)]">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-[color:var(--color-primary)] px-3 py-2 text-sm font-medium text-[color:var(--color-primary-foreground)] disabled:opacity-50"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-[color:var(--color-muted-foreground)]">
          Don't have an account? <Link href="/signup" className="underline">Sign up</Link>
        </p>
      </div>
    </main>
  )
}

function Field({ label, type, value, onChange }: { label: string; type: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="block">
      <span className="text-sm font-medium">{label}</span>
      <input
        type={type}
        required
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border bg-[color:var(--color-background)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
      />
    </label>
  )
}
