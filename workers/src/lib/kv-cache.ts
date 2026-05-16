import type { KVNamespace } from "@cloudflare/workers-types"

export interface CacheOptions {
  ttlSeconds?: number
  staleWhileRevalidate?: boolean
}

interface CacheEnvelope<T> {
  v: T
  exp: number
}

export async function kvGet<T>(kv: KVNamespace, key: string): Promise<T | null> {
  const envelope = await kv.get<CacheEnvelope<T>>(key, "json")
  if (!envelope) return null
  if (envelope.exp < Date.now()) return null
  return envelope.v
}

export async function kvSet<T>(
  kv: KVNamespace,
  key: string,
  value: T,
  opts: CacheOptions = {},
): Promise<void> {
  const ttl = opts.ttlSeconds ?? 300
  const envelope: CacheEnvelope<T> = {
    v: value,
    exp: Date.now() + ttl * 1000,
  }
  await kv.put(key, JSON.stringify(envelope), { expirationTtl: ttl })
}

export async function kvGetOrCompute<T>(
  kv: KVNamespace,
  key: string,
  compute: () => Promise<T>,
  opts: CacheOptions = {},
): Promise<T> {
  const cached = await kvGet<T>(kv, key)
  if (cached !== null) return cached
  const fresh = await compute()
  await kvSet(kv, key, fresh, opts)
  return fresh
}

export function hashKey(input: string): Promise<string> {
  return crypto.subtle.digest("SHA-256", new TextEncoder().encode(input)).then((buf) =>
    Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join(""),
  )
}
