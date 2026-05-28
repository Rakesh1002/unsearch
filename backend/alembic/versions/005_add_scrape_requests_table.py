"""Add scrape_requests table for scraping analytics

Revision ID: 005_add_scrape_requests
Revises: 004_add_agent_fields
Create Date: 2026-02-13

This migration adds the scrape_requests table for logging and analytics
of standalone scraping operations (separate from search requests).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '005_add_scrape_requests'
down_revision = '004_add_agent_fields'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'scrape_requests' not in existing_tables:
        op.create_table(
            'scrape_requests',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('request_id', sa.String(36), unique=True, nullable=False),
            sa.Column('api_key_id', sa.Integer(), sa.ForeignKey('api_keys.id'), nullable=True),
            
            # Request info
            sa.Column('urls', sa.JSON(), nullable=False),
            sa.Column('url_count', sa.Integer(), nullable=False),
            
            # Configuration
            sa.Column('config', sa.JSON(), nullable=True),
            sa.Column('extraction_strategy', sa.String(50), nullable=True),
            
            # Results
            sa.Column('successful_scrapes', sa.Integer(), server_default='0'),
            sa.Column('failed_scrapes', sa.Integer(), server_default='0'),
            sa.Column('total_content_length', sa.Integer(), nullable=True),
            
            # Performance metrics
            sa.Column('processing_time_ms', sa.Integer(), nullable=True),
            
            # Error tracking
            sa.Column('error_message', sa.Text(), nullable=True),
            
            # Request metadata
            sa.Column('client_ip', sa.String(45), nullable=True),
            sa.Column('user_agent', sa.Text(), nullable=True),
            
            # Timestamps
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        )
        
        # Create indexes
        op.create_index('idx_scrape_requests_created', 'scrape_requests', ['created_at'])
        op.create_index('idx_scrape_requests_api_key', 'scrape_requests', ['api_key_id'])


def downgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'scrape_requests' in existing_tables:
        # Drop indexes first
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('scrape_requests')]
        if 'idx_scrape_requests_created' in existing_indexes:
            op.drop_index('idx_scrape_requests_created', table_name='scrape_requests')
        if 'idx_scrape_requests_api_key' in existing_indexes:
            op.drop_index('idx_scrape_requests_api_key', table_name='scrape_requests')
        
        op.drop_table('scrape_requests')
