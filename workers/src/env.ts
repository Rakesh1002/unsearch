import type {
  Ai,
  AnalyticsEngineDataset,
  D1Database,
  DurableObjectNamespace,
  KVNamespace,
  Queue,
  R2Bucket,
  Vectorize,
} from "@cloudflare/workers-types"

/**
 * Service binding shape — duck-typed to avoid Request type collisions
 * between workers-types and the global lib used by Hono.
 */
export interface ServiceBinding {
  fetch(input: Request | string, init?: RequestInit): Promise<Response>
}

export interface Env {
  // ----- Resource bindings -----
  AI: Ai
  DB: D1Database
  CACHE: KVNamespace
  RATE_LIMIT: KVNamespace
  SESSIONS: KVNamespace
  API_KEYS: KVNamespace
  STORAGE: R2Bucket
  VECTORS: Vectorize
  TASK_QUEUE: Queue<TaskMessage>
  ANALYTICS: AnalyticsEngineDataset
  CONTAINER?: ServiceBinding

  // ----- Durable Object namespaces -----
  RESEARCH_AGENT: DurableObjectNamespace
  TOPIC_MONITOR: DurableObjectNamespace
  SESSION_MANAGER: DurableObjectNamespace
  RATE_LIMITER: DurableObjectNamespace

  // ----- Vars (non-secret) -----
  ENVIRONMENT: "development" | "staging" | "production"
  APP_NAME: string
  API_VERSION: string
  CLOUDFLARE_LLM_MODEL: string
  CLOUDFLARE_REASONING_MODEL: string
  CLOUDFLARE_EMBEDDING_MODEL: string
  CLOUDFLARE_RERANKER_MODEL: string
  CLOUDFLARE_SAFETY_MODEL: string
  FRONTEND_URL: string
  EMAIL_FROM: string
  EMAIL_REPLY_TO: string

  // ----- Secrets (bound via `wrangler secret put`) -----
  SECRET_KEY: string
  CLOUDFLARE_ACCOUNT_ID: string
  CLOUDFLARE_API_TOKEN: string
  STRIPE_SECRET_KEY: string
  STRIPE_PUBLISHABLE_KEY: string
  STRIPE_WEBHOOK_SECRET: string
  STRIPE_PRO_PRODUCT_ID?: string
  STRIPE_PRO_MONTHLY_PRICE_ID?: string
  STRIPE_PRO_YEARLY_PRICE_ID?: string
  STRIPE_GROWTH_PRODUCT_ID?: string
  STRIPE_GROWTH_MONTHLY_PRICE_ID?: string
  STRIPE_GROWTH_YEARLY_PRICE_ID?: string
  STRIPE_SCALE_PRODUCT_ID?: string
  STRIPE_SCALE_MONTHLY_PRICE_ID?: string
  STRIPE_SCALE_YEARLY_PRICE_ID?: string
  RESEND_API_KEY: string
  GOOGLE_CLIENT_ID?: string
  GOOGLE_CLIENT_SECRET?: string
  GITHUB_CLIENT_ID?: string
  GITHUB_CLIENT_SECRET?: string
  SENTRY_DSN?: string
  POSTHOG_API_KEY?: string
  POSTHOG_HOST?: string
  SERPER_API_KEY?: string
  SEARCHAPI_KEY?: string
  GOOGLE_CSE_API_KEY?: string
  GOOGLE_CSE_CX?: string
  OPENAI_API_KEY?: string
  SEARXNG_SECRET_KEY: string
}

export type TaskMessage =
  | { type: "scrape"; jobId: string; urls: string[]; config: Record<string, unknown> }
  | { type: "research"; sessionId: string; query: string; depth: number }
  | { type: "embed"; documents: Array<{ id: string; text: string; metadata?: Record<string, unknown> }> }
  | { type: "monitor.check"; monitorId: string }
  | { type: "webhook.deliver"; url: string; payload: unknown; attempt: number }

export interface AuthContext {
  userId: number
  apiKeyId: number | null
  planType: "FREE" | "PRO" | "GROWTH" | "SCALE" | "ENTERPRISE"
  rateLimit: string
  scopes: string[]
}

export type Variables = {
  auth: AuthContext
  requestId: string
}
