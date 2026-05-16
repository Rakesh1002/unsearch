import type { D1Database, D1Result } from "@cloudflare/workers-types"

export async function d1All<T = Record<string, unknown>>(
  db: D1Database,
  sql: string,
  params: unknown[] = [],
): Promise<T[]> {
  const stmt = params.length > 0 ? db.prepare(sql).bind(...params) : db.prepare(sql)
  const result = await stmt.all<T>()
  return result.results ?? []
}

export async function d1First<T = Record<string, unknown>>(
  db: D1Database,
  sql: string,
  params: unknown[] = [],
): Promise<T | null> {
  const stmt = params.length > 0 ? db.prepare(sql).bind(...params) : db.prepare(sql)
  return (await stmt.first<T>()) ?? null
}

export async function d1Run(
  db: D1Database,
  sql: string,
  params: unknown[] = [],
): Promise<D1Result> {
  const stmt = params.length > 0 ? db.prepare(sql).bind(...params) : db.prepare(sql)
  return stmt.run()
}

export async function d1Batch(
  db: D1Database,
  statements: Array<{ sql: string; params?: unknown[] }>,
): Promise<D1Result[]> {
  const prepared = statements.map((s) =>
    s.params && s.params.length > 0 ? db.prepare(s.sql).bind(...s.params) : db.prepare(s.sql),
  )
  return db.batch(prepared)
}

export function nowIso(): string {
  return new Date().toISOString()
}

export function parseJson<T = unknown>(value: string | null | undefined, fallback: T): T {
  if (!value) return fallback
  try {
    return JSON.parse(value) as T
  } catch {
    return fallback
  }
}
