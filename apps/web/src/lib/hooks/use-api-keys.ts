import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, handleAPIError } from '../api';
import { queryKeys } from '../query-client';
import type { APIKey, CreateAPIKeyRequest } from '@unsearch/shared';
import { toast } from 'sonner';

// Get all API keys
export function useAPIKeys() {
  return useQuery({
    queryKey: queryKeys.allAPIKeys(),
    queryFn: () => apiClient.getAPIKeys(),
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
}

// Create API key mutation
export function useCreateAPIKey() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: CreateAPIKeyRequest) => apiClient.createAPIKey(data),
    onSuccess: (newAPIKey: APIKey) => {
      // Update the API keys list
      queryClient.setQueryData(
        queryKeys.allAPIKeys(),
        (oldData: APIKey[] | undefined) => {
          if (!oldData) return [newAPIKey];
          return [...oldData, newAPIKey];
        }
      );
      
      toast.success('API key created successfully');
    },
    onError: (error) => {
      toast.error(handleAPIError(error));
    },
  });
}

// Delete API key mutation
export function useDeleteAPIKey() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (keyId: number) => apiClient.deleteAPIKey(keyId),
    onSuccess: (_, keyId) => {
      // Remove the deleted API key from the list
      queryClient.setQueryData(
        queryKeys.allAPIKeys(),
        (oldData: APIKey[] | undefined) => {
          if (!oldData) return [];
          return oldData.filter(key => key.id !== keyId);
        }
      );
      
      toast.success('API key deleted successfully');
    },
    onError: (error) => {
      toast.error(handleAPIError(error));
    },
  });
}
