import { DurableObject } from "cloudflare:workers"

import type { Env } from "../env.js"
import { chat } from "../lib/workers-ai.js"

interface ResearchStep {
  step: number
  query: string
  results: Array<{ url: string; title: string; snippet: string }>
  reasoning: string
  finishedAt: number
}

interface ResearchSession {
  sessionId: string
  userId: number
  initialQuery: string
  depth: number
  status: "running" | "completed" | "failed"
  steps: ResearchStep[]
  finalAnswer?: string
  startedAt: number
  finishedAt?: number
  error?: string
}

export class ResearchAgent extends DurableObject<Env> {
  override async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url)

    if (request.method === "POST" && url.pathname === "/start") {
      const body = (await request.json()) as { sessionId: string; userId: number; query: string; depth: number }
      const session: ResearchSession = {
        sessionId: body.sessionId,
        userId: body.userId,
        initialQuery: body.query,
        depth: Math.min(body.depth, 5),
        status: "running",
        steps: [],
        startedAt: Date.now(),
      }
      await this.ctx.storage.put("session", session)
      // Schedule first step alarm
      await this.ctx.storage.setAlarm(Date.now() + 100)
      return Response.json(session)
    }

    if (request.method === "GET" && url.pathname === "/state") {
      const session = await this.ctx.storage.get<ResearchSession>("session")
      return session ? Response.json(session) : new Response("not_found", { status: 404 })
    }

    return new Response("not_found", { status: 404 })
  }

  override async alarm(): Promise<void> {
    const session = await this.ctx.storage.get<ResearchSession>("session")
    if (!session || session.status !== "running") return

    try {
      const stepNumber = session.steps.length + 1
      const previousFindings = session.steps
        .map((s) => `Step ${s.step}: ${s.reasoning}`)
        .join("\n")

      // Use LLM to plan next sub-query
      const planning = await chat(this.env.AI, this.env, [
        {
          role: "system",
          content: "You are a research agent. Given the original query and prior findings, decide the next sub-query to investigate. Respond in JSON: {\"sub_query\": \"...\", \"reasoning\": \"...\"}.",
        },
        {
          role: "user",
          content: `Original query: ${session.initialQuery}\nPrior findings:\n${previousFindings || "(none yet)"}\nStep ${stepNumber} of ${session.depth}.`,
        },
      ], { tier: "reasoning", maxTokens: 512 })

      let subQuery = session.initialQuery
      let reasoning = "Initial investigation"
      try {
        const parsed = JSON.parse(planning.response.match(/\{[\s\S]*\}/)?.[0] ?? "{}") as {
          sub_query?: string
          reasoning?: string
        }
        if (parsed.sub_query) subQuery = parsed.sub_query
        if (parsed.reasoning) reasoning = parsed.reasoning
      } catch {
        // fall back to raw response
        reasoning = planning.response.slice(0, 500)
      }

      // Delegate the actual search to the Container (heavy op)
      const searchResp = await this.env.CONTAINER.fetch(
        new Request("https://container.internal/api/v1/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: subQuery, max_results: 5 }),
        }),
      )
      const searchData = (await searchResp.json()) as {
        results?: Array<{ url: string; title: string; snippet: string }>
      }

      const step: ResearchStep = {
        step: stepNumber,
        query: subQuery,
        results: searchData.results ?? [],
        reasoning,
        finishedAt: Date.now(),
      }
      session.steps.push(step)

      if (session.steps.length >= session.depth) {
        // Synthesize final answer
        const synth = await chat(this.env.AI, this.env, [
          {
            role: "system",
            content: "Synthesize the research findings into a comprehensive answer with inline citations [n] referring to source URLs.",
          },
          {
            role: "user",
            content: `Question: ${session.initialQuery}\n\nFindings:\n${session.steps
              .map((s, i) => `[${i + 1}] ${s.query}\n${s.results.map((r) => `- ${r.title} (${r.url}): ${r.snippet}`).join("\n")}`)
              .join("\n\n")}`,
          },
        ], { tier: "reasoning", maxTokens: 1500 })
        session.finalAnswer = synth.response
        session.status = "completed"
        session.finishedAt = Date.now()
      } else {
        // Schedule next step
        await this.ctx.storage.setAlarm(Date.now() + 500)
      }

      await this.ctx.storage.put("session", session)
    } catch (err) {
      session.status = "failed"
      session.error = err instanceof Error ? err.message : String(err)
      session.finishedAt = Date.now()
      await this.ctx.storage.put("session", session)
    }
  }
}
