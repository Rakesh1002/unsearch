'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { CreateAPIKeySchema, type CreateAPIKeyFormData } from '@unsearch/shared';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Checkbox } from '@/components/ui/checkbox';

interface CreateAPIKeyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (data: CreateAPIKeyFormData) => Promise<void>;
}

const AVAILABLE_SCOPES = [
  { value: 'read', label: 'Read', description: 'Read access to search and scrape' },
  { value: 'write', label: 'Write', description: 'Write access for batch operations' },
  { value: 'admin', label: 'Admin', description: 'Administrative operations' },
];

export function CreateAPIKeyDialog({ open, onOpenChange, onCreate }: CreateAPIKeyDialogProps) {
  const [loading, setLoading] = useState(false);
  const [selectedScopes, setSelectedScopes] = useState<string[]>(['read', 'write']);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<CreateAPIKeyFormData>({
    resolver: zodResolver(CreateAPIKeySchema),
    defaultValues: {
      scopes: ['read', 'write'],
    },
  });

  const onSubmit = async (data: CreateAPIKeyFormData) => {
    setLoading(true);
    try {
      await onCreate({
        ...data,
        scopes: selectedScopes,
      });
      reset();
      setSelectedScopes(['read', 'write']);
      onOpenChange(false);
    } catch (error) {
      // Error is handled by the parent component
      console.error('Failed to create API key:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleScope = (scope: string) => {
    setSelectedScopes(prev => {
      if (prev.includes(scope)) {
        return prev.filter(s => s !== scope);
      } else {
        return [...prev, scope];
      }
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create New API Key</DialogTitle>
          <DialogDescription>
            Create a new API key to access the UnSearch API. Keep your API key secure and never share it publicly.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Key Name *</Label>
            <Input
              id="name"
              placeholder="e.g., Production API Key"
              {...register('name')}
              className={errors.name ? 'border-destructive' : ''}
            />
            {errors.name && (
              <p className="text-sm text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Optional description for this API key"
              {...register('description')}
              className={errors.description ? 'border-destructive' : ''}
              rows={3}
            />
            {errors.description && (
              <p className="text-sm text-destructive">{errors.description.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label>Permissions</Label>
            <div className="space-y-3">
              {AVAILABLE_SCOPES.map((scope) => (
                <div key={scope.value} className="flex items-start space-x-3">
                  <Checkbox
                    id={scope.value}
                    checked={selectedScopes.includes(scope.value)}
                    onCheckedChange={() => toggleScope(scope.value)}
                  />
                  <div className="flex-1">
                    <label
                      htmlFor={scope.value}
                      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                    >
                      {scope.label}
                    </label>
                    <p className="text-xs text-muted-foreground mt-1">
                      {scope.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button type="submit" loading={loading} disabled={loading}>
              {loading ? 'Creating...' : 'Create API Key'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
