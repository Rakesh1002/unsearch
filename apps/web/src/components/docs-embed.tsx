'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ExternalLink, Maximize2, Minimize2 } from 'lucide-react';

interface DocsEmbedProps {
  title: string;
  url: string;
  height?: number;
  className?: string;
}

export function DocsEmbed({ title, url, height = 600, className }: DocsEmbedProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-lg">{title}</CardTitle>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </Button>
          <Button variant="ghost" size="sm" asChild>
            <a href={url} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4" />
            </a>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <iframe
          src={url}
          className="w-full border-0 rounded-b-lg"
          style={{ height: isExpanded ? '80vh' : `${height}px` }}
          title={title}
          loading="lazy"
        />
      </CardContent>
    </Card>
  );
}

// Usage example component
export function QuickDocsSection() {
  return (
    <div className="space-y-6">
      <DocsEmbed
        title="API Quickstart"
        url="https://docs.unquest.ai/quickstart"
        height={400}
      />
      
      <div className="grid gap-6 md:grid-cols-2">
        <DocsEmbed
          title="Authentication"
          url="https://docs.unquest.ai/authentication"
          height={300}
        />
        <DocsEmbed
          title="API Reference"
          url="https://docs.unquest.ai/api-reference"
          height={300}
        />
      </div>
    </div>
  );
}
