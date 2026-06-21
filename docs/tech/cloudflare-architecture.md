# UnSearch Cloudflare-Native Architecture

## Vision

Transform UnSearch from a traditional backend into a **globally distributed, edge-first AI search platform** leveraging Cloudflare's full infrastructure stack for:
- **Sub-100ms global latency**
- **Infinite scalability**
- **Zero-downtime deployments**
- **Stateless, crash-resistant processing**

---

## Cloudflare Services Integration

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                        CLOUDFLARE EDGE NETWORK (300+ PoPs)                              │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                           EDGE LAYER (Cloudflare Workers)                         │  │
│  │                                                                                    │  │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │  │
│  │   │   Router    │    │   Auth      │    │  Rate Limit │    │   Cache     │      │  │
│  │   │   Worker    │    │   Worker    │    │   Worker    │    │   Worker    │      │  │
│  │   └──────┬──────┘    └─────────────┘    └─────────────┘    └─────────────┘      │  │
│  │          │                                                                        │  │
│  └──────────┼────────────────────────────────────────────────────────────────────────┘  │
│             │                                                                            │
│  ┌──────────┼────────────────────────────────────────────────────────────────────────┐  │
│  │          ▼              PROCESSING LAYER                                          │  │
│  │                                                                                    │  │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │  │
│  │   │  Workers AI │    │  Vectorize  │    │   Queues    │    │   Durable   │      │  │
│  │   │             │    │  (Vectors)  │    │  (Async)    │    │   Objects   │      │  │
│  │   │ • gpt-oss   │    │             │    │             │    │  (State)    │      │  │
│  │   │ • embeddings│    │ • 40M vecs  │    │ • Research  │    │             │      │  │
│  │   │ • reranking │    │ • Metadata  │    │ • Crawl     │    │ • Sessions  │      │  │
│  │   │ • safety    │    │ • Filtering │    │ • Batch     │    │ • Progress  │      │  │
│  │   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘      │  │
│  │                                                                                    │  │
│  └────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                           STORAGE LAYER                                            │  │
│  │                                                                                    │  │
│  │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │  │
│  │   │     KV      │    │     R2      │    │     D1      │    │  Hyperdrive │      │  │
│  │   │  (Cache)    │    │  (Objects)  │    │  (SQLite)   │    │  (Postgres) │      │  │
│  │   │             │    │             │    │             │    │             │      │  │
│  │   │ • Results   │    │ • Documents │    │ • Users     │    │ • Legacy DB │      │  │
│  │   │ • Sessions  │    │ • Snapshots │    │ • API Keys  │    │ • Analytics │      │  │
│  │   │ • Rate data │    │ • Exports   │    │ • Usage     │    │             │      │  │
│  │   └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘      │  │
│  │                                                                                    │  │
│  └────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                     BROWSER RENDERING (Headless at Edge)                           │  │
│  │                                                                                    │  │
│  │   ┌─────────────────────────────────────────────────────────────────────────────┐ │  │
│  │   │  Puppeteer Workers - JavaScript rendering at 300+ locations                 │ │  │
│  │   └─────────────────────────────────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Request Flow Architecture

### Simple Search (Sync - <500ms)

```
User Request
     │
     ▼
┌─────────────────┐
│  Edge Worker    │  ← Closest to user (any of 300+ PoPs)
│  (Router)       │
└────────┬────────┘
         │
    ┌────┴────┐
    │ KV Cache│ ← Check cache first
    └────┬────┘
         │
    Cache miss?
         │
         ▼
┌─────────────────┐
│  Workers AI     │  ← Process at edge
│  (Embeddings)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Vectorize     │  ← Query vectors
│  (Similarity)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Workers AI     │  ← Generate answer
│  (LLM)          │
└────────┬────────┘
         │
         ▼
   Store in KV → Return Response
```

### Complex Research (Async - Minutes to Hours)

