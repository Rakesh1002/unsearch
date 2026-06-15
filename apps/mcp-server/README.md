# @unsearch/mcp-server

UnSearch MCP server — verifiable web retrieval for AI agents.

## Install

Add to your MCP client config:

```json
{
  "mcpServers": {
    "unsearch": {
      "command": "npx",
      "args": ["-y", "@unsearch/mcp-server"],
      "env": {
        "UNSEARCH_API_KEY": "uns_your_api_key"
      }
    }
  }
}
```

Or with Claude Desktop:

```bash
claude mcp add unsearch -- npx -y @unsearch/mcp-server
```

## Tools

- `search` — real-time web search with signed citation envelopes
- `extract` — scrape and extract content from URLs
- `research` — multi-step research with sources
- `verify_claim` — verify a claim against a source URL

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `UNSEARCH_API_KEY` | Yes | Your UnSearch API key (`uns_...`) |
| `UNSEARCH_BASE_URL` | No | Override the API base URL |

## License

Apache 2.0
