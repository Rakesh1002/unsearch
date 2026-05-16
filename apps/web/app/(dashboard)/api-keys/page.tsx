"use client"

import { useEffect, useState } from "react"

import { type ApiKey, createApiKey, listApiKeys, revokeApiKey } from "~/lib/api"
import { getStoredToken } from "~/lib/auth"

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState("")
  const [created, setCreated] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function refresh() {
    const token = getStoredToken()
    if (!token) return
    try {
      const resp = await listApiKeys(token)
      setKeys(resp.keys)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load keys")
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  async function onCreate(e: React.FormEvent) {
    e.preventDefault()
    const token = getStoredToken()
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const created = await createApiKey(token, { name })
      setCreated(created.key)
      setName("")
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create key")
    } finally {
      setLoading(false)
    }
  }

  async function onRevoke(id: number) {
    const token = getStoredToken()
    if (!token) return
    await revokeApiKey(token, id)
    await refresh()
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-semibold">API keys</h1>
        <p className="mt-1 text-sm text-[color:var(--color-muted-foreground)]">
          Create scoped keys for your agents. Each key counts toward your plan's quota.
        </p>
      </header>

      <form onSubmit={onCreate} className="flex gap-2">
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. production-agent"
          className="flex-1 rounded-md border bg-[color:var(--color-background)] px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-[color:var(--color-primary)] px-4 py-2 text-sm font-medium text-[color:var(--color-primary-foreground)] disabled:opacity-50"
        >
          {loading ? "Creating…" : "Create key"}
        </button>
      </form>

      {created && (
        <div className="rounded-md border bg-[color:var(--color-accent)] p-4">
          <p className="text-sm font-medium">Save this key now — you won't see it again.</p>
          <code className="mt-2 block break-all rounded bg-[color:var(--color-background)] p-2 text-sm">{created}</code>
          <button onClick={() => setCreated(null)} className="mt-2 text-xs underline">Dismiss</button>
        </div>
      )}

      {error && <p className="text-sm text-[color:var(--color-destructive)]">{error}</p>}

      <table className="w-full text-sm">
        <thead className="border-b text-left text-xs uppercase tracking-wider text-[color:var(--color-muted-foreground)]">
          <tr>
            <th className="py-2">Name</th>
            <th>Created</th>
            <th>Last used</th>
            <th>Calls</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody className="divide-y">
          {keys.length === 0 && (
            <tr><td colSpan={6} className="py-6 text-center text-[color:var(--color-muted-foreground)]">No keys yet.</td></tr>
          )}
          {keys.map((k) => (
            <tr key={k.id}>
              <td className="py-3">{k.name}</td>
              <td>{new Date(k.created_at).toLocaleDateString()}</td>
              <td>{k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "—"}</td>
              <td>{k.request_count.toLocaleString()}</td>
              <td>{k.is_active ? "Active" : "Revoked"}</td>
              <td className="text-right">
                {k.is_active && (
                  <button onClick={() => onRevoke(k.id)} className="text-xs text-[color:var(--color-destructive)] underline">Revoke</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