```
User Request
     │
     ▼
┌─────────────────┐
│  Edge Worker    │
│  (Router)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Durable Object  │  ← Create research session
│ (ResearchSession)│
└────────┬────────┘
         │
    ┌────┴────┐
    │  Queue  │  ← Enqueue research tasks
    └────┬────┘
         │
         ▼
┌─────────────────────────────────────────────────┐
│              PARALLEL PROCESSING                 │
│                                                  │
│  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐│
│  │Worker 1│  │Worker 2│  │Worker 3│  │Worker N││
│  │Search  │  │Scrape  │  │Analyze │  │Synth.  ││
│  └───┬────┘  └───┬────┘  └───┬────┘  └───┬────┘│
│      │           │           │           │      │
│      └───────────┴───────────┴───────────┘      │
│                      │                          │
│                      ▼                          │
│              Durable Object                     │
│              (Aggregate Results)                │
└─────────────────────────────────────────────────┘
         │
         ▼
   Webhook / Poll → Final Response
```

---

## Feature Implementation Plan

### Phase 1: Exa Feature Parity

#### 1. Neural/Semantic Search
```typescript
// workers/search.ts
export default {
  async fetch(request, env) {
    const { query } = await request.json();
    
    // Generate query embedding at edge
    const embedding = await env.AI.run('@cf/baai/bge-m3', {
      text: query
    });
    
    // Query Vectorize
    const results = await env.VECTORIZE.query(embedding.data[0], {
      topK: 20,
      filter: { type: 'web_content' }
    });
    
    // Rerank with AI
    const reranked = await env.AI.run('@cf/baai/bge-reranker-base', {
      query,
      documents: results.matches.map(m => m.metadata.content)
    });
    
    return Response.json({ results: reranked });
  }
}
```

#### 2. Auto-Prompting (Query Expansion)
```typescript
// Expand user query for better recall
async function expandQuery(query: string, env: Env) {
  const expansion = await env.AI.run('@cf/openai/gpt-oss-20b', {
    input: `Expand this search query with synonyms and related terms. 
            Return as JSON array of queries.
            Query: "${query}"`,
    reasoning: { effort: 'low' }
  });
  return JSON.parse(expansion.output[1].content[0].text);
}
```

#### 3. Highlights (Key Passages)
```typescript
// Extract key passages from content
async function extractHighlights(content: string, query: string, env: Env) {
  const result = await env.AI.run('@cf/meta/llama-3.1-8b-instruct-fast', {
    messages: [{
      role: 'user',
      content: `Extract the 3 most relevant passages from this content for the query "${query}".
                Return as JSON array with {text, relevance_score}.
                Content: ${content.substring(0, 4000)}`
    }]
  });
  return JSON.parse(result.response);
}
```

#### 4. Similar Content Discovery
```typescript
// Find similar content using vector similarity
async function findSimilar(url: string, env: Env) {
  // Get embedding for the URL's content
  const cached = await env.KV.get(`embed:${url}`);
  if (!cached) return [];
  
  const embedding = JSON.parse(cached);
  
  // Query Vectorize for similar
  const similar = await env.VECTORIZE.query(embedding, {
    topK: 10,
    filter: { url: { $ne: url } }
  });
  
  return similar.matches;
}
```

### Phase 2: Glean Feature Parity

#### 5. Document Connectors
```typescript
// Connector interface
interface DocumentConnector {
  name: string;
  connect(credentials: any): Promise<void>;
  listDocuments(): AsyncGenerator<Document>;
  fetchDocument(id: string): Promise<Document>;
  watchChanges(): AsyncGenerator<ChangeEvent>;
}

// Google Drive connector
class GoogleDriveConnector implements DocumentConnector {
  async *listDocuments() {
    // Paginated document listing
    let pageToken = null;
    do {
      const response = await this.client.files.list({ pageToken });
      for (const file of response.files) {
        yield await this.fetchDocument(file.id);
      }
      pageToken = response.nextPageToken;
    } while (pageToken);
  }
}

// Slack connector
class SlackConnector implements DocumentConnector { ... }

// Confluence connector  
class ConfluenceConnector implements DocumentConnector { ... }

// Notion connector
class NotionConnector implements DocumentConnector { ... }
```

