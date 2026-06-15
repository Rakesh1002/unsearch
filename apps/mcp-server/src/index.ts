/**
 * UnSearch MCP server.
 *
 * Exposes four tools:
 * - search: real-time web search with signed citation envelopes
 * - extract: scrape and extract content from URLs
 * - research: multi-step research synthesis
 * - verify_claim: span-level claim verification against a source
 *
 * Supports both stdio (for `npx @unsearch/mcp-server`) and programmatic
 * transport injection (for hosted surfaces).
 */
import { Server } from "@modelcontextprotocol/sdk/server/index.js"
import type { Transport } from "@modelcontextprotocol/sdk/shared/transport.js"
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  type CallToolRequest,
  type TextContent,
} from "@modelcontextprotocol/sdk/types.js"

import { createClient, getMissingKeyMessage, type UnSearchConfig } from "./unsearch-client.js"

export { createClient, getMissingKeyMessage, type UnSearchConfig }

const TOOLS = [
  {
    name: "search",
    description:
      "Search the open web and return ranked results. Each result includes a signed citation envelope (url, fetched_at, content_sha256, snapshot_key, signature) so the retrieval is replayable and auditable.",
    inputSchema: {
      type: "object" as const,
      properties: {
        query: { type: "string", description: "Search query" },
        max_results: { type: "number", description: "Maximum results to return (1-20)", default: 5 },
        engines: {
          type: "array",
          items: { type: "string" },
          description: "Search engines to use",
          default: ["google", "bing", "duckduckgo"],
        },
        scrape_content: {
          type: "boolean",
          description: "Whether to scrape full page content for each result",
          default: false,
        },
      },
      required: ["query"],
    },
  },
  {
    name: "extract",
    description:
      "Scrape and extract structured content from one or more URLs. Returns raw text/markdown plus a signed citation envelope per URL.",
    inputSchema: {
      type: "object" as const,
      properties: {
        urls: {
          type: "array",
          items: { type: "string" },
          description: "URLs to extract",
        },
        include_images: { type: "boolean", default: false },
        extract_depth: {
          type: "string",
          enum: ["basic", "advanced"],
          default: "basic",
        },
      },
      required: ["urls"],
    },
  },
  {
    name: "research",
    description:
      "Run a multi-step research query and return a synthesized answer with sources. Each source carries a signed citation envelope.",
    inputSchema: {
      type: "object" as const,
      properties: {
        topic: { type: "string", description: "Research question or topic" },
        depth: {
          type: "string",
          enum: ["quick", "standard", "deep", "comprehensive"],
          default: "standard",
        },
        max_sources: { type: "number", default: 10 },
        include_analysis: { type: "boolean", default: true },
        include_summary: { type: "boolean", default: true },
      },
      required: ["topic"],
    },
  },
  {
    name: "verify_claim",
    description:
      "Verify a claim against a source URL. Returns a verdict, confidence score, and evidence spans with signed citations.",
    inputSchema: {
      type: "object" as const,
      properties: {
        claim: { type: "string", description: "Claim to verify" },
        source_url: { type: "string", description: "Source URL to check the claim against" },
        depth: { type: "string", enum: ["quick", "thorough"], default: "quick" },
      },
      required: ["claim", "source_url"],
    },
  },
]

function textContent(text: string): TextContent {
  return { type: "text", text }
}

export function createServer(config?: UnSearchConfig): Server {
  const client = createClient(config)
  const apiKey = config?.apiKey ?? process.env.UNSEARCH_API_KEY

  const server = new Server(
    { name: "unsearch", version: "0.1.0" },
    { capabilities: { tools: {} } }
  )

  server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }))

  server.setRequestHandler(CallToolRequestSchema, async (request: CallToolRequest) => {
    if (!apiKey) {
      return { content: [textContent(getMissingKeyMessage())], isError: true }
    }

    const { name, arguments: argsRaw } = request.params
    const args = (argsRaw ?? {}) as Record<string, unknown>

    try {
      let result: unknown
      if (name === "search") {
        result = await client.search({
          query: String(args.query),
          max_results: Number(args.max_results ?? 5),
          engines: Array.isArray(args.engines) ? (args.engines as string[]) : undefined,
          scrape_content: Boolean(args.scrape_content),
        })
      }

      if (name === "extract") {
        result = await client.extract({
          urls: Array.isArray(args.urls) ? args.urls.map(String) : [],
          include_images: Boolean(args.include_images),
          extract_depth: String(args.extract_depth ?? "basic") as "basic" | "advanced",
        })
      }

      if (name === "research") {
        result = await client.research({
          query: String(args.topic),
          depth: String(args.depth ?? "standard") as any,
        })
      }

      if (name === "verify_claim") {
        result = await client.verifyClaim({
          claim: String(args.claim),
          source_url: String(args.source_url),
          depth: String(args.depth ?? "quick") as "quick" | "thorough",
        })
      }

      if (name === "extract") {
        const result = await client.extract({
          urls: Array.isArray(args.urls) ? args.urls.map(String) : [],
          include_images: Boolean(args.include_images),
          extract_depth: String(args.extract_depth ?? "basic") as "basic" | "advanced",
        })
        return { content: [textContent(JSON.stringify(result, null, 2))] }
      }

      if (name === "research") {
        const result = await client.research({
          query: String(args.topic),
          depth: String(args.depth ?? "standard") as any,
          max_sources: Number(args.max_sources ?? 10),
          include_analysis: Boolean(args.include_analysis),
          include_summary: Boolean(args.include_summary),
        })
        return { content: [textContent(JSON.stringify(result, null, 2))] }
      }

      if (name === "verify_claim") {
        const result = await client.verifyClaim({
          claim: String(args.claim),
          source_url: String(args.source_url),
          depth: String(args.depth ?? "quick") as "quick" | "thorough",
        })
        return { content: [textContent(JSON.stringify(result, null, 2))] }
      }

      return {
        content: [textContent(`Unknown tool: ${name}`)],
        isError: true,
      }
    } catch (err: any) {
      return {
        content: [textContent(`UnSearch tool ${name} failed: ${err.message || String(err)}`)],
        isError: true,
      }
    }
  })

  return server
}

export async function startServer(transport: Transport, config?: UnSearchConfig): Promise<Server> {
  const server = createServer(config)
  await server.connect(transport)
  return server
}
