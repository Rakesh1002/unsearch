import { QueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 30, // 30 minutes (formerly cacheTime)
      retry: (failureCount, error) => {
        const axiosError = error as AxiosError;
        // Don't retry on 401, 403, 404
        if (axiosError?.response?.status === 401 || 
            axiosError?.response?.status === 403 || 
            axiosError?.response?.status === 404) {
          return false;
        }
        // Retry up to 3 times for other errors
        return failureCount < 3;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      retry: false,
    },
  },
});

// Query keys factory
export const queryKeys = {
  all: ['unsearch'] as const,
  
  // Auth queries
  auth: () => [...queryKeys.all, 'auth'] as const,
  currentUser: () => [...queryKeys.auth(), 'current-user'] as const,
  
  // API Keys queries
  apiKeys: () => [...queryKeys.all, 'api-keys'] as const,
  allAPIKeys: () => [...queryKeys.apiKeys(), 'list'] as const,
  
  // Search queries
  search: () => [...queryKeys.all, 'search'] as const,
  searchEngines: () => [...queryKeys.search(), 'engines'] as const,
  searchHistory: () => [...queryKeys.search(), 'history'] as const,
  
  // Billing queries
  billing: () => [...queryKeys.all, 'billing'] as const,
  subscription: () => [...queryKeys.billing(), 'subscription'] as const,
  plans: () => [...queryKeys.billing(), 'plans'] as const,
  usage: () => [...queryKeys.billing(), 'usage'] as const,
  invoices: () => [...queryKeys.billing(), 'invoices'] as const,
} as const;
