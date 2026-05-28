"""Add user and billing tables

Revision ID: 002_add_user_billing
Revises: 001_initial_schema
Create Date: 2024-01-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_user_billing'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types (with IF NOT EXISTS to handle SQLAlchemy auto-creation)
    # Updated to include GROWTH and SCALE tiers for new laddered pricing
    op.execute("DO $$ BEGIN CREATE TYPE plantype AS ENUM ('FREE', 'PRO', 'GROWTH', 'SCALE', 'ENTERPRISE'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE subscriptionstatus AS ENUM ('ACTIVE', 'TRIALING', 'CANCELLED', 'PAST_DUE', 'UNPAID', 'INCOMPLETE'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(36), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('username', sa.String(100), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('salt', sa.String(32), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('company', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(20), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=True, server_default='UTC'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('is_admin', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verification_token', sa.String(255), nullable=True),
        sa.Column('reset_token', sa.String(255), nullable=True),
        sa.Column('reset_token_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('stripe_customer_id', sa.String(255), nullable=True),
        sa.Column('stripe_payment_method_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_users_email', 'users', ['email'], unique=True)
    op.create_index('idx_users_username', 'users', ['username'], unique=True)
    op.create_index('idx_users_uuid', 'users', ['uuid'], unique=True)
    op.create_index('idx_users_stripe', 'users', ['stripe_customer_id'], unique=True)
    op.create_index('idx_users_active', 'users', ['is_active'])
    
    # Create user_api_keys table
    op.create_table(
        'user_api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(64), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('ip_whitelist', sa.JSON(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('request_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_api_keys_key', 'user_api_keys', ['key'], unique=True)
    op.create_index('idx_user_api_keys_active', 'user_api_keys', ['is_active'])
    op.create_index('idx_user_api_keys_user', 'user_api_keys', ['user_id'])
    
    # Create plans table
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('stripe_product_id', sa.String(255), nullable=True),
        sa.Column('stripe_price_id', sa.String(255), nullable=True),
        sa.Column('stripe_price_id_yearly', sa.String(255), nullable=True),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('price_yearly', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(3), nullable=True, server_default='usd'),
        sa.Column('interval', sa.String(20), nullable=True, server_default='month'),
        sa.Column('search_limit', sa.Integer(), nullable=True),
        sa.Column('scrape_limit', sa.Integer(), nullable=True),
        sa.Column('rate_limit', sa.String(50), nullable=True),
        sa.Column('concurrent_requests', sa.Integer(), nullable=True, server_default='10'),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('is_visible', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_plans_name', 'plans', ['name'], unique=True)
    op.create_index('idx_plans_stripe_product', 'plans', ['stripe_product_id'], unique=True)
    op.create_index('idx_plans_stripe_price', 'plans', ['stripe_price_id'], unique=True)
    op.create_index('idx_plans_stripe_price_yearly', 'plans', ['stripe_price_id_yearly'], unique=True)
    op.create_index('idx_plans_active', 'plans', ['is_active'])
    
    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stripe_subscription_id', sa.String(255), nullable=True),
        sa.Column('stripe_price_id', sa.String(255), nullable=True),
        sa.Column('stripe_product_id', sa.String(255), nullable=True),
        sa.Column('plan_type', postgresql.ENUM('FREE', 'PRO', 'GROWTH', 'SCALE', 'ENTERPRISE', name='plantype', create_type=False), nullable=False),
        sa.Column('status', postgresql.ENUM('ACTIVE', 'TRIALING', 'CANCELLED', 'PAST_DUE', 'UNPAID', 'INCOMPLETE', name='subscriptionstatus', create_type=False), nullable=False),
        sa.Column('amount', sa.Float(), nullable=True, server_default='0'),
        sa.Column('currency', sa.String(3), nullable=True, server_default='usd'),
        sa.Column('interval', sa.String(20), nullable=True, server_default='month'),
        sa.Column('search_limit', sa.Integer(), nullable=True, server_default='5000'),
        sa.Column('scrape_limit', sa.Integer(), nullable=True, server_default='500'),
        sa.Column('rate_limit', sa.String(50), nullable=True, server_default='10/minute'),
        sa.Column('features', sa.JSON(), nullable=True),
        sa.Column('trial_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_subscriptions_user', 'subscriptions', ['user_id'])
    op.create_index('idx_subscriptions_status', 'subscriptions', ['status'])
    op.create_index('idx_subscriptions_stripe', 'subscriptions', ['stripe_subscription_id'], unique=True)
    
    # Create usage_records table
    op.create_table(
        'usage_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('search_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('scrape_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('api_calls', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('usage_by_engine', sa.JSON(), nullable=True),
        sa.Column('usage_by_day', sa.JSON(), nullable=True),
        sa.Column('search_overage', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('scrape_overage', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_usage_records_user', 'usage_records', ['user_id'])
    op.create_index('idx_usage_records_period', 'usage_records', ['period_start', 'period_end'])
    op.create_index('idx_usage_user_period', 'usage_records', ['user_id', 'period_start', 'period_end'], unique=True)
    
    # Create invoices table
    op.create_table(
        'invoices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('stripe_invoice_id', sa.String(255), nullable=True),
        sa.Column('stripe_charge_id', sa.String(255), nullable=True),
        sa.Column('invoice_number', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=True),
        sa.Column('amount_due', sa.Integer(), nullable=True),
        sa.Column('amount_paid', sa.Integer(), nullable=True),
        sa.Column('amount_remaining', sa.Integer(), nullable=True),
        sa.Column('subtotal', sa.Integer(), nullable=True),
        sa.Column('tax', sa.Integer(), nullable=True),
        sa.Column('total', sa.Integer(), nullable=True),
        sa.Column('currency', sa.String(3), nullable=True, server_default='usd'),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invoice_pdf', sa.String(500), nullable=True),
        sa.Column('hosted_invoice_url', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_invoices_user', 'invoices', ['user_id'])
    op.create_index('idx_invoices_stripe', 'invoices', ['stripe_invoice_id'], unique=True)
    op.create_index('idx_invoices_number', 'invoices', ['invoice_number'], unique=True)
    op.create_index('idx_invoices_status', 'invoices', ['status'])
    
    # Create webhook_events table
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('stripe_event_id', sa.String(255), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_webhook_events_stripe_id', 'webhook_events', ['stripe_event_id'], unique=True)
    op.create_index('idx_webhook_events_type', 'webhook_events', ['event_type'])
    op.create_index('idx_webhook_events_processed', 'webhook_events', ['processed'])
    
    # Add user_id foreign key to existing api_keys table (if it exists)
    with op.batch_alter_table('api_keys') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_api_keys_user_id', 'users', ['user_id'], ['id'])
        batch_op.create_index('idx_api_keys_user_id', ['user_id'])
    
    # Insert default plans - competitive pricing based on Tavily/Exa/Brave analysis
    # Key: 5x free tier, 50%+ cheaper than Tavily at all tiers
    # Yearly pricing = 10 months (17% off / 2 months free)
    op.execute("""
        INSERT INTO plans (name, display_name, description, price, price_yearly, search_limit, scrape_limit, rate_limit, features)
        VALUES 
        ('free', 'Free', '5x more free queries than competitors', 0, 0, 5000, 500, '10/minute', 
         '{"api_access": true, "webhook_support": false, "priority_support": false, "zero_retention": false}'::jsonb),
        ('pro', 'Pro', 'For serious AI applications', 19, 190, 25000, 5000, '60/minute',
         '{"api_access": true, "webhook_support": true, "priority_support": false, "zero_retention": true}'::jsonb),
        ('growth', 'Growth', 'For scaling teams and products', 49, 490, 100000, 25000, '200/minute',
         '{"api_access": true, "webhook_support": true, "priority_support": true, "custom_engines": true, "zero_retention": true}'::jsonb),
        ('scale', 'Scale', 'For high-volume AI applications', 149, 1490, 500000, 100000, '1000/minute',
         '{"api_access": true, "webhook_support": true, "priority_support": true, "custom_engines": true, "dedicated_pool": true, "sla": true, "zero_retention": true}'::jsonb)
    """)


def downgrade():
    # Drop tables in reverse order
    op.drop_index('idx_api_keys_user_id', 'api_keys')
    with op.batch_alter_table('api_keys') as batch_op:
        batch_op.drop_constraint('fk_api_keys_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')
    
    op.drop_table('webhook_events')
    op.drop_table('invoices')
    op.drop_table('usage_records')
    op.drop_table('subscriptions')
    op.drop_table('plans')
    op.drop_table('user_api_keys')
    op.drop_table('users')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS plantype")
    op.execute("DROP TYPE IF EXISTS subscriptionstatus")
