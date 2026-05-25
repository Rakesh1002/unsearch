'use client';

import { useState } from 'react';
import { APIKey } from '@unsearch/shared';
import { formatDateTime, maskAPIKey, copyToClipboard } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Copy, Eye, EyeOff, Trash2, Plus } from 'lucide-react';
import { toast } from 'sonner';

interface APIKeysTableProps {
  apiKeys: APIKey[];
  onDelete: (keyId: number) => void;
  onCreateNew: () => void;
  isLoading?: boolean;
}

export function APIKeysTable({ apiKeys, onDelete, onCreateNew, isLoading }: APIKeysTableProps) {
  const [visibleKeys, setVisibleKeys] = useState<Set<number>>(new Set());

  const toggleKeyVisibility = (keyId: number) => {
    setVisibleKeys(prev => {
      const newSet = new Set(prev);
      if (newSet.has(keyId)) {
        newSet.delete(keyId);
      } else {
        newSet.add(keyId);
      }
      return newSet;
    });
  };

  const handleCopy = async (key: string) => {
    try {
      await copyToClipboard(key);
      toast.success('API key copied to clipboard');
    } catch (error) {
      toast.error('Failed to copy API key');
    }
  };

  const handleDelete = (keyId: number, keyName: string) => {
    if (confirm(`Are you sure you want to delete the API key "${keyName}"? This action cannot be undone.`)) {
      onDelete(keyId);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>API Keys</CardTitle>
          <CardDescription>Loading your API keys...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-3">
            <div className="h-10 bg-muted rounded"></div>
            <div className="h-10 bg-muted rounded"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>API Keys</CardTitle>
            <CardDescription>
              Manage your API keys for accessing the UnSearch API
            </CardDescription>
          </div>
          <Button onClick={onCreateNew} size="sm">
            <Plus className="mr-2 h-4 w-4" />
            Create New Key
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {apiKeys.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-muted-foreground mb-4">
              You haven&apos;t created any API keys yet.
            </p>
            <Button onClick={onCreateNew}>
              <Plus className="mr-2 h-4 w-4" />
              Create Your First API Key
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {apiKeys.map((apiKey) => (
              <div
                key={apiKey.id}
                className="border rounded-lg p-4 space-y-2"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-semibold">{apiKey.name}</h4>
                      {apiKey.is_active ? (
                        <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded-full">
                          Active
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded-full">
                          Inactive
                        </span>
                      )}
                    </div>
                    {apiKey.description && (
                      <p className="text-sm text-muted-foreground mt-1">
                        {apiKey.description}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDelete(apiKey.id, apiKey.name)}
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <code className="flex-1 px-3 py-2 bg-muted rounded text-sm font-mono">
                      {visibleKeys.has(apiKey.id) ? apiKey.key : maskAPIKey(apiKey.key)}
                    </code>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleKeyVisibility(apiKey.id)}
                    >
                      {visibleKeys.has(apiKey.id) ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopy(apiKey.key)}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>

                  <div className="flex gap-4 text-xs text-muted-foreground">
                    <span>Created: {formatDateTime(apiKey.created_at)}</span>
                    {apiKey.last_used_at && (
                      <span>Last used: {formatDateTime(apiKey.last_used_at)}</span>
                    )}
                    {apiKey.request_count > 0 && (
                      <span>Used {apiKey.request_count} times</span>
                    )}
                    {apiKey.expires_at && (
                      <span className="text-yellow-600">
                        Expires: {formatDateTime(apiKey.expires_at)}
                      </span>
                    )}
                  </div>

                  {apiKey.scopes && apiKey.scopes.length > 0 && (
                    <div className="flex gap-2 text-xs">
                      <span className="text-muted-foreground">Scopes:</span>
                      {apiKey.scopes.map((scope) => (
                        <span
                          key={scope}
                          className="px-2 py-1 bg-muted rounded"
                        >
                          {scope}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
