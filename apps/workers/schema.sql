-- UnSearch D1 schema — consolidated from alembic revisions 001-005.
-- SQLite dialect for Cloudflare D1.
-- Translations:
--   BIGSERIAL/Integer PK     -> INTEGER PRIMARY KEY AUTOINCREMENT
--   String(N)/Text           -> TEXT
--   Boolean                  -> INTEGER (0/1)
--   JSON/JSONB               -> TEXT (stored as JSON string; use json() helpers)
--   Float                    -> REAL
--   DateTime(timezone=True)  -> TEXT (ISO 8601 UTC)
--   server_default=now()     -> DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
--   ENUM                     -> TEXT with CHECK constraint

PRAGMA foreign_keys = ON;

-- =========================================================================
-- users (alembic 002 + 004)
-- =========================================================================
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL,
    email TEXT NOT NULL,
    username TEXT,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    full_name TEXT,
    company TEXT,
    phone TEXT,
    timezone TEXT DEFAULT 'UTC',
    is_active INTEGER DEFAULT 1,
    is_verified INTEGER DEFAULT 0,
    is_admin INTEGER DEFAULT 0,
    email_verified_at TEXT,
    verification_token TEXT,
    reset_token TEXT,
    reset_token_expires TEXT,
    stripe_customer_id TEXT,
    stripe_payment_method_id TEXT,
    -- agent self-registration (004)
    is_agent_placeholder INTEGER DEFAULT 0,
    agent_name TEXT,
    agent_description TEXT,
    claim_code TEXT,
    claimed_at TEXT,
    daily_searches_used INTEGER DEFAULT 0,
    daily_reset_at TEXT,
    sandbox_expires_at TEXT,
    is_sandbox_expired INTEGER DEFAULT 0,
    registration_ip TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT,
    last_login_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_uuid ON users(uuid);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_stripe ON users(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_agent_name ON users(agent_name) WHERE agent_name IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_claim_code ON users(claim_code) WHERE claim_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_agent_placeholder ON users(is_agent_placeholder);

-- =========================================================================
-- api_keys (alembic 001; user_id added in 002)
-- =========================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    user_id INTEGER REFERENCES users(id),
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    last_used_at TEXT,
    is_active INTEGER DEFAULT 1,
    rate_limit_override TEXT,
    metadata TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(key);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);

-- =========================================================================
-- user_api_keys (alembic 002) — per-user scoped keys (separate from legacy api_keys)
-- =========================================================================
CREATE TABLE IF NOT EXISTS user_api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    scopes TEXT,
    ip_whitelist TEXT,
    last_used_at TEXT,
    request_count INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    expires_at TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_api_keys_key ON user_api_keys(key);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_active ON user_api_keys(is_active);
CREATE INDEX IF NOT EXISTS idx_user_api_keys_user ON user_api_keys(user_id);

-- =========================================================================
-- search_requests (alembic 001)
-- =========================================================================
CREATE TABLE IF NOT EXISTS search_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL,
    api_key_id INTEGER REFERENCES api_keys(id),
    query TEXT NOT NULL,
    engines TEXT NOT NULL,
    max_results INTEGER NOT NULL,
    language TEXT,
    safe_search TEXT,
    search_time_ms INTEGER,
    scraping_time_ms INTEGER,
    total_time_ms INTEGER,
    results_count INTEGER,
    scraped_count INTEGER,
    cache_hit INTEGER DEFAULT 0,
    cache_key TEXT,
    client_ip TEXT,
    user_agent TEXT,
    request_headers TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    completed_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_search_requests_request_id ON search_requests(request_id);
CREATE INDEX IF NOT EXISTS idx_search_requests_cache_key ON search_requests(cache_key);
CREATE INDEX IF NOT EXISTS idx_search_requests_created ON search_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_search_requests_query ON search_requests(query);

