import { env, SELF } from "cloudflare:test"
import { describe, expect, it } from "vitest"

describe("worker root", () => {
  it("returns service info on /", async () => {
    const resp = await SELF.fetch("https://example.com/")
    expect(resp.status).toBe(200)
    const body = (await resp.json()) as { name: string; status: string }
    expect(body.status).toBe("ok")
  })

  it("returns 200 on /health", async () => {
    const resp = await SELF.fetch("https://example.com/health")
    expect(resp.status).toBe(200)
  })

  it("requires auth on /api/v1/search", async () => {
    const resp = await SELF.fetch("https://example.com/api/v1/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: "hello" }),
    })
    expect(resp.status).toBe(401)
  })

  it("env bindings are wired", () => {
    expect(env.DB).toBeDefined()
    expect(env.AI).toBeDefined()
    expect(env.CACHE).toBeDefined()
    expect(env.VECTORS).toBeDefined()
  })
})
