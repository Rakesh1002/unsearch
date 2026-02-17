# Migrating from Tavily to UnSearch

UnSearch is **100% compatible** with Tavily's API. Migration takes less than 5 minutes.

## Why Migrate?

| Feature | Tavily | UnSearch | Benefit |
|---------|--------|----------|---------|
| **Price at scale** | ~$0.0075/query | $0.0003/query | **96% savings** |
| **Free tier** | 1,000 queries | 5,000 queries | **5x more** |
| **Search engines** | Single | 70+ aggregated | Better coverage |
| **Self-hosting** | ❌ | ✅ Open source | Full control |
| **Zero retention** | ❌ | ✅ Available | Privacy |
| **Deep research** | ❌ | ✅ Exclusive | Advanced features |
| **Model choice** | Single | 20+ AI models | Flexibility |

**Cost Example (Scale plan - 500K queries):**
- 500K queries/month on Tavily: **$3,750/month** (~$0.0075/query)
- 500K queries/month on UnSearch: **$149/month** ($0.0003/query)
- **Savings: $3,601/month = $43,212/year**

---

## Migration Steps

### Step 1: Get UnSearch API Key

1. Sign up at [unsearch.dev](https://unsearch.dev)
2. Go to Dashboard → API Keys
3. Create new key (starts with `uns_`)

### Step 2: Update SDK

#### JavaScript/TypeScript

```bash
# Remove Tavily
npm uninstall @tavily/core

# Install UnSearch
npm install unsearch
```

#### Python

```bash
# Remove Tavily
pip uninstall tavily-python

# Install UnSearch
pip install unsearch
```

### Step 3: Update Code

#### JavaScript/TypeScript

```diff
- import { TavilyClient } from '@tavily/core';
+ import { UnSearchClient } from 'unsearch';

- const client = new TavilyClient({
+ const client = new UnSearchClient({
-   apiKey: process.env.TAVILY_API_KEY
+   apiKey: process.env.UNSEARCH_API_KEY
  });
```

#### Python

```diff
- from tavily import TavilyClient
+ from unsearch import UnSearchClient

- client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
+ client = UnSearchClient(api_key=os.getenv("UNSEARCH_API_KEY"))
```

### Step 4: Update Environment Variables

```diff
- TAVILY_API_KEY=tvly-...
+ UNSEARCH_API_KEY=uns_...
```

**That's it!** All other code remains the same.

---

## API Compatibility Matrix

### ✅ Fully Compatible Methods

| Method | Tavily | UnSearch | Notes |
|--------|--------|----------|-------|
| `search()` | ✅ | ✅ | 100% compatible |
| `extract()` | ✅ | ✅ | 100% compatible |
| `getSearchContext()` | ✅ | ✅ | RAG context method |

### 🚀 UnSearch Exclusive Methods

| Method | Description |
|--------|-------------|
| `research()` | Multi-step deep research with AI synthesis |
| `qna()` | Quick Q&A shortcut for simple questions |
| `ragSearch()` | RAG-optimized search with assembled context |

---

## Feature Comparison

### Search API

**Tavily:**
```typescript
const results = await client.search({
  query: 'What is RAG?',
  searchDepth: 'advanced',
  maxResults: 5,
  includeAnswer: true
});
```

**UnSearch (same + more):**
```typescript
const results = await client.search({
  query: 'What is RAG?',
  searchDepth: 'advanced',  // basic | advanced | fast | ultra-fast
  maxResults: 5,
  includeAnswer: true,
  model: 'quality',  // ← NEW: Choose AI model
  rerank: true,      // ← NEW: AI reranking
  includeImages: true,  // ← NEW: Image results
  includeDomains: ['arxiv.org'],  // ← NEW: Domain filtering
});
```

### Extract API

**Tavily:**
```typescript
const extracted = await client.extract({
  urls: ['https://example.com/article']
});
```

**UnSearch (same + more):**
```typescript
const extracted = await client.extract({
  urls: ['https://example.com/article'],
  extractDepth: 'advanced',  // ← NEW: basic | advanced
  includeImages: true  // ← NEW: Extract images
});
```

### RAG Context

**Tavily:**
```typescript
const context = await client.getSearchContext(
  'query',
  5  // max results
);
```

**UnSearch (100% compatible):**
```typescript
const context = await client.getSearchContext(
  'query',
  5  // max results
);
// Returns exact same format as Tavily
```

---

## Code Examples

### Example 1: Basic Search

**Before (Tavily):**
```typescript
import { TavilyClient } from '@tavily/core';

const tavily = new TavilyClient({
  apiKey: process.env.TAVILY_API_KEY
});

const results = await tavily.search({
  query: 'latest AI developments',
  maxResults: 10
});
```

**After (UnSearch):**
```typescript
import { UnSearchClient } from 'unsearch';

const unsearch = new UnSearchClient({
  apiKey: process.env.UNSEARCH_API_KEY
});

const results = await unsearch.search({
  query: 'latest AI developments',
  maxResults: 10
});
```

### Example 2: RAG Application

**Before (Tavily):**
```typescript
const context = await tavily.getSearchContext(
  'machine learning best practices',
  5
);

const answer = await openai.chat.completions.create({
  messages: [
    { role: 'system', content: `Context: ${context}` },
    { role: 'user', content: 'Explain best practices' }
  ]
});
```

**After (UnSearch - same code!):**
```typescript
const context = await unsearch.getSearchContext(
  'machine learning best practices',
  5
);

const answer = await openai.chat.completions.create({
  messages: [
    { role: 'system', content: `Context: ${context}` },
    { role: 'user', content: 'Explain best practices' }
  ]
});
```

---

## LangChain Integration

### Before (Tavily)

```python
from langchain.tools import TavilySearchResults

tool = TavilySearchResults(api_key="tvly-...")
results = tool.invoke("query")
```

### After (UnSearch)

```python
from unsearch.langchain import UnSearchResults

tool = UnSearchResults(api_key="uns_...")
results = tool.invoke("query")

# Or use Tavily-compatible alias
from unsearch.langchain import TavilySearchResults
tool = TavilySearchResults(api_key="uns_...")  # Works!
```

---

## Environment-Specific Migration

### Production Migration Strategy

**Recommended Approach:** Gradual rollout

```typescript
// 1. Test in development first
const client = new UnSearchClient({
  apiKey: process.env.UNSEARCH_API_KEY
});

// 2. A/B test in production (50/50 split)
const useUnSearch = Math.random() > 0.5;
const client = useUnSearch
  ? new UnSearchClient({ apiKey: process.env.UNSEARCH_API_KEY })
  : new TavilyClient({ apiKey: process.env.TAVILY_API_KEY });

// 3. Monitor metrics:
// - Response time
// - Quality of results
// - Error rates

// 4. Full migration once validated
```

### Cost Comparison Tool

Calculate your savings:

```typescript
// Current Tavily cost
const monthlyQueries = 500000;
const tavilyCost = monthlyQueries * 0.0075;
console.log('Tavily:', tavilyCost);  // $3,750

// UnSearch cost (Scale plan: $149/mo for 500K)
const unsearchCost = 149;  // Flat rate
console.log('UnSearch:', unsearchCost);  // $149

console.log('Monthly savings:', tavilyCost - unsearchCost);  // $3,601
console.log('Annual savings:', (tavilyCost - unsearchCost) * 12);  // $43,212
```

---

## Testing Your Migration

### 1. Functionality Test

```typescript
// Test all methods work
const tests = async () => {
  // Search
  const search = await client.search({ query: 'test' });
  console.assert(search.results.length > 0, 'Search failed');

  // Extract
  const extract = await client.extract({
    urls: ['https://example.com']
  });
  console.assert(extract.results.length > 0, 'Extract failed');

  // RAG context
  const context = await client.getSearchContext('test', 5);
  console.assert(context.length > 0, 'Context failed');

  console.log('✓ All tests passed');
};
```

### 2. Performance Test

```typescript
// Compare response times
const benchmarkSearch = async (client, name) => {
  const start = Date.now();
  await client.search({ query: 'test query', maxResults: 5 });
  const duration = Date.now() - start;
  console.log(`${name} search: ${duration}ms`);
};

// Run for both clients
await benchmarkSearch(tavilyClient, 'Tavily');
await benchmarkSearch(unsearchClient, 'UnSearch');
```

### 3. Quality Test

```typescript
// Compare result quality
const query = 'What is machine learning?';

const tavilyResults = await tavilyClient.search({
  query,
  includeAnswer: true
});

const unsearchResults = await unsearchClient.search({
  query,
  includeAnswer: true
});

// Manually compare answers
console.log('Tavily answer:', tavilyResults.answer);
console.log('UnSearch answer:', unsearchResults.answer);
```

---

## Troubleshooting

### Issue: Different response format

**Solution:** UnSearch returns identical format. Check API version.

```typescript
// Both return:
{
  query: string;
  results: Array<{
    title: string;
    url: string;
    content: string;
  }>;
  answer?: string;
}
```

### Issue: Rate limit errors

**Solution:** UnSearch has higher free tier limits.

```typescript
// Tavily: 1,000 free queries/month
// UnSearch: 5,000 free queries/month

// Check your usage:
// Dashboard → Usage → Current period
```

### Issue: Missing features

**Solution:** UnSearch has all Tavily features + more.

```typescript
// If you used Tavily feature X, UnSearch has it
// Plus: research(), qna(), model selection, domain filtering
```

---

## Support

### Migration Help

- 📧 Email: support@unsearch.dev (subject: "Tavily Migration")
- 💬 Discord: [#migration channel](https://discord.gg/unsearch)
- 📖 Docs: [docs.unsearch.dev](https://docs.unsearch.dev)

### Migration Checklist

- [ ] Sign up for UnSearch account
- [ ] Get API key
- [ ] Update SDK dependency
- [ ] Update import statements
- [ ] Update environment variables
- [ ] Test in development
- [ ] A/B test in production (optional)
- [ ] Monitor metrics
- [ ] Full migration
- [ ] Cancel Tavily subscription
- [ ] Enjoy up to 96% cost savings! 🎉

---

## Common Questions

**Q: Will my existing code break?**
A: No. UnSearch is 100% Tavily-compatible. Just change the client initialization.

**Q: What about my Tavily subscription?**
A: You can run both in parallel during migration, then cancel Tavily.

**Q: Is the API response format identical?**
A: Yes, identical. Your downstream code won't need any changes.

**Q: What about performance?**
A: UnSearch typically has similar or better response times due to 70+ search engine aggregation.

**Q: Can I self-host?**
A: Yes! UnSearch is open source. See [Self-Hosting Guide](../guides/self-hosting.md).

**Q: What if I need help?**
A: Email support@unsearch.dev with "Tavily Migration" in subject. We'll help you migrate.

---

**Ready to save up to 96%?** [Get started now →](https://unsearch.dev/signup)