#### 6. Knowledge Graph
```typescript
// Store entities and relationships in Vectorize + D1
interface Entity {
  id: string;
  type: 'person' | 'company' | 'concept' | 'document';
  name: string;
  embedding: number[];
  metadata: Record<string, any>;
}

interface Relationship {
  from: string;
  to: string;
  type: string;
  weight: number;
}

// Build knowledge graph from documents
async function buildKnowledgeGraph(documents: Document[], env: Env) {
  for (const doc of documents) {
    // Extract entities with AI
    const entities = await env.AI.run('@cf/openai/gpt-oss-120b', {
      input: `Extract all entities (people, companies, concepts) from:
              ${doc.content}
              Return as JSON array.`
    });
    
    // Generate embeddings
    const embeddings = await env.AI.run('@cf/baai/bge-m3', {
      text: entities.map(e => e.name)
    });
    
    // Store in Vectorize
    await env.VECTORIZE.upsert(entities.map((e, i) => ({
      id: e.id,
      values: embeddings.data[i],
      metadata: e
    })));
    
    // Store relationships in D1
    await env.DB.batch(relationships.map(r => 
      env.DB.prepare('INSERT INTO relationships VALUES (?, ?, ?, ?)')
        .bind(r.from, r.to, r.type, r.weight)
    ));
  }
}
```

#### 7. People Search
```typescript
// Search for people across connected sources
async function searchPeople(query: string, env: Env) {
  // Vector search for people entities
  const embedding = await env.AI.run('@cf/baai/bge-m3', { text: query });
  
  const people = await env.VECTORIZE.query(embedding.data[0], {
    topK: 20,
    filter: { type: 'person' }
  });
  
  // Enrich with activity data
  const enriched = await Promise.all(people.matches.map(async p => {
    const activity = await env.DB.prepare(
      'SELECT * FROM activity WHERE person_id = ? ORDER BY timestamp DESC LIMIT 10'
    ).bind(p.id).all();
    
    return { ...p.metadata, recentActivity: activity.results };
  }));
  
  return enriched;
}
```

### Phase 3: Groundbreaking Features

#### 8. Real-Time Web Monitoring (Topic Alerts)
```typescript
// Durable Object for persistent monitoring
export class TopicMonitor {
  state: DurableObjectState;
  topics: Map<string, TopicConfig>;
  
  async alarm() {
    // Runs periodically
    for (const [topicId, config] of this.topics) {
      // Search for new content
      const results = await this.searchTopic(config);
      
      // Check against last seen
      const newResults = results.filter(r => 
        r.timestamp > config.lastChecked
      );
      
      if (newResults.length > 0) {
        // Send webhook notification
        await this.notify(config.webhookUrl, newResults);
        
        // Queue for deeper analysis if configured
        if (config.deepAnalysis) {
          await this.env.QUEUE.send({
            type: 'analyze_topic_results',
            topicId,
            results: newResults
          });
        }
      }
      
      config.lastChecked = Date.now();
    }
    
    // Schedule next check
    await this.state.storage.setAlarm(Date.now() + 60000); // 1 min
  }
}
```

#### 9. Autonomous Research Agents
```typescript
// Long-running research agent using Durable Objects + Queues
export class ResearchAgent {
  state: DurableObjectState;
  
  async startResearch(config: ResearchConfig) {
    // Initialize research session
    const sessionId = crypto.randomUUID();
    await this.state.storage.put('session', {
      id: sessionId,
      config,
      status: 'running',
      startedAt: Date.now(),
      progress: 0,
      findings: []
    });
    
    // Generate research plan with reasoning model
    const plan = await this.env.AI.run('@cf/qwen/qwq-32b', {
      messages: [{
        role: 'user',
        content: `Create a detailed research plan for: ${config.topic}
                  Include: search queries, sources to check, analysis steps.
                  Return as JSON.`
      }]
    });
    
    // Enqueue all research tasks
    const tasks = JSON.parse(plan.response);
    for (const task of tasks.queries) {
      await this.env.QUEUE.send({
        type: 'research_query',
        sessionId,
        query: task,
        priority: task.priority
      });
    }
    
    return { sessionId, estimatedTime: tasks.estimatedMinutes };
  }
  
  async aggregateFindings(findings: Finding[]) {
    // Synthesize findings with production model
    const synthesis = await this.env.AI.run('@cf/openai/gpt-oss-120b', {
      input: `Synthesize these research findings into a comprehensive report:
              ${JSON.stringify(findings)}
              
              Include:
              - Executive summary
              - Key findings with evidence
              - Contradictions or debates
              - Confidence levels
              - Recommendations`,
      reasoning: { effort: 'high', summary: 'detailed' }
    });
    
    return synthesis;
  }
}
```

