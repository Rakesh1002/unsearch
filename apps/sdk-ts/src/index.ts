/**
 * @unsearch/sdk — TypeScript client for the UnSearch API.
 *
 * Works in any modern JS runtime: Node ≥18, Bun, Deno, browsers,
 * Cloudflare Workers, Vercel Edge.
 *
 * @example
 * ```ts
 * import { UnSearch } from "@unsearch/sdk"
 * const client = new UnSearch({ apiKey: process.env.UNSEARCH_API_KEY! })
 * const results = await client.search({ query: "AI agents in 2026" })
 * ```
 */

export interface UnSearchClientOptions {
  apiKey: string
  baseUrl?: string
  timeoutMs?: number
  fetch?: typeof fetch
}

export interface SearchRequest {
  query: string
  engines?: string[]
  max_results?: number
  language?: string
  safe_search?: "off" | "moderate" | "strict"
  scrape_content?: boolean
  use_cache?: boolean
}

export interface CitationEnvelope {
  v: number
  url: string
  fetched_at: string
  content_sha256: string
  content_type: string
  content_bytes: number
  snapshot_key: string
  engine: string
  agent_run_id?: string
  api_key_id?: string
  signed_at: string
  signing_key_id?: string
  signing_alg: string
  signature: string
}

export interface SearchResult {
  rank: number
  title: string
  url: string
  snippet: string
  engine: string
  score: number | null
  scraped_content?: { text: string; html?: string; citation_envelope?: CitationEnvelope } | null
  citation_envelope?: CitationEnvelope
}

export interface ExtractRequest {
  urls: string[]
  include_images?: boolean
  extract_depth?: "basic" | "advanced"
}

export interface ExtractedContentResult {
  url: string
  raw_content: string
  images?: string[]
  failed: boolean
  error?: string
  citation_envelope?: CitationEnvelope
}

export interface ExtractResponse {
  results: ExtractedContentResult[]
  failed_urls: string[]
  response_time: number
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
  response_time_ms: number
  cache_hit: boolean
  request_id?: string
}

export interface NeuralSearchRequest {
  query: string
  top_k?: number
  use_autoprompt?: boolean
  category?: string
  namespace?: string
}

export interface VectorMatch {
  id: string
  score: number
  metadata?: Record<string, unknown>
}

export interface NeuralSearchResponse {
  query: string
  expanded_from?: string
  matches: VectorMatch[]
}

export interface RagQueryRequest {
  query: string
  namespace?: string
  top_k?: number
  model_tier?: "fast" | "balanced" | "reasoning"
}

export interface RagQueryResponse {
  query: string
  answer: string
  sources: VectorMatch[]
}

export interface ResearchSession {
  session_id: string
  status: "running" | "completed" | "failed"
  steps: Array<{ step: number; query: string; reasoning: string; results: SearchResult[]; finishedAt: number }>
  finalAnswer?: string
}

export class UnSearchError extends Error {
  constructor(message: string, public status: number, public body?: unknown) {
    super(message)
    this.name = "UnSearchError"
  }
}

export class UnSearch {
  private apiKey: string
  private baseUrl: string
  private timeoutMs: number
  private fetcher: typeof fetch

  constructor(opts: UnSearchClientOptions) {
    if (!opts.apiKey) throw new Error("UnSearch: apiKey is required")
    this.apiKey = opts.apiKey
    this.baseUrl = (opts.baseUrl ?? "https://api.unsearch.dev").replace(/\/$/, "")
    this.timeoutMs = opts.timeoutMs ?? 60_000
    this.fetcher = opts.fetch ?? fetch
  }

  // ----- Search -----

  search(req: SearchRequest): Promise<SearchResponse> {
    return this.request<SearchResponse>("POST", "/api/v1/search", req)
  }

