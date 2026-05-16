/**
 * @unsearch/llamaindex — LlamaIndex retriever backed by UnSearch.
 *
 * Usage:
 * ```ts
 * import { UnSearch } from "@unsearch/sdk"
 * import { UnSearchRetriever } from "@unsearch/llamaindex"
 * import { RetrieverQueryEngine } from "llamaindex"
 *
 * const client = new UnSearch({ apiKey: process.env.UNSEARCH_API_KEY! })
 * const retriever = new UnSearchRetriever(client, { topK: 5, namespace: "docs" })
 * const engine = new RetrieverQueryEngine(retriever)
 * const response = await engine.query({ query: "..." })
 * ```
 */
import type { UnSearch, VectorMatch } from "@unsearch/sdk"
import type { BaseRetriever, NodeWithScore, QueryBundle } from "llamaindex"
import { TextNode } from "llamaindex"

export interface UnSearchRetrieverOptions {
  topK?: number
  namespace?: string
  useNeural?: boolean
}

export class UnSearchRetriever implements BaseRetriever {
  constructor(
    private client: UnSearch,
    private opts: UnSearchRetrieverOptions = {},
  ) {}

  async retrieve(query: string | QueryBundle): Promise<NodeWithScore[]> {
    const queryStr = typeof query === "string" ? query : query.query.toString()
    const topK = this.opts.topK ?? 5

    if (this.opts.useNeural !== false) {
      const resp = await this.client.neuralSearch({
        query: queryStr,
        top_k: topK,
        namespace: this.opts.namespace,
      })
      return resp.matches.map(matchToNode)
    }

    const resp = await this.client.search({ query: queryStr, max_results: topK })
    return resp.results.map((r, i) => ({
      node: new TextNode({
        id_: r.url,
        text: `${r.title}\n\n${r.snippet}`,
        metadata: { url: r.url, title: r.title, engine: r.engine, rank: r.rank },
      }),
      score: r.score ?? 1 - i / topK,
    }))
  }
}

function matchToNode(match: VectorMatch): NodeWithScore {
  const text = (match.metadata?.text as string | undefined) ?? ""
  const title = (match.metadata?.title as string | undefined) ?? match.id
  return {
    node: new TextNode({
      id_: match.id,
      text: `${title}\n\n${text}`,
      metadata: match.metadata ?? {},
    }),
    score: match.score,
  }
}
