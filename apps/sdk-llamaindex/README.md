# @unsearch/llamaindex

[LlamaIndex](https://ts.llamaindex.ai/) retriever backed by UnSearch.

## Install

```bash
pnpm add @unsearch/llamaindex @unsearch/sdk llamaindex
```

## Use

```ts
import { UnSearch } from "@unsearch/sdk"
import { UnSearchRetriever } from "@unsearch/llamaindex"
import { RetrieverQueryEngine } from "llamaindex"

const client = new UnSearch({ apiKey: process.env.UNSEARCH_API_KEY! })
const retriever = new UnSearchRetriever(client, { topK: 5, namespace: "my-docs" })

const engine = new RetrieverQueryEngine(retriever)
const response = await engine.query({ query: "What's new in 2026?" })
console.log(response.toString())
```

Set `useNeural: false` to use full-text web search instead of vector search over your namespace.
