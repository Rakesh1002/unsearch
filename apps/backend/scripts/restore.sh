#!/bin/bash

# UnSearch API Database Restore Script
# Restores PostgreSQL database and Redis data from backups

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_prompt() {
    echo -e "${BLUE}[PROMPT]${NC} $1"
}

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
else
    log_warn ".env file not found. Using default values."
fi

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-UnSearch}"
DB_USER="${DB_USER:-UnSearch}"
DB_PASSWORD="${DB_PASSWORD:-UnSearch123}"

# Redis configuration
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

# S3 configuration (optional)
S3_BUCKET="${S3_BUCKET:-}"
S3_REGION="${S3_REGION:-us-east-1}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to list available backups
list_backups() {
    local backup_type=$1
    
    log_info "Available $backup_type backups:"
    
    case $backup_type in
        postgres)
            find "$BACKUP_DIR" -name "postgres_*.sql.gz" -type f | sort -r | head -20
            ;;
        redis)
            find "$BACKUP_DIR" -name "redis_*.rdb.gz" -type f | sort -r | head -20
            ;;
        app)
            find "$BACKUP_DIR" -name "app_files_*.tar.gz" -type f | sort -r | head -20
            ;;
        *)
            find "$BACKUP_DIR" -name "*.gz" -type f | sort -r | head -20
            ;;
    esac
}

# Function to download from S3
download_from_s3() {
    local s3_path=$1
    local local_file=$2
    
    if [ -z "$S3_BUCKET" ]; then
        log_error "S3 bucket not configured"
        return 1
    fi
    
    if ! command_exists aws; then
        log_error "AWS CLI not installed"
        return 1
    fi
    
    log_info "Downloading from S3: $s3_path"
    
    aws s3 cp "$s3_path" "$local_file" --region "$S3_REGION"
    
    if [ $? -eq 0 ]; then
        log_info "Successfully downloaded: $local_file"
        return 0
    else
        log_error "Failed to download from S3"
        return 1
    fi
}