#### 10. Predictive Search (Anticipate Needs)
```typescript
// Predict what user might search next
async function predictiveSearch(userId: string, context: Context, env: Env) {
  // Get user's search history
  const history = await env.KV.get(`history:${userId}`, 'json');
  
  // Get current context (time, location, recent activity)
  const userContext = {
    ...context,
    recentSearches: history?.slice(-10),
    timeOfDay: new Date().getHours(),
    dayOfWeek: new Date().getDay()
  };
  
  // Predict next queries
  const predictions = await env.AI.run('@cf/meta/llama-3.3-70b-instruct-fp8-fast', {
    messages: [{
      role: 'user',
      content: `Based on this user context, predict 5 searches they might make next:
                ${JSON.stringify(userContext)}
                Return as JSON array with {query, confidence, reason}.`
    }]
  });
  
  // Pre-fetch results for top predictions
  const topPredictions = JSON.parse(predictions.response).slice(0, 3);
  for (const pred of topPredictions) {
    // Don't await - fire and forget
    prefetchResults(pred.query, env);
  }
  
  return topPredictions;
}
```

#### 11. Source Verification (Fact-Checking)
```typescript
// Verify claims against multiple sources
async function verifyClaim(claim: string, env: Env) {
  // Search for supporting and contradicting evidence
  const [supporting, contradicting] = await Promise.all([
    searchWithBias(claim, 'supporting', env),
    searchWithBias(claim, 'contradicting', env)
  ]);
  
  // Analyze with reasoning model
  const analysis = await env.AI.run('@cf/qwen/qwq-32b', {
    messages: [{
      role: 'user',
      content: `Analyze this claim for accuracy:
                Claim: "${claim}"
                
                Supporting evidence:
                ${JSON.stringify(supporting)}
                
                Contradicting evidence:
                ${JSON.stringify(contradicting)}
                
                Provide:
                - Verdict (true/false/partially true/unverifiable)
                - Confidence (0-100)
                - Key evidence
                - Nuances/context`
    }]
  });
  
  return {
    claim,
    verdict: analysis.verdict,
    confidence: analysis.confidence,
    supporting: supporting.slice(0, 3),
    contradicting: contradicting.slice(0, 3),
    analysis: analysis.response
  };
}
```

#### 12. Multi-Modal Search
```typescript
// Search across text, images, video
async function multiModalSearch(query: string, modalities: string[], env: Env) {
  const results = await Promise.all([
    // Text search
    modalities.includes('text') && searchText(query, env),
    
    // Image search with vision model
    modalities.includes('images') && searchImages(query, env),
    
    // Video search
    modalities.includes('video') && searchVideo(query, env),
    
    // Audio/podcast search
    modalities.includes('audio') && searchAudio(query, env)
  ]);
  
  // Unified ranking across modalities
  const unified = await unifiedRanking(results.flat(), query, env);
  
  return unified;
}

async function searchImages(query: string, env: Env) {
  // Generate image embedding
  const embedding = await env.AI.run('@cf/baai/bge-m3', { text: query });
  
  // Search image vectors
  const images = await env.VECTORIZE.query(embedding.data[0], {
    topK: 20,
    filter: { type: 'image' }
  });
  
  // Analyze relevance with vision model
  const analyzed = await Promise.all(images.matches.map(async img => {
    const analysis = await env.AI.run('@cf/meta/llama-3.2-11b-vision-instruct', {
      image: img.metadata.url,
      prompt: `Is this image relevant to: "${query}"? Explain briefly.`
    });
    return { ...img, analysis };
  }));
  
  return analyzed;
}
```

