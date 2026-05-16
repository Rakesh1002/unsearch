import { Hono } from "hono"
import { z } from "zod"
import { zValidator } from "@hono/zod-validator"

import type { Env, Variables } from "../env.js"
import { chat } from "../lib/workers-ai.js"
import { requireAuth } from "../middleware/auth.js"
import { rateLimitMiddleware } from "../middleware/rate-limit.js"

export const verifyRoutes = new Hono<{ Bindings: Env; Variables: Variables }>()

verifyRoutes.use("*", requireAuth(), rateLimitMiddleware())

const claimSchema = z.object({
  claim: z.string().min(5).max(2000),
  context_urls: z.array(z.string().url()).max(10).optional(),
})

verifyRoutes.post("/claim", zValidator("json", claimSchema), async (c) => {
  const body = c.req.valid("json")

  // Step 1: gather evidence (forward to container which has the search aggregator)
  const evidenceResp = await c.env.CONTAINER.fetch(
    new Request("https://container.internal/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: body.claim, max_results: 10, scrape_content: true }),
    }),
  )
  const evidence = (await evidenceResp.json()) as {
    results?: Array<{ url: string; title: string; snippet: string; content?: string }>
  }
  const sources = evidence.results ?? []

  const sourcesText = sources
    .map((s, i) => `[${i + 1}] ${s.title} (${s.url})\n${s.content?.slice(0, 1500) ?? s.snippet}`)
    .join("\n\n")

  // Step 2: ask reasoning model to verify
  const verdict = await chat(c.env.AI, c.env, [
    {
      role: "system",
      content: `You are a fact-checker. Given a claim and sources, return JSON: {"verdict":"true|false|partly_true|unverifiable","confidence":0-1,"reasoning":"...","supporting_sources":[indices],"contradicting_sources":[indices]}.`,
    },
    {
      role: "user",
      content: `Claim: ${body.claim}\n\nSources:\n${sourcesText}`,
    },
  ], { tier: "reasoning", maxTokens: 800 })

  let parsed: Record<string, unknown>
  try {
    parsed = JSON.parse(verdict.response.match(/\{[\s\S]*\}/)?.[0] ?? "{}")
  } catch {
    parsed = { verdict: "unverifiable", confidence: 0, reasoning: verdict.response.slice(0, 500) }
  }

  return c.json({ claim: body.claim, ...parsed, sources })
})

const sourceSchema = z.object({ url: z.string().url() })
verifyRoutes.post("/source", zValidator("json", sourceSchema), async (c) => {
  const body = c.req.valid("json")
  const host = new URL(body.url).hostname

  // Heuristic credibility — production version would consult a curated DB
  const verdict = await chat(c.env.AI, c.env, [
    {
      role: "system",
      content: `Rate the credibility of a website. Return JSON: {"score":0-100,"category":"news|academic|government|social|blog|unknown","bias":"left|center|right|unknown","reasoning":"..."}.`,
    },
    { role: "user", content: `Domain: ${host}` },
  ], { tier: "balanced", maxTokens: 300 })

  let parsed: Record<string, unknown>
  try {
    parsed = JSON.parse(verdict.response.match(/\{[\s\S]*\}/)?.[0] ?? "{}")
  } catch {
    parsed = { score: 50, category: "unknown", bias: "unknown", reasoning: "could not parse" }
  }
  return c.json({ url: body.url, host, ...parsed })
})

const batchSchema = z.object({ claims: z.array(z.string()).min(1).max(20) })
verifyRoutes.post("/batch", zValidator("json", batchSchema), async (c) => {
  // Defer batch processing to container (uses CF Queues internally for fan-out)
  return c.env.CONTAINER.fetch(c.req.raw)
})
