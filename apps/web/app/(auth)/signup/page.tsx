"use client"

import Link from "next/link"
import { useRouter } from "next/navigation"
import { useState } from "react"

import { signup } from "~/lib/api"
import { setStoredSession } from "~/lib/auth"

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
    <main className="flex min-h-screen items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold">Create your UnSearch account</h1>
        <p className="mt-1 text-sm text-[color:var(--color-muted-foreground)]">5,000 free queries every month — no credit card.</p>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <Field label="Full name" value={form.full_name} onChange={setField("full_name")} />
          <Field label="Company (optional)" value={form.company} onChange={setField("company")} required={false} />
          <Field label="Work email" type="email" value={form.email} onChange={setField("email")} />
          <Field label="Password" type="password" value={form.password} onChange={setField("password")} />
          {error && <p className="text-sm text-[color:var(--color-destructive)]">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-md bg-[color:var(--color-primary)] px-3 py-2 text-sm font-medium text-[color:var(--color-primary-foreground)] disabled:opacity-50"
          >
            {loading ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-[color:var(--color-muted-foreground)]">
          Already have an account? <Link href="/login" className="underline">Sign in</Link>
        </p>
      </div>
    </main>
  )
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required = true,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  type?: string
  required?: boolean
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium">{label}</span>
      <input
        type={type}
        required={required}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 w-full rounded-md border bg-[color:var(--color-background)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[color:var(--color-primary)]"
      />
    </label>
  )
}
