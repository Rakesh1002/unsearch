/**
 * Hosted MCP server at /mcp.
 *
 * This is an HTTP tool server compatible with the Model Context Protocol:
 * - GET /mcp returns the tool catalog.
 * - POST /mcp accepts a JSON-RPC-style body `{ method, params, id }` and invokes
 *   the named tool against the UnSearch backend.
 *
 * It reuses @unsearch/sdk so the tool semantics match the standalone
 * `npx @unsearch/mcp-server` package exactly.
 */
import { Hono } from "hono"
import { UnSearch } from "@unsearch/sdk"
import type { Env, Variables } from "../env.js"

const TOOLS = [
  {
    name: "search",
    description:
      "Search the open web and return ranked results. Each result includes a signed citation envelope (url, fetched_at, content_sha256, snapshot_key, signature) so the retrieval is replayable and auditable.",
    inputSchema: {
      type: "object" as const,
      properties: {
        query: { type: "string" },
        max_results: { type: "number", default: 5 },
        engines: { type: "array", items: { type: "string" }, default: ["google", "bing", "duckduckgo"] },
        scrape_content: { type: "boolean", default: false },
      },
      required: ["query"],
    },
  },
  {
    name: "extract",
    description: "Scrape and extract structured content from one or more URLs. Returns raw text/markdown plus a signed citation envelope per URL.",
    inputSchema: {
      type: "object" as const,
      properties: {
        urls: { type: "array", items: { type: "string" } },
        include_images: { type: "boolean", default: false },
        extract_depth: { type: "string", enum: ["basic", "advanced"], default: "basic" },
      },
      required: ["urls"],
    },
  },
  {
    name: "research",
    description: "Run a multi-step research query and return a synthesized answer with sources. Each source carries a signed citation envelope.",
    inputSchema: {
      type: "object" as const,
      properties: {
        topic: { type: "string" },
        depth: { type: "string", enum: ["quick", "standard", "deep", "comprehensive"], default: "standard" },
        max_sources: { type: "number", default: 10 },
        include_analysis: { type: "boolean", default: true },
        include_summary: { type: "boolean", default: true },
      },
      required: ["topic"],
    },
  },
  {
    name: "verify_claim",
    description: "Verify a claim against a source URL. Returns a verdict, confidence score, and evidence spans with signed citations.",
    inputSchema: {
      type: "object" as const,
      properties: {
        claim: { type: "string" },
        source_url: { type: "string" },
        depth: { type: "string", enum: ["quick", "thorough"], default: "quick" },
      },
      required: ["claim", "source_url"],
    },
  },
]

function getClient(c: any): UnSearch {
  const apiKey = c.get("apiKey") || c.env.UNSEARCH_API_KEY
  const baseUrl = c.env.UNSEARCH_BASE_URL || `https://${c.req.header("host")}`
  return new UnSearch({ apiKey: apiKey || "", baseUrl })
}

const app = new Hono<{ Bindings: Env; Variables: Variables }>()

app.get("/", (c) =>
  c.json({
    protocol: "mcp-v1-http",
    name: "unsearch",
    version: "0.1.0",
    tools: TOOLS,
  }),
)

app.post("/", async (c) => {
  const body = await c.req.json().catch(() => ({}))
  const { method, params, id } = body

  if (method === "tools/list") {
    return c.json({ jsonrpc: "2.0", id, result: { tools: TOOLS } })
  }

  if (method === "tools/call") {
    const toolName = params?.name
    const args = params?.arguments || {}
    const client = getClient(c)

    try {
      let result: unknown
      if (toolName === "search") {
        result = await client.search({
          query: String(args.query),
          max_results: Number(args.max_results ?? 5),
          engines: Array.isArray(args.engines) ? args.engines : undefined,
          scrape_content: Boolean(args.scrape_content),
        })
      } else if (toolName === "extract") {
        result = await client.extract({
          urls: Array.isArray(args.urls) ? args.urls.map(String) : [],
          include_images: Boolean(args.include_images),
          extract_depth: String(args.extract_depth ?? "basic") as "basic" | "advanced",
        })
      } else if (toolName === "research") {
        result = await client.research({
          query: String(args.topic),
          depth: String(args.depth ?? "standard") as any,
          max_sources: Number(args.max_sources ?? 10),
          include_analysis: Boolean(args.include_analysis),
          include_summary: Boolean(args.include_summary),
        })
      } else if (toolName === "verify_claim") {
        result = await client.verifyClaim({
          claim: String(args.claim),
          source_url: String(args.source_url),
          depth: String(args.depth ?? "quick") as "quick" | "thorough",
        })
      } else {
        return c.json({ jsonrpc: "2.0", id, error: { code: -32601, message: `Unknown tool: ${toolName}` } }, 404)
      }

      return c.json({
        jsonrpc: "2.0",
        id,
        result: {
          content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
        },
      })
    } catch (err: any) {
      return c.json(
        {
          jsonrpc: "2.0",
          id,
          error: { code: -32603, message: err.message || String(err) },
        },
        500,
      )
    }
  }

  return c.json({ jsonrpc: "2.0", id, error: { code: -32601, message: `Unknown method: ${method}` } }, 400)
})

export default app