---

## Queue-Based Processing Architecture

### Queue Configuration
```typescript
// wrangler.toml
[[queues.producers]]
queue = "search-tasks"
binding = "SEARCH_QUEUE"

[[queues.producers]]
queue = "research-tasks"  
binding = "RESEARCH_QUEUE"

[[queues.producers]]
queue = "crawl-tasks"
binding = "CRAWL_QUEUE"

[[queues.consumers]]
queue = "search-tasks"
max_batch_size = 10
max_batch_timeout = 30
max_retries = 3
dead_letter_queue = "search-dlq"
```

### Queue Consumer
```typescript
export default {
  async queue(batch: MessageBatch, env: Env) {
    for (const message of batch.messages) {
      try {
        switch (message.body.type) {
          case 'search':
            await processSearch(message.body, env);
            break;
          case 'research_query':
            await processResearchQuery(message.body, env);
            break;
          case 'crawl':
            await processCrawl(message.body, env);
            break;
          case 'embed':
            await processEmbedding(message.body, env);
            break;
        }
        message.ack();
      } catch (error) {
        if (message.attempts < 3) {
          message.retry();
        } else {
          // Send to dead letter queue
          await env.DLQ.send(message.body);
          message.ack();
        }
      }
    }
  }
}
```

### Failsafe Processing
```typescript
// Idempotent processing with checkpointing
async function processWithCheckpoint(
  taskId: string, 
  processor: () => Promise<any>,
  env: Env
) {
  // Check if already completed
  const existing = await env.KV.get(`checkpoint:${taskId}`);
  if (existing) return JSON.parse(existing);
  
  // Process with timeout
  const result = await Promise.race([
    processor(),
    new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Timeout')), 25000)
    )
  ]);
  
  // Store checkpoint
  await env.KV.put(`checkpoint:${taskId}`, JSON.stringify(result), {
    expirationTtl: 86400 // 24 hours
  });
  
  return result;
}
```

---

## Data Model (Vectorize + D1)

### Vectorize Indexes
```typescript
// Vector indexes for different content types
const indexes = {
  webContent: {
    dimensions: 1024,  // bge-m3
    metric: 'cosine',
    metadata: ['url', 'title', 'domain', 'timestamp', 'type']
  },
  documents: {
    dimensions: 1024,
    metric: 'cosine', 
    metadata: ['source', 'author', 'created', 'type', 'org_id']
  },
  entities: {
    dimensions: 1024,
    metric: 'cosine',
    metadata: ['name', 'type', 'source_count', 'last_seen']
  },
  users: {
    dimensions: 768,  // Smaller for user preferences
    metric: 'cosine',
    metadata: ['user_id', 'preference_type']
  }
};
```

### D1 Schema
```sql
-- Users and authentication
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE,
  org_id TEXT,
  created_at INTEGER,
  settings JSON
);

-- API keys
CREATE TABLE api_keys (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  key_hash TEXT,
  name TEXT,
  permissions JSON,
  rate_limit INTEGER,
  created_at INTEGER,
  last_used INTEGER
);

-- Usage tracking
CREATE TABLE usage (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  endpoint TEXT,
  tokens_used INTEGER,
  model TEXT,
  timestamp INTEGER
);

-- Knowledge graph relationships
CREATE TABLE relationships (
  id TEXT PRIMARY KEY,
  from_entity TEXT,
  to_entity TEXT,
  type TEXT,
  weight REAL,
  source TEXT,
  timestamp INTEGER
);

-- Topic monitors
CREATE TABLE monitors (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  topic TEXT,
  config JSON,
  last_checked INTEGER,
  status TEXT
);

-- Research sessions
CREATE TABLE research_sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  topic TEXT,
  status TEXT,
  progress REAL,
  findings JSON,
  started_at INTEGER,
  completed_at INTEGER
);

-- Document connectors
CREATE TABLE connectors (
  id TEXT PRIMARY KEY,
  org_id TEXT,
  type TEXT,
  config JSON,
  status TEXT,
  last_sync INTEGER,
  doc_count INTEGER
);
```

