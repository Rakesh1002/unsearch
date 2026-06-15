#!/usr/bin/env node
/**
 * CLI entry point for `npx @unsearch/mcp-server`.
 *
 * Starts an MCP server over stdio. Configure with environment variables:
 *   UNSEARCH_API_KEY=uns_...
 *   UNSEARCH_BASE_URL=https://api.unsearch.dev  (optional)
 */
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js"
import { startServer } from "./index.js"

async function main(): Promise<void> {
  const transport = new StdioServerTransport()
  await startServer(transport)
  // Keep process alive until stdio closes.
}

main().catch((err) => {
  console.error("UnSearch MCP server failed:", err)
  process.exit(1)
})