-- =========================================================================
-- search_results (alembic 001)
-- =========================================================================
CREATE TABLE IF NOT EXISTS search_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL REFERENCES search_requests(id),
    rank INTEGER NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    snippet TEXT,
    engine TEXT NOT NULL,
    score REAL,
    scraped_successfully INTEGER DEFAULT 0,
    scraped_content TEXT,
    scraping_error TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_search_results_request ON search_results(request_id);
CREATE INDEX IF NOT EXISTS idx_search_results_url ON search_results(url);

-- =========================================================================
-- scraping_jobs (alembic 001) — async batch scraping
-- =========================================================================
CREATE TABLE IF NOT EXISTS scraping_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    task_id TEXT,
    urls TEXT NOT NULL,
    config TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','running','completed','failed','cancelled')),
    results TEXT,
    error_message TEXT,
    webhook_url TEXT,
    webhook_attempts INTEGER DEFAULT 0,
    webhook_last_attempt TEXT,
    webhook_success INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    started_at TEXT,
    completed_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_scraping_jobs_job_id ON scraping_jobs(job_id);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_created ON scraping_jobs(created_at);
CREATE INDEX IF NOT EXISTS idx_scraping_jobs_status ON scraping_jobs(status);

-- =========================================================================
-- cache_entries (alembic 001) — analytics only; hot cache lives in KV
-- =========================================================================
CREATE TABLE IF NOT EXISTS cache_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT NOT NULL,
    query_hash TEXT NOT NULL,
    size_bytes INTEGER,
    hit_count INTEGER DEFAULT 0,
    ttl_seconds INTEGER,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    last_accessed_at TEXT,
    expires_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_cache_entries_cache_key ON cache_entries(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_entries_expires ON cache_entries(expires_at);

-- =========================================================================
-- error_logs (alembic 001)
-- =========================================================================
CREATE TABLE IF NOT EXISTS error_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    error_details TEXT,
    stack_trace TEXT,
    endpoint TEXT,
    method TEXT,
    status_code INTEGER,
    client_ip TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_error_logs_created ON error_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_error_logs_request ON error_logs(request_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_type ON error_logs(error_type);

-- =========================================================================
-- plans (alembic 002 + 003)
-- =========================================================================
CREATE TABLE IF NOT EXISTS plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    description TEXT,
    stripe_product_id TEXT,
    stripe_price_id TEXT,
    stripe_price_id_yearly TEXT,
    price REAL NOT NULL,
    price_yearly REAL,
    currency TEXT DEFAULT 'usd',
    interval TEXT DEFAULT 'month',
    search_limit INTEGER,
    scrape_limit INTEGER,
    rate_limit TEXT,
    concurrent_requests INTEGER DEFAULT 10,
    features TEXT,
    is_active INTEGER DEFAULT 1,
    is_visible INTEGER DEFAULT 1,
    metadata TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_plans_name ON plans(name);
CREATE UNIQUE INDEX IF NOT EXISTS idx_plans_stripe_product ON plans(stripe_product_id) WHERE stripe_product_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_plans_stripe_price ON plans(stripe_price_id) WHERE stripe_price_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_plans_stripe_price_yearly ON plans(stripe_price_id_yearly) WHERE stripe_price_id_yearly IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_plans_active ON plans(is_active);

-- =========================================================================
-- subscriptions (alembic 002)
-- =========================================================================
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    stripe_subscription_id TEXT,
    stripe_price_id TEXT,
    stripe_product_id TEXT,
    plan_type TEXT NOT NULL CHECK (plan_type IN ('FREE','PRO','GROWTH','SCALE','ENTERPRISE')),
    status TEXT NOT NULL CHECK (status IN ('ACTIVE','TRIALING','CANCELLED','PAST_DUE','UNPAID','INCOMPLETE')),
    amount REAL DEFAULT 0,
    currency TEXT DEFAULT 'usd',
    interval TEXT DEFAULT 'month',
    search_limit INTEGER DEFAULT 5000,
    scrape_limit INTEGER DEFAULT 500,
    rate_limit TEXT DEFAULT '10/minute',
    features TEXT,
    trial_start TEXT,
    trial_end TEXT,
    current_period_start TEXT,
    current_period_end TEXT,
    cancelled_at TEXT,
    ended_at TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_stripe ON subscriptions(stripe_subscription_id) WHERE stripe_subscription_id IS NOT NULL;

-- =========================================================================
-- usage_records (alembic 002)
-- =========================================================================
CREATE TABLE IF NOT EXISTS usage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    search_count INTEGER DEFAULT 0,
    scrape_count INTEGER DEFAULT 0,
    api_calls INTEGER DEFAULT 0,
    usage_by_engine TEXT,
    usage_by_day TEXT,
    search_overage INTEGER DEFAULT 0,
    scrape_overage INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_usage_records_user ON usage_records(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_records_period ON usage_records(period_start, period_end);
CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_user_period ON usage_records(user_id, period_start, period_end);

-- =========================================================================
-- invoices (alembic 002)
-- =========================================================================
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    stripe_invoice_id TEXT,
    stripe_charge_id TEXT,
    invoice_number TEXT,
    status TEXT,
    amount_due INTEGER,
    amount_paid INTEGER,
    amount_remaining INTEGER,
    subtotal INTEGER,
    tax INTEGER,
    total INTEGER,
    currency TEXT DEFAULT 'usd',
    period_start TEXT,
    period_end TEXT,
    due_date TEXT,
    paid_at TEXT,
    invoice_pdf TEXT,
    hosted_invoice_url TEXT,
    description TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_invoices_user ON invoices(user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_stripe ON invoices(stripe_invoice_id) WHERE stripe_invoice_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number) WHERE invoice_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);

-- =========================================================================
-- webhook_events (alembic 002)
-- =========================================================================
CREATE TABLE IF NOT EXISTS webhook_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stripe_event_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    processed INTEGER DEFAULT 0,
    processed_at TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    data TEXT NOT NULL,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_webhook_events_stripe_id ON webhook_events(stripe_event_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_type ON webhook_events(event_type);
CREATE INDEX IF NOT EXISTS idx_webhook_events_processed ON webhook_events(processed);

-- =========================================================================
-- scrape_requests (alembic 005)
-- =========================================================================
CREATE TABLE IF NOT EXISTS scrape_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id TEXT NOT NULL UNIQUE,
    api_key_id INTEGER REFERENCES api_keys(id),
    urls TEXT NOT NULL,
    url_count INTEGER NOT NULL,
    config TEXT,
    extraction_strategy TEXT,
    successful_scrapes INTEGER DEFAULT 0,
    failed_scrapes INTEGER DEFAULT 0,
    total_content_length INTEGER,
    processing_time_ms INTEGER,
    error_message TEXT,
    client_ip TEXT,
    user_agent TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    completed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_scrape_requests_created ON scrape_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_scrape_requests_api_key ON scrape_requests(api_key_id);

-- =========================================================================
-- Seed: default plans (matches alembic 002 seed)
-- =========================================================================
INSERT OR IGNORE INTO plans (name, display_name, description, price, price_yearly, search_limit, scrape_limit, rate_limit, features) VALUES
  ('free',   'Free',   '5x more free queries than competitors', 0,   0,    5000,   500,    '10/minute',
   '{"api_access":true,"webhook_support":false,"priority_support":false,"zero_retention":false}'),
  ('pro',    'Pro',    'For serious AI applications',          19,  190,  25000,  5000,   '60/minute',
   '{"api_access":true,"webhook_support":true,"priority_support":false,"zero_retention":true}'),
  ('growth', 'Growth', 'For scaling teams and products',       49,  490,  100000, 25000,  '200/minute',
   '{"api_access":true,"webhook_support":true,"priority_support":true,"custom_engines":true,"zero_retention":true}'),
  ('scale',  'Scale',  'For high-volume AI applications',      149, 1490, 500000, 100000, '1000/minute',
   '{"api_access":true,"webhook_support":true,"priority_support":true,"custom_engines":true,"dedicated_pool":true,"sla":true,"zero_retention":true}');
