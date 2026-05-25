import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import type {
  User,
  LoginRequest,
  RegisterRequest,
  LoginResponse,
  APIKey,
  CreateAPIKeyRequest,
  SearchRequest,
  SearchResponse,
  BatchSearchRequest,
  BatchSearchResponse,
  Subscription,
  Plan,
  CreateSubscriptionRequest,
  BillingPortalResponse,
  UsageRecord
} from '@unsearch/shared';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class APIClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_BASE_URL}/api/v1`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Load tokens from localStorage if available
    if (typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('access_token');
      this.refreshToken = localStorage.getItem('refresh_token');
    }

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        if (this.accessToken) {
          config.headers.Authorization = `Bearer ${this.accessToken}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor to handle token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            await this.refreshAccessToken();
            if (this.accessToken && originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${this.accessToken}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            this.logout();
            throw refreshError;
          }
        }

        throw error;
      }
    );
  }

  // Auth Methods
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.client.post<LoginResponse>('/auth/login', credentials);
    const { access_token, refresh_token } = response.data;
    
    this.setTokens(access_token, refresh_token);
    return response.data;
  }

  async register(userData: RegisterRequest): Promise<User> {
    const response = await this.client.post<User>('/auth/register', userData);
    return response.data;
  }

  async refreshAccessToken(): Promise<void> {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await this.client.post<{ access_token: string; refresh_token: string }>(
      '/auth/refresh',
      { refresh_token: this.refreshToken }
    );

    const { access_token, refresh_token } = response.data;
    this.setTokens(access_token, refresh_token);
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/auth/me');
    return response.data;
  }

  async updateUser(updates: Partial<Pick<User, 'full_name' | 'company'>>): Promise<User> {
    const response = await this.client.patch<User>('/auth/me', updates);
    return response.data;
  }

  logout(): void {
    this.accessToken = null;
    this.refreshToken = null;
    
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  }

  private setTokens(accessToken: string, refreshToken: string): void {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);
    }
  }

  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  // API Key Methods
  async getAPIKeys(): Promise<APIKey[]> {
    const response = await this.client.get<APIKey[]>('/auth/api-keys');
    return response.data;
  }

  async createAPIKey(data: CreateAPIKeyRequest): Promise<APIKey> {
    const response = await this.client.post<APIKey>('/auth/api-keys', data);
    return response.data;
  }

  async deleteAPIKey(keyId: number): Promise<void> {
    await this.client.delete(`/auth/api-keys/${keyId}`);
  }

  // Search Methods
  async search(query: SearchRequest): Promise<SearchResponse> {
    const response = await this.client.post<SearchResponse>('/search', query);
    return response.data;
  }

  async batchSearch(queries: BatchSearchRequest): Promise<BatchSearchResponse> {
    const response = await this.client.post<BatchSearchResponse>('/search/batch', queries);
    return response.data;
  }

  async getSearchEngines(): Promise<string[]> {
    const response = await this.client.get<string[]>('/search/engines');
    return response.data;
  }

  // Billing Methods
  async getSubscription(): Promise<Subscription | null> {
    try {
      const response = await this.client.get<Subscription>('/billing/subscription');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null; // No subscription found
      }
      throw error;
    }
  }

  async getPlans(): Promise<Plan[]> {
    const response = await this.client.get<Plan[]>('/billing/plans');
    return response.data;
  }

  async createSubscription(data: CreateSubscriptionRequest): Promise<{ client_secret: string }> {
    const response = await this.client.post('/billing/subscription', data);
    return response.data;
  }

  async cancelSubscription(): Promise<void> {
    await this.client.delete('/billing/subscription');
  }

  async getBillingPortal(): Promise<BillingPortalResponse> {
    const response = await this.client.post<BillingPortalResponse>('/billing/portal');
    return response.data;
  }

  async getUsage(): Promise<UsageRecord | null> {
    try {
      const response = await this.client.get<UsageRecord>('/billing/usage');
      return response.data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        return null;
      }
      throw error;
    }
  }

  // Health Check
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get<{ status: string }>('/health');
    return response.data;
  }
}

// Export singleton instance
export const apiClient = new APIClient();

// Error handling helper
export const handleAPIError = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    if (error.response?.data?.message) {
      return error.response.data.message;
    }
    if (error.response?.data?.detail) {
      return error.response.data.detail;
    }
    if (error.message) {
      return error.message;
    }
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return 'An unexpected error occurred';
};
