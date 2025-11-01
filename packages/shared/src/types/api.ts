import { z } from 'zod';

// Search types
export interface SearchRequest {
  query: string;
  engines?: string[];
  language?: string;
  safe_search?: 'strict' | 'moderate' | 'off';
  time_range?: string;
  max_results?: number;
  include_images?: boolean;
  include_videos?: boolean;
  scrape_results?: boolean;
  scrape_options?: ScrapeOptions;
  webhook_url?: string;
  metadata?: Record<string, any>;
}

export interface ScrapeOptions {
  css_selector?: string;
  extract_images?: boolean;
  extract_links?: boolean;
  extract_metadata?: boolean;
  respect_robots_txt?: boolean;
  timeout_seconds?: number;
}

export interface SearchResult {
  title: string;
  url: string;
  content: string;
  engine: string;
  score: number;
  timestamp: string;
  scraped_content?: ScrapedContent;
}

export interface ScrapedContent {
  title: string;
  content: string;
  cleaned_content: string;
  word_count: number;
  language?: string;
  images: string[];
  links: Link[];
  metadata: ContentMetadata;
  quality_score: number;
}

export interface ContentMetadata {
  description?: string;
  author?: string;
  publish_date?: string;
  last_modified?: string;
  keywords: string[];
  og_data: Record<string, string>;
  twitter_data: Record<string, string>;
  json_ld: Record<string, any>[];
}

export interface Link {
  url: string;
  text: string;
  is_external: boolean;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
  search_time: number;
  engines_used: string[];
  request_id: string;
  cached: boolean;
  timestamp: string;
}

export interface BatchSearchRequest {
  queries: SearchRequest[];
  webhook_url?: string;
  metadata?: Record<string, any>;
}

export interface BatchSearchResponse {
  batch_id: string;
  total_queries: number;
  estimated_completion_time: number;
  webhook_url?: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
}

// Error types
export interface APIError {
  error: string;
  message: string;
  details?: Record<string, any>;
  request_id: string;
  timestamp: string;
}

// Validation schemas
export const SearchRequestSchema = z.object({
  query: z.string().min(1, 'Query is required').max(500, 'Query too long'),
  engines: z.array(z.string()).optional(),
  language: z.string().length(2).optional(),
  safe_search: z.enum(['strict', 'moderate', 'off']).optional(),
  time_range: z.string().optional(),
  max_results: z.number().min(1).max(100).optional(),
  include_images: z.boolean().optional(),
  include_videos: z.boolean().optional(),
  scrape_results: z.boolean().optional(),
  webhook_url: z.string().url().optional(),
  scrape_options: z.object({
    css_selector: z.string().optional(),
    extract_images: z.boolean().optional(),
    extract_links: z.boolean().optional(),
    extract_metadata: z.boolean().optional(),
    respect_robots_txt: z.boolean().optional(),
    timeout_seconds: z.number().min(1).max(60).optional()
  }).optional()
});

export const BatchSearchRequestSchema = z.object({
  queries: z.array(SearchRequestSchema).min(1).max(50),
  webhook_url: z.string().url().optional()
});

export type SearchFormData = z.infer<typeof SearchRequestSchema>;
export type BatchSearchFormData = z.infer<typeof BatchSearchRequestSchema>;
