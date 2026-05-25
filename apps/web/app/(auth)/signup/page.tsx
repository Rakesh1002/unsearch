"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { Search } from "lucide-react"
import { useState } from "react"

import { signup } from "~/lib/api"
import { setStoredSession } from "~/lib/auth"
import { AuthField } from "~/app/_components/auth-field"

export default function SignupPage() {
  const router = useRouter()
  const [form, setForm] = useState({ email: "", password: "", full_name: "", company: "" })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const resp = await signup(form)
      setStoredSession({ token: resp.token, plan: resp.plan, userId: resp.user_id })
      router.push("/dashboard")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Signup failed")
    } finally {
      setLoading(false)
    }
  }

  function setField<K extends keyof typeof form>(key: K) {
    return (v: string) => setForm({ ...form, [key]: v })
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center px-4 py-12">
      <div className="dotted-grid pointer-events-none absolute inset-0 -z-10 opacity-50" aria-hidden />
      <div className="w-full max-w-sm">
        <Link href="/" className="mb-8 flex items-center justify-center gap-2 text-base font-semibold tracking-tight">
          <span className="inline-flex size-7 items-center justify-center rounded-md bg-gradient-to-br from-foreground to-foreground/70 text-background">
            <Search className="size-4" strokeWidth={2.5} />
          </span>
          UnSearch
        </Link>
        <div className="rounded-xl border border-border bg-card p-7 shadow-sm">
          <h1 className="text-xl font-semibold tracking-tight">Create your account</h1>
          <p className="mt-1 text-sm text-muted-foreground">5,000 free queries every month — no credit card required.</p>
          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <AuthField id="full_name" label="Full name" value={form.full_name} onChange={setField("full_name")} autoComplete="name" />
            <AuthField
              id="company"
              label="Company"
              hint="optional"
              required={false}
              value={form.company}
              onChange={setField("company")}
              autoComplete="organization"
            />
            <AuthField
              id="email"
              label="Work email"
              type="email"
              value={form.email}
              onChange={setField("email")}
              autoComplete="email"
            />
            <AuthField
              id="password"
              label="Password"
              type="password"
              value={form.password}
              onChange={setField("password")}
              autoComplete="new-password"
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
              {loading ? "Creating account…" : "Create account"}
            </button>
            <p className="text-center text-xs text-muted-foreground">
              By signing up you agree to our{" "}
              <Link href="https://docs.unsearch.dev/terms" className="underline-offset-2 hover:underline">
                Terms
              </Link>{" "}
              and{" "}
              <Link href="https://docs.unsearch.dev/privacy" className="underline-offset-2 hover:underline">
                Privacy Policy
              </Link>
              .
            </p>
          </form>
        </div>
        <p className="mt-6 text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-foreground underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  )
}