  async *streamSearch(req: SearchRequest): AsyncIterable<{ event: string; data: string }> {
    const resp = await this.fetcher(`${this.baseUrl}/api/v1/search/stream`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify(req),
    })
    if (!resp.ok || !resp.body) throw await this.toError(resp)
    yield* parseSSE(resp.body)
  }

  // ----- Neural -----

  neuralSearch(req: NeuralSearchRequest): Promise<NeuralSearchResponse> {
    return this.request("POST", "/api/v1/neural/search", req)
  }

  similar(req: { url?: string; text?: string; top_k?: number }) {
    return this.request<{ matches: VectorMatch[] }>("POST", "/api/v1/neural/similar", req)
  }

  highlights(req: { query: string; document: string; num_highlights?: number }) {
    return this.request<{ highlights: Array<{ text: string; relevance: number }> }>(
      "POST",
      "/api/v1/neural/highlights",
      req,
    )
  }

  // ----- RAG -----

  ragQuery(req: RagQueryRequest): Promise<RagQueryResponse> {
    return this.request("POST", "/api/v1/rag/query", req)
  }

  async *streamRag(req: RagQueryRequest): AsyncIterable<{ event: string; data: string }> {
    const resp = await this.fetcher(`${this.baseUrl}/api/v1/rag/query`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ ...req, stream: true }),
    })
    if (!resp.ok || !resp.body) throw await this.toError(resp)
    yield* parseSSE(resp.body)
  }

  ingest(req: {
    namespace?: string
    documents: Array<{ id?: string; text: string; metadata?: Record<string, unknown> }>
  }) {
    return this.request<{ ingested: number; mutation_id: string; namespace: string }>(
      "POST",
      "/api/v1/rag/ingest",
      req,
    )
  }

  // ----- Research agent -----

  startResearch(req: { query: string; depth?: number }): Promise<{ session_id: string; status: string }> {
    return this.request("POST", "/api/v1/agent/research", req)
  }

  async research(req: {
    query: string
    depth?: "quick" | "standard" | "deep" | "comprehensive"
    max_sources?: number
    include_analysis?: boolean
    include_summary?: boolean
  }): Promise<ResearchSession> {
    const depthMap: Record<string, number> = { quick: 1, standard: 2, deep: 3, comprehensive: 4 }
    const { session_id } = await this.startResearch({
      query: req.query,
      depth: req.depth ? depthMap[req.depth] ?? 2 : undefined,
    })
    return this.pollResearch(session_id)
  }

  getResearch(sessionId: string): Promise<ResearchSession> {
    return this.request("GET", `/api/v1/agent/research/${encodeURIComponent(sessionId)}`)
  }

  async pollResearch(
    sessionId: string,
    opts: { intervalMs?: number; timeoutMs?: number } = {},
  ): Promise<ResearchSession> {
    const interval = opts.intervalMs ?? 1500
    const timeout = opts.timeoutMs ?? 120_000
    const start = Date.now()
    while (true) {
      const session = await this.getResearch(sessionId)
      if (session.status !== "running") return session
      if (Date.now() - start > timeout) throw new UnSearchError("Research polling timed out", 408)
      await new Promise((r) => setTimeout(r, interval))
    }
  }

  // ----- Extract -----

  extract(req: ExtractRequest): Promise<ExtractResponse> {
    return this.request<ExtractResponse>("POST", "/api/v1/agent/extract", req)
  }

  // ----- Verify -----

  verifyClaim(req: { claim: string; source_url?: string; depth?: "quick" | "thorough" }) {
    return this.request<Record<string, unknown>>("POST", "/api/v1/verify/claim", req)
  }

  verifySource(url: string) {
    return this.request<Record<string, unknown>>("POST", "/api/v1/verify/source", { url })
  }

  verifyCitation(req: { url: string; snapshot_key?: string; content_sha256?: string; include_live_content?: boolean }) {
    return this.request<Record<string, unknown>>("POST", "/api/v1/verify/citation", req)
  }

  // ----- Audit -----

  audit(params?: { start_date?: string; end_date?: string; limit?: number; offset?: number }) {
    const qs = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : ""
    return this.request<Record<string, unknown>>("GET", `/api/v1/audit${qs}`)
  }

  // ----- Topic monitoring -----

  createMonitor(req: {
    topic: string
    query: string
    interval_minutes?: number
    webhook_url?: string
  }) {
    return this.request<{ monitor_id: string }>("POST", "/api/v1/monitor/topics", req)
  }

  // ----- Tavily-compatible drop-in -----

  tavilySearch(req: SearchRequest & { include_answer?: boolean }) {
    return this.request("POST", "/api/v1/agent/search", req)
  }

  // ----- Internals -----

  private headers(): Record<string, string> {
    return {
      "X-API-Key": this.apiKey,
      "Content-Type": "application/json",
      "User-Agent": "@unsearch/sdk-ts/0.1.0",
    }
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), this.timeoutMs)
    try {
      const resp = await this.fetcher(`${this.baseUrl}${path}`, {
        method,
        headers: this.headers(),
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: ctrl.signal,
      })
      if (!resp.ok) throw await this.toError(resp)
      if (resp.status === 204) return undefined as T
      return (await resp.json()) as T
    } finally {
      clearTimeout(timer)
    }
  }

  private async toError(resp: Response): Promise<UnSearchError> {
    let body: unknown = undefined
    try { body = await resp.json() } catch { /* ignore */ }
    return new UnSearchError(`UnSearch ${resp.status}: ${resp.statusText}`, resp.status, body)
  }
}

