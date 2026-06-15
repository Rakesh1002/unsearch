/**
 * Thin wrapper around @unsearch/sdk for the MCP server.
 *
 * Reads UNSEARCH_API_KEY and UNSEARCH_BASE_URL from the environment.
 * Falls back to a local development URL when no key is provided, returning
 * a clear error to the LLM if the key is missing for a live call.
 */
import { UnSearch } from "@unsearch/sdk"

export interface UnSearchConfig {
  apiKey?: string
  baseUrl?: string
}

export function createClient(config?: UnSearchConfig): UnSearch {
  const apiKey = config?.apiKey ?? process.env.UNSEARCH_API_KEY
  const baseUrl = config?.baseUrl ?? process.env.UNSEARCH_BASE_URL

  if (!apiKey) {
    // Return a client instance anyway; live calls will surface the auth error.
    // This lets the MCP server start without a key for local inspection.
    return new UnSearch({ apiKey: "missing", baseUrl })
  }

  return new UnSearch({ apiKey, baseUrl })
}

export function getMissingKeyMessage(): string {
  return "UNSEARCH_API_KEY is not set. Set it in your MCP server config to use UnSearch."
}
