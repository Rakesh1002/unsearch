/**
 * Typed UnSearch API client used by the dashboard.
 * In production hits api.unsearch.dev directly; in dev the Next.js
 * rewrite in next.config.ts proxies /api/v1/* to the local Worker.
 */
const BASE = process.env.NEXT_PUBLIC_API_URL ?? ""

export class UnSearchError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: unknown,
  ) {
    super(message)
  }
}

export interface RequestInitWithAuth extends RequestInit {
  token?: string
  apiKey?: string
}

async function request<T>(path: string, init: RequestInitWithAuth = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json")
  if (init.token) headers.set("Authorization", `Bearer ${init.token}`)
  if (init.apiKey) headers.set("X-API-Key", init.apiKey)

  const resp = await fetch(`${BASE}${path}`, { ...init, headers })
  if (!resp.ok) {
    let body: unknown
    try { body = await resp.json() } catch { /* ignore */ }
    throw new UnSearchError(`${resp.status} ${resp.statusText}`, resp.status, body)
  }
  if (resp.status === 204) return undefined as T
  return resp.json() as Promise<T>
}

// ----- Auth -----

export interface SignupResponse { user_id: number; uuid: string; email: string; token: string; plan: string }
export const signup = (body: { email: string; password: string; full_name?: string; company?: string }) =>
  request<SignupResponse>("/api/v1/auth/signup", { method: "POST", body: JSON.stringify(body) })

export interface LoginResponse { user_id: number; token: string; plan: string; verified: boolean }
export const login = (body: { email: string; password: string }) =>
  request<LoginResponse>("/api/v1/auth/login", { method: "POST", body: JSON.stringify(body) })

export const me = (token: string) =>
  request<{ user: Record<string, unknown>; plan: string; rate_limit: string }>(
    "/api/v1/auth/me",
    { token },
  )

// ----- API keys -----

export interface ApiKey {
  id: number
  name: string
  description?: string
  scopes: string[]
  last_used_at: string | null
  request_count: number
  is_active: boolean
  expires_at: string | null
  created_at: string
}

export const listApiKeys = (token: string) =>
  request<{ keys: ApiKey[] }>("/api/v1/auth/keys", { token })

export const createApiKey = (
  token: string,
  body: { name: string; description?: string; scopes?: string[]; expires_in_days?: number },
) => request<ApiKey & { key: string }>("/api/v1/auth/keys", {
  method: "POST",
  token,
  body: JSON.stringify(body),
})

export const revokeApiKey = (token: string, id: number) =>
  request<{ revoked: boolean }>(`/api/v1/auth/keys/${id}`, { method: "DELETE", token })

// ----- Search (for the playground) -----

export interface SearchResult {
  rank: number
  title: string
  url: string
  snippet: string
  engine: string
  score: number | null
}

export const search = (
  apiKey: string,
  body: { query: string; engines?: string[]; max_results?: number; scrape_content?: boolean },
) =>
  request<{ query: string; results: SearchResult[]; response_time_ms: number; cache_hit: boolean }>(
    "/api/v1/search",
    { method: "POST", apiKey, body: JSON.stringify(body) },
  )

// ----- Billing -----

export const createCheckout = (token: string, body: { plan: "pro" | "growth" | "scale"; interval?: "monthly" | "yearly" }) =>
  request<{ checkout_url: string; session_id: string }>("/api/v1/billing/checkout", {
    method: "POST",
    token,
    body: JSON.stringify(body),
  })

export const createPortal = (token: string) =>
  request<{ portal_url: string }>("/api/v1/billing/portal", { method: "POST", token })

export const getUsage = (token: string) =>
  request<{ plan: string; current_period: Record<string, unknown> | null }>(
    "/api/v1/billing/usage",
    { token },
  )
