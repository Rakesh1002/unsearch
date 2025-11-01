#!/bin/bash

# SearchScrape API Database Backup Script
# Performs automated backups of PostgreSQL database and Redis data

set -e  # Exit on error
set -u  # Exit on undefined variable

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
else
    log_warn ".env file not found. Using default values."
fi

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-searchscrape}"
DB_USER="${DB_USER:-searchscrape}"
DB_PASSWORD="${DB_PASSWORD:-searchscrape123}"

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

# Function to create backup directory
create_backup_dir() {
    if [ ! -d "$BACKUP_DIR" ]; then
        mkdir -p "$BACKUP_DIR"
        log_info "Created backup directory: $BACKUP_DIR"
    fi
}

# Function to backup PostgreSQL database
backup_postgres() {
    log_info "Starting PostgreSQL backup..."
    
    local backup_file="$BACKUP_DIR/postgres_${DB_NAME}_${TIMESTAMP}.sql.gz"
    
    # Check if PostgreSQL is accessible
    PGPASSWORD=$DB_PASSWORD pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        log_error "Cannot connect to PostgreSQL database"
        return 1
    fi
    
    # Perform backup
    PGPASSWORD=$DB_PASSWORD pg_dump \
        -h $DB_HOST \
        -p $DB_PORT \
        -U $DB_USER \
        -d $DB_NAME \
        --verbose \
        --clean \
        --if-exists \
        --no-owner \
        --no-acl \
        --format=plain \
        --encoding=UTF8 | gzip -9 > "$backup_file"
    
    if [ $? -eq 0 ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_info "PostgreSQL backup completed: $backup_file (Size: $size)"
        echo "$backup_file"
    else
        log_error "PostgreSQL backup failed"
        return 1
    fi
}

# Function to backup Redis data
backup_redis() {
    log_info "Starting Redis backup..."
    
    local backup_file="$BACKUP_DIR/redis_${TIMESTAMP}.rdb"
    
    # Check if Redis is accessible
    redis-cli -h $REDIS_HOST -p $REDIS_PORT ping > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        log_error "Cannot connect to Redis"
        return 1
    fi
    
    # Trigger Redis save
    redis-cli -h $REDIS_HOST -p $REDIS_PORT BGSAVE
    
    # Wait for save to complete
    log_info "Waiting for Redis save to complete..."
    while [ "$(redis-cli -h $REDIS_HOST -p $REDIS_PORT LASTSAVE)" = "$(redis-cli -h $REDIS_HOST -p $REDIS_PORT LASTSAVE)" ]; do
        sleep 1
    done
    
    # Copy the dump file
    if [ -f "/var/lib/redis/dump.rdb" ]; then
        cp /var/lib/redis/dump.rdb "$backup_file"
    elif [ -f "./dump.rdb" ]; then
        cp ./dump.rdb "$backup_file"
    else
        # Try to get it from Docker container
        docker cp searchscrape-redis:/data/dump.rdb "$backup_file" 2>/dev/null || {
            log_warn "Could not find Redis dump file"
            return 1
        }
    fi
    
    # Compress the backup
    gzip -9 "$backup_file"
    backup_file="${backup_file}.gz"
    
    if [ -f "$backup_file" ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_info "Redis backup completed: $backup_file (Size: $size)"
        echo "$backup_file"
    else
        log_error "Redis backup failed"
        return 1
    fi
}

# Function to backup application files
backup_application() {
    log_info "Starting application files backup..."
    
    local backup_file="$BACKUP_DIR/app_files_${TIMESTAMP}.tar.gz"
    
    # Create list of important files/directories to backup
    local files_to_backup=(
        ".env"
        "alembic"
        "searxng/settings.yml"
        "nginx/nginx.conf"
        "scripts"
    )
    
    # Change to project root
    cd "$PROJECT_ROOT"
    
    # Create tar archive
    tar -czf "$backup_file" "${files_to_backup[@]}" 2>/dev/null || {
        log_warn "Some files might not exist, continuing..."
    }
    
    if [ -f "$backup_file" ]; then
        local size=$(du -h "$backup_file" | cut -f1)
        log_info "Application files backup completed: $backup_file (Size: $size)"
        echo "$backup_file"
    else
        log_error "Application files backup failed"
        return 1
    fi
}

# Function to upload to S3
upload_to_s3() {
    local file=$1
    
    if [ -z "$S3_BUCKET" ]; then
        log_info "S3 backup not configured, skipping upload"
        return 0
    fi
    
    if ! command_exists aws; then
        log_warn "AWS CLI not installed, skipping S3 upload"
        return 0
    fi
    
    log_info "Uploading to S3: $file"
    
    local filename=$(basename "$file")
    local s3_path="s3://$S3_BUCKET/backups/searchscrape/$(date +%Y/%m/%d)/$filename"
    
    aws s3 cp "$file" "$s3_path" --region "$S3_REGION"
    
    if [ $? -eq 0 ]; then
        log_info "Successfully uploaded to S3: $s3_path"
        return 0
    else
        log_error "Failed to upload to S3"
        return 1
    fi
}

# Function to clean old backups
cleanup_old_backups() {
    log_info "Cleaning up old backups (older than $RETENTION_DAYS days)..."
    
    find "$BACKUP_DIR" -type f -name "*.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -type f -name "*.sql" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -type f -name "*.rdb" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -type f -name "*.tar" -mtime +$RETENTION_DAYS -delete
    
    log_info "Cleanup completed"
}

# Function to create backup report
create_backup_report() {
    local report_file="$BACKUP_DIR/backup_report_${TIMESTAMP}.txt"
    
    cat > "$report_file" << EOF
========================================
SearchScrape API Backup Report
========================================
Date: $(date)
Hostname: $(hostname)
User: $(whoami)

Backup Details:
----------------------------------------
EOF
    
    for file in "$@"; do
        if [ -f "$file" ]; then
            echo "- $(basename "$file"): $(du -h "$file" | cut -f1)" >> "$report_file"
        fi
    done
    
    cat >> "$report_file" << EOF

Backup Location: $BACKUP_DIR
Retention Policy: $RETENTION_DAYS days
S3 Bucket: ${S3_BUCKET:-Not configured}

========================================
EOF
    
    log_info "Backup report created: $report_file"
    cat "$report_file"
}

# Function to send notification (optional)
send_notification() {
    local status=$1
    local message=$2
    
    # Slack webhook notification (if configured)
    if [ ! -z "${SLACK_WEBHOOK_URL:-}" ]; then
        local color="good"
        if [ "$status" != "success" ]; then
            color="danger"
        fi
        
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"SearchScrape Backup\",
                    \"text\": \"$message\",
                    \"footer\": \"Backup System\",
                    \"ts\": $(date +%s)
                }]
            }" 2>/dev/null
    fi
    
    # Email notification (if configured)
    if [ ! -z "${BACKUP_EMAIL:-}" ] && command_exists mail; then
        echo "$message" | mail -s "SearchScrape Backup - $status" "$BACKUP_EMAIL"
    fi
}