# Function to confirm action
confirm_action() {
    local message=$1
    local response
    
    log_prompt "$message (yes/no): "
    read -r response
    
    case $response in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Function to restore PostgreSQL database
restore_postgres() {
    local backup_file=$1
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    log_info "Restoring PostgreSQL from: $backup_file"
    
    # Check if PostgreSQL is accessible
    PGPASSWORD=$DB_PASSWORD pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        log_error "Cannot connect to PostgreSQL database"
        return 1
    fi
    
    # Warn about data loss
    log_warn "⚠️  This will REPLACE ALL DATA in database: $DB_NAME"
    if ! confirm_action "Are you sure you want to continue?"; then
        log_info "Restore cancelled"
        return 0
    fi
    
    # Create backup of current database before restore
    log_info "Creating backup of current database..."
    local pre_restore_backup="$BACKUP_DIR/pre_restore_$(date +%Y%m%d_%H%M%S).sql.gz"
    PGPASSWORD=$DB_PASSWORD pg_dump \
        -h $DB_HOST \
        -p $DB_PORT \
        -U $DB_USER \
        -d $DB_NAME \
        --no-owner \
        --no-acl | gzip -9 > "$pre_restore_backup"
    log_info "Current database backed up to: $pre_restore_backup"
    
    # Terminate active connections
    log_info "Terminating active database connections..."
    PGPASSWORD=$DB_PASSWORD psql \
        -h $DB_HOST \
        -p $DB_PORT \
        -U $DB_USER \
        -d postgres \
        -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME' AND pid <> pg_backend_pid();" \
        > /dev/null 2>&1
    
    # Drop and recreate database
    log_info "Recreating database..."
    PGPASSWORD=$DB_PASSWORD psql \
        -h $DB_HOST \
        -p $DB_PORT \
        -U $DB_USER \
        -d postgres \
        -c "DROP DATABASE IF EXISTS $DB_NAME; CREATE DATABASE $DB_NAME;" \
        > /dev/null 2>&1
    
    # Restore from backup
    log_info "Restoring database..."
    gunzip -c "$backup_file" | PGPASSWORD=$DB_PASSWORD psql \
        -h $DB_HOST \
        -p $DB_PORT \
        -U $DB_USER \
        -d $DB_NAME \
        --set ON_ERROR_STOP=on
    
    if [ $? -eq 0 ]; then
        log_info "PostgreSQL restore completed successfully"
        
        # Run migrations
        log_info "Running database migrations..."
        cd "$PROJECT_ROOT"
        alembic upgrade head
        
        return 0
    else
        log_error "PostgreSQL restore failed"
        log_info "Attempting to restore from pre-restore backup..."
        gunzip -c "$pre_restore_backup" | PGPASSWORD=$DB_PASSWORD psql \
            -h $DB_HOST \
            -p $DB_PORT \
            -U $DB_USER \
            -d $DB_NAME
        return 1
    fi
}

# Function to restore Redis data
restore_redis() {
    local backup_file=$1
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    log_info "Restoring Redis from: $backup_file"
    
    # Check if Redis is accessible
    redis-cli -h $REDIS_HOST -p $REDIS_PORT ping > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        log_error "Cannot connect to Redis"
        return 1
    fi
    
    # Warn about data loss
    log_warn "⚠️  This will REPLACE ALL DATA in Redis"
    if ! confirm_action "Are you sure you want to continue?"; then
        log_info "Restore cancelled"
        return 0
    fi
    
    # Create backup of current Redis data
    log_info "Creating backup of current Redis data..."
    redis-cli -h $REDIS_HOST -p $REDIS_PORT BGSAVE
    sleep 2  # Wait for save to start
    
    # Extract backup file
    local temp_file="/tmp/redis_restore_$(date +%s).rdb"
    gunzip -c "$backup_file" > "$temp_file"
    
    # Stop Redis (if using Docker)
    if command_exists docker && docker ps | grep -q UnSearch-redis; then
        log_info "Stopping Redis container..."
        docker stop UnSearch-redis
        
        # Copy dump file
        docker cp "$temp_file" UnSearch-redis:/data/dump.rdb
        
        # Start Redis
        log_info "Starting Redis container..."
        docker start UnSearch-redis
    else
        # For local Redis
        log_info "Stopping Redis service..."
        sudo systemctl stop redis || sudo service redis stop
        
        # Copy dump file
        sudo cp "$temp_file" /var/lib/redis/dump.rdb
        sudo chown redis:redis /var/lib/redis/dump.rdb
        
        # Start Redis
        log_info "Starting Redis service..."
        sudo systemctl start redis || sudo service redis start
    fi
    
    # Clean up temp file
    rm -f "$temp_file"
    
    # Verify restoration
    sleep 2
    redis-cli -h $REDIS_HOST -p $REDIS_PORT ping > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        local keys_count=$(redis-cli -h $REDIS_HOST -p $REDIS_PORT DBSIZE | cut -d' ' -f2)
        log_info "Redis restore completed successfully. Keys in database: $keys_count"
        return 0
    else
        log_error "Redis restore failed"
        return 1
    fi
}

# Function to restore application files
restore_application() {
    local backup_file=$1
    
    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        return 1
    fi
    
    log_info "Restoring application files from: $backup_file"
    
    # Warn about overwriting files
    log_warn "⚠️  This will overwrite configuration files"
    if ! confirm_action "Are you sure you want to continue?"; then
        log_info "Restore cancelled"
        return 0
    fi
    
    # Create backup of current files
    log_info "Creating backup of current configuration..."
    local pre_restore_backup="$BACKUP_DIR/app_pre_restore_$(date +%Y%m%d_%H%M%S).tar.gz"
    cd "$PROJECT_ROOT"
    tar -czf "$pre_restore_backup" .env alembic searxng nginx scripts 2>/dev/null || true
    log_info "Current configuration backed up to: $pre_restore_backup"
    
    # Extract backup
    log_info "Extracting application files..."
    tar -xzf "$backup_file" -C "$PROJECT_ROOT"
    
    if [ $? -eq 0 ]; then
        log_info "Application files restore completed successfully"
        
        # Reload services if running
        if command_exists docker && docker ps | grep -q UnSearch-api; then
            log_info "Reloading services..."
            docker compose restart api nginx
        fi
        
        return 0
    else
        log_error "Application files restore failed"
        return 1
    fi
}

# Function to perform full restore
full_restore() {
    log_info "Performing full system restore"
    
    # Find latest backups
    local latest_postgres=$(find "$BACKUP_DIR" -name "postgres_*.sql.gz" -type f | sort -r | head -1)
    local latest_redis=$(find "$BACKUP_DIR" -name "redis_*.rdb.gz" -type f | sort -r | head -1)
    local latest_app=$(find "$BACKUP_DIR" -name "app_files_*.tar.gz" -type f | sort -r | head -1)
    
    if [ -z "$latest_postgres" ] && [ -z "$latest_redis" ] && [ -z "$latest_app" ]; then
        log_error "No backup files found in $BACKUP_DIR"
        return 1
    fi
    
    log_info "Found backups:"
    [ ! -z "$latest_postgres" ] && log_info "  PostgreSQL: $(basename $latest_postgres)"
    [ ! -z "$latest_redis" ] && log_info "  Redis: $(basename $latest_redis)"
    [ ! -z "$latest_app" ] && log_info "  Application: $(basename $latest_app)"
    
    if ! confirm_action "Restore from these backups?"; then
        log_info "Restore cancelled"
        return 0
    fi
    
    # Stop services
    log_info "Stopping services..."
    if command_exists docker && docker compose ps | grep -q Up; then
        docker compose stop
    fi
    
    # Restore each component
    local restore_success=true
    
    if [ ! -z "$latest_app" ]; then
        restore_application "$latest_app" || restore_success=false
    fi
    
    if [ ! -z "$latest_postgres" ]; then
        restore_postgres "$latest_postgres" || restore_success=false
    fi
    
    if [ ! -z "$latest_redis" ]; then
        restore_redis "$latest_redis" || restore_success=false
    fi
    
    # Start services
    log_info "Starting services..."
    if command_exists docker; then
        docker compose up -d
    fi
    
    if $restore_success; then
        log_info "Full restore completed successfully"
        return 0
    else
        log_error "Some components failed to restore"
        return 1
    fi
}

# Interactive restore menu
interactive_restore() {
    while true; do
        echo
        log_info "========================================="
        log_info "UnSearch API Restore Menu"
        log_info "========================================="
        echo "1) Restore PostgreSQL database"
        echo "2) Restore Redis data"
        echo "3) Restore application files"
        echo "4) Full system restore (all components)"
        echo "5) List available backups"
        echo "6) Download backup from S3"
        echo "0) Exit"
        echo
        log_prompt "Enter your choice [0-6]: "
        
        read -r choice
        
        case $choice in
            1)
                list_backups postgres
                echo
                log_prompt "Enter the full path to PostgreSQL backup file: "
                read -r backup_file
                restore_postgres "$backup_file"
                ;;
            2)
                list_backups redis
                echo
                log_prompt "Enter the full path to Redis backup file: "
                read -r backup_file
                restore_redis "$backup_file"
                ;;
            3)
                list_backups app
                echo
                log_prompt "Enter the full path to application backup file: "
                read -r backup_file
                restore_application "$backup_file"
                ;;
            4)
                full_restore
                ;;
            5)
                log_info "All available backups:"
                list_backups all
                ;;
            6)
                log_prompt "Enter S3 path (e.g., s3://bucket/path/to/backup.gz): "
                read -r s3_path
                log_prompt "Enter local filename to save as: "
                read -r local_file
                download_from_s3 "$s3_path" "$BACKUP_DIR/$local_file"
                ;;
            0)
                log_info "Exiting restore menu"
                exit 0
                ;;
            *)
                log_error "Invalid choice"
                ;;
        esac
    done
}

# Main function
main() {
    # Check required commands
    for cmd in psql pg_isready redis-cli tar gzip; do
        if ! command_exists $cmd; then
            log_error "Required command not found: $cmd"
            exit 1
        fi
    done
    
    # Check if backup directory exists
    if [ ! -d "$BACKUP_DIR" ]; then
        log_error "Backup directory not found: $BACKUP_DIR"
        exit 1
    fi
    
    # Handle command line arguments
    case "${1:-}" in
        postgres)
            if [ -z "${2:-}" ]; then
                list_backups postgres
                log_error "Please specify a PostgreSQL backup file"
                exit 1
            fi
            restore_postgres "$2"
            ;;
        redis)
            if [ -z "${2:-}" ]; then
                list_backups redis
                log_error "Please specify a Redis backup file"
                exit 1
            fi
            restore_redis "$2"
            ;;
        app)
            if [ -z "${2:-}" ]; then
                list_backups app
                log_error "Please specify an application backup file"
                exit 1
            fi
            restore_application "$2"
            ;;
        full)
            full_restore
            ;;
        list)
            list_backups "${2:-all}"
            ;;
        *)
            interactive_restore
            ;;
    esac
}

# Run main function
main "$@"
