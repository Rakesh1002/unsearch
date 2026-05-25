import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient, handleAPIError } from '../api';
import { queryKeys } from '../query-client';
import type { 
  CreateSubscriptionRequest
} from '@unsearch/shared';
import { toast } from 'sonner';

// Get current subscription
export function useSubscription() {
  return useQuery({
    queryKey: queryKeys.subscription(),
    queryFn: () => apiClient.getSubscription(),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });
}

// Get available plans
export function usePlans() {
  return useQuery({
    queryKey: queryKeys.plans(),
    queryFn: () => apiClient.getPlans(),
    staleTime: 1000 * 60 * 15, // 15 minutes - plans don't change often
  });
}

// Get usage statistics
export function useUsage() {
  return useQuery({
    queryKey: queryKeys.usage(),
    queryFn: () => apiClient.getUsage(),
    staleTime: 1000 * 60 * 2, // 2 minutes
  });
}

// Create subscription mutation
export function useCreateSubscription() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: CreateSubscriptionRequest) => apiClient.createSubscription(data),
    onSuccess: () => {
      // Invalidate subscription and usage queries
      queryClient.invalidateQueries({ queryKey: queryKeys.subscription() });
      queryClient.invalidateQueries({ queryKey: queryKeys.usage() });
      queryClient.invalidateQueries({ queryKey: queryKeys.currentUser() });
      
      toast.success('Subscription created successfully');
    },
    onError: (error) => {
      toast.error(handleAPIError(error));
    },
  });
}

// Cancel subscription mutation
export function useCancelSubscription() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => apiClient.cancelSubscription(),
    onSuccess: () => {
      // Invalidate subscription query
      queryClient.invalidateQueries({ queryKey: queryKeys.subscription() });
      queryClient.invalidateQueries({ queryKey: queryKeys.currentUser() });
      
      toast.success('Subscription cancelled successfully');
    },
    onError: (error) => {
      toast.error(handleAPIError(error));
    },
  });
}

// Get billing portal URL mutation
export function useBillingPortal() {
  return useMutation({
    mutationFn: () => apiClient.getBillingPortal(),
    onSuccess: (data) => {
      // Redirect to Stripe billing portal
      window.location.href = data.url;
    },
    onError: (error) => {
      toast.error(handleAPIError(error));
    },
  });
}
