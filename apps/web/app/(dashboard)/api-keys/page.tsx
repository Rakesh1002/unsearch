"use client"

import { KeyRound, Plus, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"

import { type ApiKey, createApiKey, listApiKeys, revokeApiKey } from "~/lib/api"
import { getStoredToken } from "~/lib/auth"
import { PageHeader } from "~/app/_components/page-header"
import { CopyButton } from "~/app/_components/copy-button"

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState("")
  const [created, setCreated] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [showCreate, setShowCreate] = useState(false)

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
      const createdKey = await createApiKey(token, { name })
      setCreated(createdKey.key)
      setName("")
      setShowCreate(false)
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
    try {
      await revokeApiKey(token, id)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revoke key")
    }
  }

  return (
    <div className="space-y-8">
      <PageHeader title="API keys" description="Create scoped keys for your agents. Each key counts toward your plan's quota.">
        <button
          onClick={() => setShowCreate((s) => !s)}
          className="inline-flex h-9 items-center rounded-md bg-primary px-3.5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
        >
          <Plus className="mr-1.5 size-3.5" />
          New key
        </button>
      </PageHeader>

      {showCreate && (
        <form
          onSubmit={onCreate}
          className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4 sm:flex-row sm:items-center"
        >
          <input
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. production-agent"
            autoFocus
            className="h-10 flex-1 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                setShowCreate(false)
                setName("")
              }}
              className="inline-flex h-10 items-center rounded-md border border-border bg-background px-3 text-sm transition-colors hover:bg-accent"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
              {loading ? "Creating…" : "Create key"}
            </button>
          </div>
        </form>
      )}

      {created && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-5">
          <p className="text-sm font-semibold">Save this key now — you won&apos;t see it again.</p>
          <div className="mt-3 flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2">
            <code className="flex-1 truncate font-mono text-sm">{created}</code>
            <CopyButton value={created} />
          </div>
          <button
            onClick={() => setCreated(null)}
            className="mt-3 text-xs font-medium text-muted-foreground underline-offset-4 hover:underline"
          >
            Dismiss
          </button>
        </div>
      )}

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {keys.length === 0 ? (
        <EmptyState onCreate={() => setShowCreate(true)} />
      ) : (
        <div className="overflow-hidden rounded-xl border border-border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b border-border bg-muted/30 text-left text-xs font-medium tracking-wide text-muted-foreground uppercase">
              <tr>
                <th className="px-5 py-3">Name</th>
                <th className="px-5 py-3">Created</th>
                <th className="px-5 py-3">Last used</th>
                <th className="px-5 py-3 text-right">Calls</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {keys.map((k) => (
                <tr key={k.id} className="transition-colors hover:bg-muted/30">
                  <td className="px-5 py-3 font-medium">{k.name}</td>
                  <td className="px-5 py-3 text-muted-foreground">{new Date(k.created_at).toLocaleDateString()}</td>
                  <td className="px-5 py-3 text-muted-foreground">
                    {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "—"}
                  </td>
                  <td className="px-5 py-3 text-right font-mono text-muted-foreground">
                    {k.request_count.toLocaleString()}
                  </td>
                  <td className="px-5 py-3">
                    <span
                      className={
                        k.is_active
                          ? "inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-600 dark:text-emerald-400"
                          : "inline-flex items-center gap-1.5 rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground"
                      }
                    >
                      <span
                        className={`size-1.5 rounded-full ${k.is_active ? "bg-emerald-500" : "bg-muted-foreground"}`}
                      />
                      {k.is_active ? "Active" : "Revoked"}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right">
                    {k.is_active && (
                      <button
                        onClick={() => onRevoke(k.id)}
                        className="inline-flex items-center gap-1 text-xs font-medium text-destructive transition-colors hover:underline"
                      >
                        <Trash2 className="size-3.5" />
                        Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-card px-6 py-16 text-center">
      <div className="inline-flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <KeyRound className="size-5" />
      </div>
      <h3 className="mt-4 text-base font-semibold">No API keys yet</h3>
      <p className="mt-1 max-w-xs text-sm text-muted-foreground">
        Create your first key to start making search requests.
      </p>
      <button
        onClick={onCreate}
        className="mt-5 inline-flex h-9 items-center rounded-md bg-primary px-3.5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
      >
        <Plus className="mr-1.5 size-3.5" />
        Create first key
      </button>
    </div>
  )
}
