"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial database schema."""
    # Create api_keys table
    op.create_table('api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('rate_limit_override', sa.String(length=50), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_api_keys_active', 'api_keys', ['is_active'])
    op.create_index(op.f('ix_api_keys_key'), 'api_keys', ['key'], unique=True)

    # Create search_requests table
    op.create_table('search_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(length=36), nullable=False),
        sa.Column('api_key_id', sa.Integer(), nullable=True),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('engines', sa.JSON(), nullable=False),
        sa.Column('max_results', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=2), nullable=True),
        sa.Column('safe_search', sa.String(length=10), nullable=True),
        sa.Column('search_time_ms', sa.Integer(), nullable=True),
        sa.Column('scraping_time_ms', sa.Integer(), nullable=True),
        sa.Column('total_time_ms', sa.Integer(), nullable=True),
        sa.Column('results_count', sa.Integer(), nullable=True),
        sa.Column('scraped_count', sa.Integer(), nullable=True),
        sa.Column('cache_hit', sa.Boolean(), nullable=True),
        sa.Column('cache_key', sa.String(length=64), nullable=True),
        sa.Column('client_ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('request_headers', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_search_requests_cache_key', 'search_requests', ['cache_key'])
    op.create_index('idx_search_requests_created', 'search_requests', ['created_at'])
    op.create_index('idx_search_requests_query', 'search_requests', ['query'])
    op.create_index(op.f('ix_search_requests_request_id'), 'search_requests', ['request_id'], unique=True)

    # Create search_results table
    op.create_table('search_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.Integer(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('snippet', sa.Text(), nullable=True),
        sa.Column('engine', sa.String(length=50), nullable=False),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('scraped_successfully', sa.Boolean(), nullable=True),
        sa.Column('scraped_content', sa.JSON(), nullable=True),
        sa.Column('scraping_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['request_id'], ['search_requests.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_search_results_request', 'search_results', ['request_id'])
    op.create_index('idx_search_results_url', 'search_results', ['url'])

    # Create scraping_jobs table
    op.create_table('scraping_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('task_id', sa.String(length=255), nullable=True),
        sa.Column('urls', sa.JSON(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('webhook_url', sa.Text(), nullable=True),
        sa.Column('webhook_attempts', sa.Integer(), nullable=True),
        sa.Column('webhook_last_attempt', sa.DateTime(timezone=True), nullable=True),
        sa.Column('webhook_success', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_scraping_jobs_created', 'scraping_jobs', ['created_at'])
    op.create_index('idx_scraping_jobs_status', 'scraping_jobs', ['status'])
    op.create_index(op.f('ix_scraping_jobs_job_id'), 'scraping_jobs', ['job_id'], unique=True)

    # Create cache_entries table
    op.create_table('cache_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(length=64), nullable=False),
        sa.Column('query_hash', sa.String(length=64), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('hit_count', sa.Integer(), nullable=True),
        sa.Column('ttl_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_cache_entries_expires', 'cache_entries', ['expires_at'])
    op.create_index('idx_cache_entries_key', 'cache_entries', ['cache_key'])
    op.create_index(op.f('ix_cache_entries_cache_key'), 'cache_entries', ['cache_key'], unique=True)

    # Create error_logs table
    op.create_table('error_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('request_id', sa.String(length=36), nullable=True),
        sa.Column('error_type', sa.String(length=100), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=False),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('endpoint', sa.String(length=255), nullable=True),
        sa.Column('method', sa.String(length=10), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('client_ip', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_error_logs_created', 'error_logs', ['created_at'])
    op.create_index('idx_error_logs_request', 'error_logs', ['request_id'])
    op.create_index('idx_error_logs_type', 'error_logs', ['error_type'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index('idx_error_logs_type', table_name='error_logs')
    op.drop_index('idx_error_logs_request', table_name='error_logs')
    op.drop_index('idx_error_logs_created', table_name='error_logs')
    op.drop_table('error_logs')
    
    op.drop_index(op.f('ix_cache_entries_cache_key'), table_name='cache_entries')
    op.drop_index('idx_cache_entries_key', table_name='cache_entries')
    op.drop_index('idx_cache_entries_expires', table_name='cache_entries')
    op.drop_table('cache_entries')
    
    op.drop_index(op.f('ix_scraping_jobs_job_id'), table_name='scraping_jobs')
    op.drop_index('idx_scraping_jobs_status', table_name='scraping_jobs')
    op.drop_index('idx_scraping_jobs_created', table_name='scraping_jobs')
    op.drop_table('scraping_jobs')
    
    op.drop_index('idx_search_results_url', table_name='search_results')
    op.drop_index('idx_search_results_request', table_name='search_results')
    op.drop_table('search_results')
    
    op.drop_index(op.f('ix_search_requests_request_id'), table_name='search_requests')
    op.drop_index('idx_search_requests_query', table_name='search_requests')
    op.drop_index('idx_search_requests_created', table_name='search_requests')
    op.drop_index('idx_search_requests_cache_key', table_name='search_requests')
    op.drop_table('search_requests')
    
    op.drop_index(op.f('ix_api_keys_key'), table_name='api_keys')
    op.drop_index('idx_api_keys_active', table_name='api_keys')
    op.drop_table('api_keys')
