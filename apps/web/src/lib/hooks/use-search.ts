import { useMutation, useQuery } from '@tanstack/react-query';
import { apiClient, handleAPIError } from '../api';
import { queryKeys } from '../query-client';
import type { 
  SearchRequest, 
  BatchSearchRequest, 
  BatchSearchResponse 
} from '@unsearch/shared';
import { toast } from 'sonner';

// Get available search engines
export function useSearchEngines() {
  return useQuery({
    queryKey: queryKeys.searchEngines(),
    queryFn: () => apiClient.getSearchEngines(),
    staleTime: 1000 * 60 * 30, // 30 minutes - engines list doesn't change often
  });
}

// Single search mutation
export function useSearch() {
  return useMutation({
    mutationFn: (query: SearchRequest) => apiClient.search(query),
    onError: (error) => {
      toast.error(handleAPIError(error));
    },
  });
}

// Batch search mutation
export function useBatchSearch() {
  return useMutation({
    mutationFn: (queries: BatchSearchRequest) => apiClient.batchSearch(queries),
    onSuccess: (data: BatchSearchResponse) => {
      toast.success(`Batch search queued with ${data.total_queries} queries`);
    },
    onError: (error) => {
      toast.error(handleAPIError(error));
    },
  });
}

// Custom hook for managing search state
export function useSearchState() {
  const searchMutation = useSearch();
  const batchSearchMutation = useBatchSearch();
  
  return {
    // Single search
    search: searchMutation.mutate,
    searchAsync: searchMutation.mutateAsync,
    searchResult: searchMutation.data,
    isSearching: searchMutation.isPending,
    searchError: searchMutation.error,
    
    // Batch search
    batchSearch: batchSearchMutation.mutate,
    batchSearchAsync: batchSearchMutation.mutateAsync,
    batchSearchResult: batchSearchMutation.data,
    isBatchSearching: batchSearchMutation.isPending,
    batchSearchError: batchSearchMutation.error,
    
    // Combined loading state
    isLoading: searchMutation.isPending || batchSearchMutation.isPending,
    
    // Reset functions
    resetSearch: () => {
      searchMutation.reset();
      batchSearchMutation.reset();
    },
  };
}
