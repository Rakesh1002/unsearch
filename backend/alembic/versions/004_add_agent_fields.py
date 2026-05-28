"""Add agent self-registration fields to users table

Revision ID: 004_add_agent_fields
Revises: 003_add_yearly_price
Create Date: 2026-02-12

This migration adds fields for AI agent self-registration:
- is_agent_placeholder: True for agents that haven't been claimed by a human
- agent_name: Unique identifier for the agent (reserved permanently)
- agent_description: Description of what the agent does
- claim_code: Code used by humans to claim the agent
- claimed_at: When the agent was claimed
- daily_searches_used: Daily search counter for sandbox agents (25/day)
- daily_reset_at: When daily counter resets
- sandbox_expires_at: 7 days from registration
- is_sandbox_expired: True after 7 days without claim
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '004_add_agent_fields'
down_revision = '003_add_yearly_price'
branch_labels = None
depends_on = None


def upgrade():
    # Get current connection and inspect the table
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check existing columns
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    # Add agent placeholder fields
    if 'is_agent_placeholder' not in columns:
        op.add_column('users', sa.Column('is_agent_placeholder', sa.Boolean(), nullable=True, server_default='false'))
    
    if 'agent_name' not in columns:
        op.add_column('users', sa.Column('agent_name', sa.String(100), nullable=True))
        op.create_index('idx_users_agent_name', 'users', ['agent_name'], unique=True)
    
    if 'agent_description' not in columns:
        op.add_column('users', sa.Column('agent_description', sa.Text(), nullable=True))
    
    if 'claim_code' not in columns:
        op.add_column('users', sa.Column('claim_code', sa.String(64), nullable=True))
        op.create_index('idx_users_claim_code', 'users', ['claim_code'], unique=True)
    
    if 'claimed_at' not in columns:
        op.add_column('users', sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add sandbox limit fields
    if 'daily_searches_used' not in columns:
        op.add_column('users', sa.Column('daily_searches_used', sa.Integer(), nullable=True, server_default='0'))
    
    if 'daily_reset_at' not in columns:
        op.add_column('users', sa.Column('daily_reset_at', sa.DateTime(timezone=True), nullable=True))
    
    if 'sandbox_expires_at' not in columns:
        op.add_column('users', sa.Column('sandbox_expires_at', sa.DateTime(timezone=True), nullable=True))
    
    if 'is_sandbox_expired' not in columns:
        op.add_column('users', sa.Column('is_sandbox_expired', sa.Boolean(), nullable=True, server_default='false'))
    
    if 'registration_ip' not in columns:
        op.add_column('users', sa.Column('registration_ip', sa.String(45), nullable=True))
    
    # Create index for agent placeholder lookup
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    if 'idx_users_agent_placeholder' not in existing_indexes:
        op.create_index('idx_users_agent_placeholder', 'users', ['is_agent_placeholder'])


def downgrade():
    # Check if columns exist before dropping
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('users')]
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    
    # Drop indexes first
    if 'idx_users_agent_placeholder' in existing_indexes:
        op.drop_index('idx_users_agent_placeholder', table_name='users')
    if 'idx_users_claim_code' in existing_indexes:
        op.drop_index('idx_users_claim_code', table_name='users')
    if 'idx_users_agent_name' in existing_indexes:
        op.drop_index('idx_users_agent_name', table_name='users')
    
    # Drop columns
    columns_to_drop = [
        'is_agent_placeholder',
        'agent_name',
        'agent_description',
        'claim_code',
        'claimed_at',
        'daily_searches_used',
        'daily_reset_at',
        'sandbox_expires_at',
        'is_sandbox_expired',
        'registration_ip',
    ]
    
    for col in columns_to_drop:
        if col in columns:
            op.drop_column('users', col)