/**
 * Verify a citation envelope's HMAC-SHA256 signature.
 *
 * Works in Node.js, Cloudflare Workers, Deno, Bun, and modern browsers.
 * Returns true if the signature is valid for the given signing key.
 */
export async function verifyEnvelope(
  envelope: CitationEnvelope,
  signingKey: string,
): Promise<boolean> {
  const payload: Record<string, unknown> = {
    v: envelope.v,
    url: envelope.url,
    fetched_at: envelope.fetched_at,
    content_sha256: envelope.content_sha256,
    content_type: envelope.content_type,
    content_bytes: envelope.content_bytes,
    snapshot_key: envelope.snapshot_key,
    engine: envelope.engine,
    agent_run_id: envelope.agent_run_id,
    api_key_id: envelope.api_key_id,
    signed_at: envelope.signed_at,
    signing_key_id: envelope.signing_key_id,
    signing_alg: envelope.signing_alg,
  }
  Object.keys(payload).forEach((key) => {
    if (payload[key] === undefined) delete payload[key]
  })
  const canonical = JSON.stringify(payload, Object.keys(payload).sort(), 0)

  // Prefer Web Crypto (available in Workers, Deno, Bun, browser, Node >=20).
  const subtle =
    (typeof globalThis !== "undefined" && (globalThis as any).crypto?.subtle) ||
    (typeof crypto !== "undefined" && (crypto as any).subtle)

  if (subtle) {
    const encoder = new TextEncoder()
    const keyData = encoder.encode(signingKey)
    const cryptoKey = await subtle.importKey(
      "raw",
      keyData,
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["sign"],
    )
    const sig = await subtle.sign("HMAC", cryptoKey, encoder.encode(canonical))
    const computed = Array.from(new Uint8Array(sig))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("")
    return timingSafeEqual(computed, envelope.signature)
  }

  // Fallback to Node.js crypto for older Node versions.
  try {
    const { createHmac } = await import("node:crypto")
    const computed = createHmac("sha256", signingKey).update(canonical).digest("hex")
    return timingSafeEqual(computed, envelope.signature)
  } catch {
    throw new Error("No HMAC implementation available. Provide a Web Crypto or Node crypto environment.")
  }
}

function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  let result = 0
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i)
  }
  return result === 0
}

async function* parseSSE(body: ReadableStream<Uint8Array>): AsyncIterable<{ event: string; data: string }> {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const events = buffer.split("\n\n")
    buffer = events.pop() ?? ""
    for (const block of events) {
      const lines = block.split("\n")
      let event = "message"
      let data = ""
      for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim()
        else if (line.startsWith("data:")) data += line.slice(5).trimStart()
      }
      if (data) yield { event, data }
    }
  }
}
