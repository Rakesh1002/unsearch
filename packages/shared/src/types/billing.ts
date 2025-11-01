import { z } from 'zod';

// Plan types
export type PlanType = 'FREE' | 'PRO' | 'ENTERPRISE';
export type SubscriptionStatus = 'ACTIVE' | 'TRIALING' | 'CANCELLED' | 'PAST_DUE' | 'UNPAID' | 'INCOMPLETE';

export interface Plan {
  id: number;
  name: string;
  type: PlanType;
  price_monthly: number;
  price_yearly?: number;
  stripe_price_id: string;
  stripe_price_id_yearly?: string;
  features: PlanFeatures;
  is_active: boolean;
}

export interface PlanFeatures {
  max_searches_per_month: number | null; // null = unlimited
  max_scrapes_per_month: number | null;
  rate_limit_per_minute: number;
  api_keys_limit: number | null;
  webhook_support: boolean;
  priority_support: boolean;
  custom_rate_limits: boolean;
}

export interface Subscription {
  id: number;
  user_id: number;
  plan_id: number;
  status: SubscriptionStatus;
  stripe_subscription_id?: string;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  created_at: string;
  updated_at?: string;
  plan: Plan;
}

export interface UsageRecord {
  id: number;
  user_id: number;
  month: string; // Format: YYYY-MM
  searches_count: number;
  scrapes_count: number;
  api_calls_count: number;
  created_at: string;
  updated_at?: string;
}

export interface Invoice {
  id: number;
  user_id: number;
  stripe_invoice_id?: string;
  amount: number;
  currency: string;
  status: string;
  period_start: string;
  period_end: string;
  invoice_url?: string;
  created_at: string;
  paid_at?: string;
}

// Request/Response types
export interface CreateSubscriptionRequest {
  plan_id: number;
  payment_method_id?: string;
}

export interface UpdateSubscriptionRequest {
  plan_id?: number;
  cancel_at_period_end?: boolean;
}

export interface BillingPortalRequest {
  return_url?: string;
}

export interface BillingPortalResponse {
  url: string;
}

// Validation schemas
export const CreateSubscriptionSchema = z.object({
  plan_id: z.number().positive('Invalid plan ID'),
  payment_method_id: z.string().optional()
});

export const UpdateSubscriptionSchema = z.object({
  plan_id: z.number().positive('Invalid plan ID').optional(),
  cancel_at_period_end: z.boolean().optional()
});

export type CreateSubscriptionFormData = z.infer<typeof CreateSubscriptionSchema>;
export type UpdateSubscriptionFormData = z.infer<typeof UpdateSubscriptionSchema>;