---

## API Endpoints (New)

### Exa-Compatible
```
POST /api/v1/search/neural          # Neural/semantic search
POST /api/v1/search/similar         # Find similar content
POST /api/v1/search/highlights      # Extract key passages
GET  /api/v1/search/categories      # Available categories
```

### Glean-Compatible
```
POST /api/v1/connectors             # Add document connector
GET  /api/v1/connectors             # List connectors
POST /api/v1/connectors/{id}/sync   # Trigger sync
GET  /api/v1/people                 # Search people
GET  /api/v1/knowledge/graph        # Query knowledge graph
GET  /api/v1/knowledge/entities     # List entities
```

### Groundbreaking
```
POST /api/v1/monitor/topics         # Create topic monitor
GET  /api/v1/monitor/topics         # List monitors
POST /api/v1/research/agent         # Start research agent
GET  /api/v1/research/agent/{id}    # Check progress
POST /api/v1/verify/claim           # Fact-check claim
POST /api/v1/search/predictive      # Get predicted searches
POST /api/v1/search/multimodal      # Multi-modal search
```

---

## Security Architecture

### Edge Authentication
```typescript
// Auth at edge before any processing
async function authenticate(request: Request, env: Env) {
  const apiKey = request.headers.get('X-API-Key');
  if (!apiKey) throw new Error('Missing API key');
  
  // Check KV cache first
  const cached = await env.KV.get(`auth:${apiKey}`);
  if (cached) return JSON.parse(cached);
  
  // Verify against D1
  const keyHash = await hash(apiKey);
  const key = await env.DB.prepare(
    'SELECT * FROM api_keys WHERE key_hash = ?'
  ).bind(keyHash).first();
  
  if (!key) throw new Error('Invalid API key');
  
  // Cache for 5 minutes
  await env.KV.put(`auth:${apiKey}`, JSON.stringify(key), {
    expirationTtl: 300
  });
  
  return key;
}
```

### Rate Limiting at Edge
```typescript
// Distributed rate limiting with KV
async function rateLimit(userId: string, limit: number, env: Env) {
  const key = `rate:${userId}:${Math.floor(Date.now() / 60000)}`;
  
  const current = await env.KV.get(key, 'json') || { count: 0 };
  
  if (current.count >= limit) {
    throw new Error('Rate limit exceeded');
  }
  
  await env.KV.put(key, JSON.stringify({ count: current.count + 1 }), {
    expirationTtl: 120
  });
}
```

---

## Deployment

### Wrangler Configuration
```toml
name = "unsearch-edge"
main = "src/index.ts"
compatibility_date = "2024-01-01"

[ai]
binding = "AI"

[[vectorize]]
binding = "VECTORIZE"
index_name = "unsearch-main"

[[d1_databases]]
binding = "DB"
database_id = "xxx"

[[kv_namespaces]]
binding = "KV"
id = "xxx"

[[r2_buckets]]
binding = "R2"
bucket_name = "unsearch-storage"

[[queues.producers]]
queue = "tasks"
binding = "QUEUE"

[[queues.consumers]]
queue = "tasks"
max_batch_size = 10

[[durable_objects.bindings]]
name = "RESEARCH_AGENT"
class_name = "ResearchAgent"

[[durable_objects.bindings]]
name = "TOPIC_MONITOR"
class_name = "TopicMonitor"
```

---

## Migration Path

### Phase 1: Edge Router (Week 1)
- Deploy Cloudflare Worker as router
- Forward to existing Python backend
- Implement edge caching

### Phase 2: Vectorize Integration (Week 2)
- Migrate vector store to Vectorize
- Update embedding pipeline
- Parallel operation with existing

### Phase 3: Queue Processing (Week 3)
- Implement Cloudflare Queues
- Migrate batch operations
- Add Durable Objects for state

### Phase 4: Full Edge (Week 4+)
- Migrate remaining services to Workers
- Deprecate Python backend for hot path
- Keep Python for complex operations
