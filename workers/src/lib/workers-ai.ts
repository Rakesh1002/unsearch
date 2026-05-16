import type { Ai } from "@cloudflare/workers-types"

import type { Env } from "../env.js"

export type ModelTier = "fast" | "balanced" | "reasoning"

export function pickLlmModel(env: Env, tier: ModelTier = "balanced"): string {
  if (tier === "reasoning") return env.CLOUDFLARE_REASONING_MODEL
  if (tier === "fast") return "@cf/meta/llama-3.1-8b-instruct"
  return env.CLOUDFLARE_LLM_MODEL
}

export interface ChatMessage {
  role: "system" | "user" | "assistant"
  content: string
}

export interface ChatOptions {
  model?: string
  tier?: ModelTier
  maxTokens?: number
  temperature?: number
  stream?: boolean
}

export async function chat(
  ai: Ai,
  env: Env,
  messages: ChatMessage[],
  opts: ChatOptions = {},
): Promise<{ response: string }> {
  const model = opts.model ?? pickLlmModel(env, opts.tier)
  const result = (await ai.run(model as never, {
    messages,
    max_tokens: opts.maxTokens ?? 1024,
    temperature: opts.temperature ?? 0.3,
    stream: false,
  } as never)) as unknown as { response: string }
  return { response: result.response }
}

export async function chatStream(
  ai: Ai,
  env: Env,
  messages: ChatMessage[],
  opts: ChatOptions = {},
): Promise<ReadableStream<Uint8Array>> {
  const model = opts.model ?? pickLlmModel(env, opts.tier)
  const result = (await ai.run(model as never, {
    messages,
    max_tokens: opts.maxTokens ?? 1024,
    temperature: opts.temperature ?? 0.3,
    stream: true,
  } as never)) as unknown as ReadableStream<Uint8Array>
  return result
}

export async function embed(
  ai: Ai,
  env: Env,
  texts: string[],
): Promise<number[][]> {
  const result = (await ai.run(env.CLOUDFLARE_EMBEDDING_MODEL as never, {
    text: texts,
  } as never)) as unknown as { data: number[][] }
  return result.data
}

export async function rerank(
  ai: Ai,
  env: Env,
  query: string,
  documents: string[],
): Promise<Array<{ index: number; score: number }>> {
  const result = (await ai.run(env.CLOUDFLARE_RERANKER_MODEL as never, {
    query,
    contexts: documents.map((text) => ({ text })),
  } as never)) as unknown as { response: Array<{ id: number; score: number }> }
  return result.response.map((r) => ({ index: r.id, score: r.score }))
}

export async function classifyContentSafety(
  ai: Ai,
  env: Env,
  text: string,
): Promise<{ safe: boolean; categories: string[] }> {
  const result = (await ai.run(env.CLOUDFLARE_SAFETY_MODEL as never, {
    messages: [{ role: "user", content: text }],
  } as never)) as unknown as { response: string }
  const lower = result.response.toLowerCase()
  const safe = lower.includes("safe") && !lower.includes("unsafe")
  const categories = lower.match(/s\d+/g) ?? []
  return { safe, categories }
}
