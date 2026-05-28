"""Add stripe_price_id_yearly column to plans table

Revision ID: 003_add_yearly_price
Revises: 002_add_user_billing
Create Date: 2026-02-10

This migration adds the stripe_price_id_yearly column if it doesn't exist.
This handles cases where the database was created before this column was added.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '003_add_yearly_price'
down_revision = '002_add_user_billing'
branch_labels = None
depends_on = None


def upgrade():
    # Get current connection and inspect the table
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if column already exists
    columns = [col['name'] for col in inspector.get_columns('plans')]
    
    if 'stripe_price_id_yearly' not in columns:
        op.add_column('plans', sa.Column('stripe_price_id_yearly', sa.String(255), nullable=True))
        op.create_index('idx_plans_stripe_price_yearly', 'plans', ['stripe_price_id_yearly'], unique=True)
    
    if 'price_yearly' not in columns:
        op.add_column('plans', sa.Column('price_yearly', sa.Float(), nullable=True))
        
        # Update existing plans with yearly prices (10 months = 17% off)
        op.execute("""
            UPDATE plans SET price_yearly = price * 10 WHERE price_yearly IS NULL
        """)


def downgrade():
    # Check if columns exist before dropping
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('plans')]
    
    if 'stripe_price_id_yearly' in columns:
        op.drop_index('idx_plans_stripe_price_yearly', table_name='plans')
        op.drop_column('plans', 'stripe_price_id_yearly')
    
    if 'price_yearly' in columns:
        op.drop_column('plans', 'price_yearly')
