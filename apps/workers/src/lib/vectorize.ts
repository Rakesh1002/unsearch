import type { Vectorize } from "@cloudflare/workers-types"

export interface VectorDoc {
  id: string
  values: number[]
  metadata?: Record<string, unknown>
  namespace?: string
}

export interface VectorMatch {
  id: string
  score: number
  metadata?: Record<string, unknown>
}

export async function upsertVectors(
  index: Vectorize,
  docs: VectorDoc[],
): Promise<{ count: number; mutationId: string }> {
  const result = await index.upsert(
    docs.map((d) => ({
      id: d.id,
      values: d.values,
      metadata: d.metadata,
      namespace: d.namespace,
    })) as unknown as Parameters<Vectorize["upsert"]>[0],
  )
  return { count: docs.length, mutationId: result.mutationId }
}

export async function searchVectors(
  index: Vectorize,
  queryVector: number[],
  opts: {
    topK?: number
    namespace?: string
    filter?: Record<string, unknown>
    returnMetadata?: boolean
  } = {},
): Promise<VectorMatch[]> {
  const result = await index.query(queryVector, {
    topK: opts.topK ?? 10,
    namespace: opts.namespace,
    filter: opts.filter as Parameters<Vectorize["query"]>[1] extends infer Q
      ? Q extends { filter?: infer F } ? F : undefined
      : undefined,
    returnMetadata: opts.returnMetadata ? "all" : "indexed",
  })
  return result.matches.map((m) => ({
    id: m.id,
    score: m.score,
    metadata: m.metadata,
  }))
}

export async function deleteVectors(index: Vectorize, ids: string[]): Promise<void> {
  await index.deleteByIds(ids)
}
