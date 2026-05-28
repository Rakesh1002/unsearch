import { describe, expect, it, vi } from "vitest"

import { UnSearch } from "../src/index"

describe("UnSearch client", () => {
  it("constructs with required apiKey", () => {
    const client = new UnSearch({ apiKey: "uns_test_key" })
    expect(client).toBeInstanceOf(UnSearch)
  })

  it("accepts an optional custom baseUrl", () => {
    const client = new UnSearch({ apiKey: "uns_test_key", baseUrl: "https://api.example.test" })
    expect(client).toBeInstanceOf(UnSearch)
  })

  it("accepts an optional custom fetch implementation", () => {
    const customFetch = vi.fn() as unknown as typeof fetch
    const client = new UnSearch({ apiKey: "uns_test_key", fetch: customFetch })
    expect(client).toBeInstanceOf(UnSearch)
  })

  it("sends X-API-Key header on search()", async () => {
    const responseBody = {
      query: "test",
      results: [],
      response_time_ms: 12,
      cache_hit: false,
    }
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 200,
        headers: { "content-type": "application/json" },
      }),
    ) as unknown as typeof fetch

    const client = new UnSearch({ apiKey: "uns_test_key", fetch: mockFetch })
    const result = await client.search({ query: "test" })

    expect(result.query).toBe("test")
    expect(mockFetch).toHaveBeenCalledTimes(1)
    const [, init] = (mockFetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    const headers = init.headers as Record<string, string>
    expect(headers["X-API-Key"]).toBe("uns_test_key")
    expect(headers["Content-Type"]).toBe("application/json")
  })
})
