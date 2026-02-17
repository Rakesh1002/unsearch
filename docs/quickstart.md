# UnSearch Quickstart - 5 Minutes to First API Call

Get from zero to your first AI-powered search in under 5 minutes.

## What is UnSearch?

UnSearch is a **Tavily-compatible AI search API** with RAG (Retrieval Augmented Generation) capabilities. It's:

- 🤖 **AI-powered** - Get intelligent answers, not just links
- 🔄 **Tavily-compatible** - Drop-in replacement
- 📚 **RAG-ready** - Built for LLM applications
- 💰 **96% cheaper at scale** - As low as $0.0003/query vs Tavily's ~$0.0075
- 🌐 **70+ search engines** - Aggregated results
- 🔒 **Privacy-first** - Zero-retention mode available

---

## Step 1: Get API Key (30 seconds)

### Option A: Sign Up on Dashboard

1. Go to [unsearch.dev](https://unsearch.dev)
2. Click "Sign Up"
3. Verify your email
4. Go to Dashboard → API Keys
5. Click "Create New Key"
6. Copy your API key (starts with `uns_`)

### Option B: Quick Test (No Signup)

Use our demo API key for testing:
```bash
export UNSEARCH_API_KEY="uns_demo_test_key"
```

**Note:** Demo key has rate limits. Get a real key for production.

---

## Step 2: Install SDK (30 seconds)

### JavaScript/TypeScript

```bash
npm install unsearch
# or
yarn add unsearch
# or
pnpm add unsearch
```

### Python

```bash
pip install unsearch
# or
poetry add unsearch
```

---

## Step 3: Make Your First Query (2 minutes)

### JavaScript/TypeScript

```typescript
import { UnSearchClient } from 'unsearch';

const client = new UnSearchClient({
  apiKey: 'uns_...' // or set UNSEARCH_API_KEY env var
});

// Simple search
const results = await client.search({
  query: 'What is retrieval augmented generation?',
  maxResults: 5
});

console.log(results.results);
// [
//   { title: "RAG Explained", url: "...", content: "..." },
//   { title: "Introduction to RAG", url: "...", content: "..." },
//   ...
// ]
```

### Python

```python
from unsearch import UnSearchClient

client = UnSearchClient(api_key='uns_...')

# Simple search
results = client.search(
    query='What is retrieval augmented generation?',
    max_results=5
)

for result in results.results:
    print(f"{result.title}: {result.url}")
```

### cURL (No SDK Required)

```bash
curl -X POST https://api.unsearch.dev/api/v1/agent/search \
  -H "X-API-Key: uns_..." \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is retrieval augmented generation?",
    "max_results": 5
  }'
```

---

## Step 4: Get AI Answers (2 minutes)

Add `includeAnswer: true` to get AI-generated answers along with sources:

### JavaScript

```typescript
const response = await client.search({
  query: 'How does vector search work in RAG systems?',
  includeAnswer: true,  // ← Enable AI answer
  maxResults: 5
});

console.log('Answer:', response.answer);
// "Vector search in RAG systems works by converting text into
//  numerical embeddings that capture semantic meaning..."

console.log('Sources:', response.results.length);
// 5 sources used to generate the answer
```

### Python

```python
response = client.search(
    query='How does vector search work in RAG systems?',
    include_answer=True,
    max_results=5
)

print('Answer:', response.answer)
print('Sources:', len(response.sources))
```

---

## Common Use Cases

### Use Case 1: Quick Q&A

Get direct answers to simple questions:

```typescript
const answer = await client.qna('What is the capital of France?');
console.log(answer);
// "Paris is the capital and largest city of France..."
```

### Use Case 2: RAG for LLM Applications

Get search context optimized for feeding into LLMs:

```typescript
const context = await client.getSearchContext(
  'latest developments in quantum computing',
  5  // max results
);

// Feed to your LLM
const prompt = `Based on this context:\n${context}\n\nAnswer: ...`;
```

### Use Case 3: Content Extraction

Extract and parse content from URLs:

```typescript
const extracted = await client.extract({
  urls: [
    'https://example.com/article1',
    'https://example.com/article2'
  ],
  includeImages: true
});

for (const content of extracted.results) {
  console.log(content.title);
  console.log(content.markdown);  // Markdown formatted
}
```

### Use Case 4: Deep Research (UnSearch Exclusive)

Multi-step research with AI synthesis:

```typescript
const research = await client.research({
  topic: 'Impact of AI on healthcare',
  depth: 'deep',  // quick | standard | deep | comprehensive
  maxSources: 20
});

console.log(research.executiveSummary);
console.log(research.keyFindings);
console.log(research.sources.length);  // 20+ sources
```

---

## Advanced Features

### Model Selection

Choose the right AI model for your use case:

```typescript
const response = await client.search({
  query: 'complex analytical question',
  includeAnswer: true,
  model: 'reasoning',  // auto | speed | quality | reasoning | production
  maxResults: 10
});
```

**Models:**
- `auto` - Automatically choose best model (default)
- `speed` - Fast responses, simple queries (Llama 3.1 8B)
- `quality` - Best quality answers (GPT-OSS 120B)
- `reasoning` - Complex analysis (QwQ 32B)
- `production` - Enterprise-grade (GPT-OSS 120B)

### Search Depth

Control how thorough the search is:

```typescript
const results = await client.search({
  query: 'latest AI research papers',
  searchDepth: 'advanced',  // basic | advanced | fast | ultra-fast
  maxResults: 20
});
```

### Domain Filtering

Include or exclude specific domains:

```typescript
const results = await client.search({
  query: 'machine learning papers',
  includeDomains: ['arxiv.org', 'nature.com'],  // Only these
  excludeDomains: ['wikipedia.org'],  // Exclude these
  maxResults: 10
});
```

### Zero-Retention Mode (Privacy)

Enable zero-retention mode for privacy-sensitive queries:

```typescript
// In request header
headers: {
  'X-API-Key': 'uns_...',
  'X-Zero-Retention': 'true'  // Don't store query or results
}
```

---

## Error Handling

Handle common errors gracefully:

```typescript
import {
  UnSearchClient,
  UnSearchAuthError,
  UnSearchRateLimitError,
  UnSearchNetworkError
} from 'unsearch';

try {
  const results = await client.search({ query: 'test' });
} catch (error) {
  if (error instanceof UnSearchAuthError) {
    console.error('Invalid API key - check your credentials');
  } else if (error instanceof UnSearchRateLimitError) {
    console.error('Rate limit exceeded - upgrade your plan or wait');
  } else if (error instanceof UnSearchNetworkError) {
    console.error('Network error - check your connection');
  } else {
    console.error('Unknown error:', error);
  }
}
```

---

## Next Steps

### Integrate into Your App

- **Next.js:** See [examples/nextjs-app](../examples/nextjs-app)
- **React:** See [examples/react-search-bar](../examples/react-search-bar)
- **Node.js:** See [examples/nodejs-backend](../examples/nodejs-backend)
- **Python Flask:** See [examples/flask-app](../examples/flask-app)

### Explore All Features

- [API Reference](./api-reference/README.md) - Complete API documentation
- [Examples](../examples/README.md) - Full example applications
- [Migration from Tavily](./migration/from-tavily.md) - Drop-in replacement
- [Self-Hosting](./guides/self-hosting.md) - Run your own instance

### Get Help

- 📧 Email: support@unsearch.dev
- 💬 Discord: [Join community](https://discord.gg/unsearch)
- 📖 Docs: [docs.unsearch.dev](https://docs.unsearch.dev)
- 🐛 Issues: [GitHub](https://github.com/rakesh1002/unsearch/issues)

---

## Free Tier Limits

- **5,000 queries/month** (5x more than Tavily's 1,000)
- **500 scrapes/month**
- **Community support**
- **All features included**

Upgrade to Pro ($19/mo) for 25,000 queries and email support.

---

## Migration from Tavily

UnSearch is **100% Tavily-compatible**. Just swap the client:

```diff
- import { TavilyClient } from '@tavily/core';
- const client = new TavilyClient({ apiKey: '...' });
+ import { UnSearchClient } from 'unsearch';
+ const client = new UnSearchClient({ apiKey: '...' });

// All methods work the same!
const results = await client.search({ query: '...' });
```

See [Migration Guide](./migration/from-tavily.md) for complete instructions.

---

**You're all set! 🎉**

Start building AI-powered search into your applications. Questions? Reach out on [Discord](https://discord.gg/unsearch) or [email us](mailto:support@unsearch.dev).
