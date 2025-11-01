import { z } from 'zod';

// User types
export interface User {
  id: number;
  email: string;
  full_name?: string;
  company?: string;
  is_verified: boolean;
  is_active: boolean;
  plan: 'free' | 'pro' | 'enterprise';
  created_at: string;
  updated_at?: string;
  last_login_at?: string;
}

// API Key types
export interface APIKey {
  id: number;
  key: string;
  name: string;
  description?: string;
  scopes: string[];
  is_active: boolean;
  created_at: string;
  last_used_at?: string;
  expires_at?: string;
  request_count: number;
}

// Auth request/response types
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
  company?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface CreateAPIKeyRequest {
  name: string;
  description?: string;
  scopes?: string[];
}

// Validation schemas
export const LoginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required')
});

export const RegisterSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/, 'Password must contain at least one uppercase letter, one lowercase letter, and one number'),
  full_name: z.string().optional(),
  company: z.string().optional()
});

export const CreateAPIKeySchema = z.object({
  name: z.string().min(1, 'API key name is required').max(255, 'Name too long'),
  description: z.string().max(1000, 'Description too long').optional(),
  scopes: z.array(z.string()).optional()
});

export type LoginFormData = z.infer<typeof LoginSchema>;
export type RegisterFormData = z.infer<typeof RegisterSchema>;
export type CreateAPIKeyFormData = z.infer<typeof CreateAPIKeySchema>;
