'use client';

import { useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ExternalLink, Code, Zap, Shield } from 'lucide-react';

export default function DocsPage() {
  useEffect(() => {
    // Redirect to Mintlify docs after 3 seconds if user doesn't click anything
    const timer = setTimeout(() => {
      window.location.href = 'https://docs.unquest.ai';
    }, 10000);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="container mx-auto px-4 py-16">
      <div className="mx-auto max-w-4xl">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold tracking-tight mb-4">Documentation</h1>
          <p className="text-xl text-muted-foreground mb-6">
            Complete guides, API reference, and examples for the UnQuest API
          </p>
          <Button size="lg" asChild>
            <a href="https://docs.unquest.ai" target="_blank" rel="noopener noreferrer">
              View Full Documentation <ExternalLink className="ml-2 h-4 w-4" />
            </a>
          </Button>
        </div>

        {/* Quick Links */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 mb-12">
          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-primary" />
                Quickstart
              </CardTitle>
              <CardDescription>Get started in under 5 minutes</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm" asChild>
                <a href="https://docs.unquest.ai/quickstart" target="_blank" rel="noopener noreferrer">
                  Read Guide <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code className="h-5 w-5 text-primary" />
                API Reference
              </CardTitle>
              <CardDescription>Complete endpoint documentation</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm" asChild>
                <a href="https://docs.unquest.ai/api-reference" target="_blank" rel="noopener noreferrer">
                  Browse API <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-primary" />
                Authentication
              </CardTitle>
              <CardDescription>API keys and security</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm" asChild>
                <a href="https://docs.unquest.ai/authentication" target="_blank" rel="noopener noreferrer">
                  Learn More <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Quick Examples */}
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Python SDK</CardTitle>
              <CardDescription>pip install unsearch</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="rounded-md bg-muted p-4 text-sm overflow-x-auto">
{`from unsearch import Client

client = Client(api_key="USK_...")
resp = client.unified.query(
  q="What is RAG?", 
  k=5, 
  output_format="markdown"
)

for doc in resp.documents:
  print(doc.title)
  print(doc.content[:200])
`}
              </pre>
              <Button variant="ghost" size="sm" className="mt-2" asChild>
                <a href="https://docs.unquest.ai/quickstart#python" target="_blank" rel="noopener noreferrer">
                  Full Python Guide <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>TypeScript SDK</CardTitle>
              <CardDescription>npm i @unsearch/sdk</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="rounded-md bg-muted p-4 text-sm overflow-x-auto">
{`import { Unsearch } from '@unsearch/sdk'

const client = new Unsearch({ 
  apiKey: process.env.UNSEARCH_API_KEY! 
})

const { documents } = await client.unified.query({
  q: 'RAG overview', 
  k: 3,
  outputFormat: 'markdown'
})

console.log(documents.length)
`}
              </pre>
              <Button variant="ghost" size="sm" className="mt-2" asChild>
                <a href="https://docs.unquest.ai/quickstart#nodejs" target="_blank" rel="noopener noreferrer">
                  Full Node.js Guide <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Popular Sections */}
        <div className="mt-12 text-center">
          <h2 className="text-2xl font-semibold mb-6">Popular Documentation Sections</h2>
          <div className="flex flex-wrap justify-center gap-3">
            {[
              { name: 'Search API', url: '/api-reference/search' },
              { name: 'Batch Processing', url: '/features/batch-processing' },
              { name: 'Rate Limits', url: '/rate-limits' },
              { name: 'Webhooks', url: '/features/webhooks' },
              { name: 'Billing', url: '/api-reference/billing' },
              { name: 'Examples', url: '/examples' }
            ].map((item) => (
              <Button key={item.name} variant="outline" size="sm" asChild>
                <a href={`https://docs.unquest.ai${item.url}`} target="_blank" rel="noopener noreferrer">
                  {item.name} <ExternalLink className="ml-1 h-3 w-3" />
                </a>
              </Button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}