# Main backup process
main() {
    log_info "========================================="
    log_info "Starting SearchScrape API Backup"
    log_info "Timestamp: $TIMESTAMP"
    log_info "========================================="
    
    # Check required commands
    for cmd in pg_dump redis-cli tar gzip; do
        if ! command_exists $cmd; then
            log_error "Required command not found: $cmd"
            exit 1
        fi
    done
    
    # Create backup directory
    create_backup_dir
    
    # Array to store backup files
    declare -a backup_files
    
    # Perform backups
    if pg_backup=$(backup_postgres); then
        backup_files+=("$pg_backup")
        [ ! -z "$S3_BUCKET" ] && upload_to_s3 "$pg_backup"
    else
        log_error "PostgreSQL backup failed, continuing..."
    fi
    
    if redis_backup=$(backup_redis); then
        backup_files+=("$redis_backup")
        [ ! -z "$S3_BUCKET" ] && upload_to_s3 "$redis_backup"
    else
        log_error "Redis backup failed, continuing..."
    fi
    
    if app_backup=$(backup_application); then
        backup_files+=("$app_backup")
        [ ! -z "$S3_BUCKET" ] && upload_to_s3 "$app_backup"
    else
        log_error "Application backup failed, continuing..."
    fi
    
    # Clean old backups
    cleanup_old_backups
    
    # Create report
    create_backup_report "${backup_files[@]}"
    
    # Send notification
    if [ ${#backup_files[@]} -gt 0 ]; then
        send_notification "success" "Backup completed successfully. ${#backup_files[@]} files backed up."
        log_info "========================================="
        log_info "Backup completed successfully!"
        log_info "========================================="
        exit 0
    else
        send_notification "failure" "Backup failed. No files were backed up."
        log_error "========================================="
        log_error "Backup failed!"
        log_error "========================================="
        exit 1
    fi
}

# Handle script arguments
case "${1:-}" in
    postgres)
        create_backup_dir
        backup_postgres
        ;;
    redis)
        create_backup_dir
        backup_redis
        ;;
    app)
        create_backup_dir
        backup_application
        ;;
    *)
        main
        ;;
esac
