"use client";
import { useEffect, useState } from 'react';
import { apiClient, handleAPIError } from '@/lib/api';
import type { APIKey } from '@unsearch/shared';

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchKeys = async () => {
    try {
      setError(null);
      const data = await apiClient.getAPIKeys();
      setKeys(data);
    } catch (e) {
      setError(handleAPIError(e));
    }
  };

  useEffect(() => { fetchKeys(); }, []);

  const createKey = async () => {
    try {
      setLoading(true);
      await apiClient.createAPIKey({ name, description });
      setName(''); setDescription('');
      await fetchKeys();
    } catch (e) {
      setError(handleAPIError(e));
    } finally {
      setLoading(false);
    }
  };

  const deleteKey = async (id: number) => {
    try {
      setLoading(true);
      await apiClient.deleteAPIKey(id);
      await fetchKeys();
    } catch (e) {
      setError(handleAPIError(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-6">
      <h1 className="text-2xl font-semibold mb-4">API Keys</h1>
      {error && <div className="mb-3 text-red-600 text-sm">{error}</div>}
      <div className="border rounded-md p-4 mb-6">
        <h2 className="font-medium mb-3">Create new key</h2>
        <div className="flex gap-2">
          <input className="border px-2 py-1 rounded w-40" value={name} onChange={e => setName(e.target.value)} placeholder="Name" />
          <input className="border px-2 py-1 rounded flex-1" value={description} onChange={e => setDescription(e.target.value)} placeholder="Description (optional)" />
          <button onClick={createKey} disabled={loading || !name} className="border px-3 py-1 rounded hover:bg-muted disabled:opacity-50">Create</button>
        </div>
      </div>
      <div className="border rounded-md">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left border-b">
              <th className="p-2">Name</th>
              <th className="p-2">Key</th>
              <th className="p-2">Created</th>
              <th className="p-2"></th>
            </tr>
          </thead>
          <tbody>
            {keys.map(k => (
              <tr key={k.id} className="border-b">
                <td className="p-2">{k.name}</td>
                <td className="p-2 font-mono text-xs">{k.key}</td>
                <td className="p-2">{k.created_at ? new Date(k.created_at as unknown as string).toLocaleString() : ''}</td>
                <td className="p-2 text-right">
                  <button onClick={() => deleteKey(k.id)} className="border px-2 py-1 rounded hover:bg-red-50">Delete</button>
                </td>
              </tr>
            ))}
            {keys.length === 0 && (
              <tr><td className="p-3 text-muted-foreground" colSpan={4}>No keys yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
