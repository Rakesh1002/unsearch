#!/bin/bash
#
# UnSearch Service Manager
# Manages Docker services and FastAPI application
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Handle symlinks - resolve to actual script location
REAL_SCRIPT="$(readlink -f "${BASH_SOURCE[0]}")"
REAL_SCRIPT_DIR="$(dirname "$REAL_SCRIPT")"
PROJECT_DIR="$(dirname "$REAL_SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"
VENV_DIR="$PROJECT_DIR/venv"
PID_FILE="$PROJECT_DIR/.fastapi.pid"
LOG_DIR="$PROJECT_DIR/logs"

# Default values
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
API_WORKERS="${API_WORKERS:-4}"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Print colored message
print_msg() {
    local color=$1
    local msg=$2
    echo -e "${color}${msg}${NC}"
}

print_header() {
    echo ""
    print_msg "$BLUE" "=========================================="
    print_msg "$BLUE" " $1"
    print_msg "$BLUE" "=========================================="
}

# Check if command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_msg "$RED" "Error: $1 is not installed"
        return 1
    fi
    return 0
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    local missing=0
    
    for cmd in docker python3; do
        if check_command "$cmd"; then
            print_msg "$GREEN" "  ✓ $cmd"
        else
            missing=1
        fi
    done
    
    # Check docker compose (v2)
    if docker compose version &> /dev/null; then
        print_msg "$GREEN" "  ✓ docker compose"
    else
        print_msg "$RED" "  ✗ docker compose"
        missing=1
    fi
    
    # Check virtual environment
    if [ -d "$VENV_DIR" ]; then
        print_msg "$GREEN" "  ✓ Python virtual environment"
    else
        print_msg "$YELLOW" "  ! Virtual environment not found, will create"
    fi
    
    # Check .env file
    if [ -f "$PROJECT_DIR/.env" ]; then
        print_msg "$GREEN" "  ✓ .env configuration"
    else
        print_msg "$YELLOW" "  ! .env not found, copying from .env.example"
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env" 2>/dev/null || true
    fi
    
    return $missing
}

# Setup Python environment
setup_python() {
    print_header "Setting Up Python Environment"
    
    cd "$PROJECT_DIR"
    
    if [ ! -d "$VENV_DIR" ]; then
        print_msg "$YELLOW" "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    fi
    
    source "$VENV_DIR/bin/activate"
    
    print_msg "$YELLOW" "Installing/updating dependencies..."
    pip install --upgrade pip setuptools wheel -q
    pip install -r "$BACKEND_DIR/requirements.txt" -q
    
    # Install additional dependencies if needed
    pip install numpy fakeredis pytest-mock -q 2>/dev/null || true
    
    # Download NLTK data
    python3 -c "import nltk; nltk.download('punkt', quiet=True); nltk.download('punkt_tab', quiet=True); nltk.download('stopwords', quiet=True)" 2>/dev/null || true
    
    print_msg "$GREEN" "Python environment ready"
}

# Start Docker services
start_docker() {
    print_header "Starting Docker Services"
    
    cd "$PROJECT_DIR"
    
    # Check if services are already running
    local running=$(docker compose ps -q 2>/dev/null | wc -l)
    
    if [ "$running" -gt 0 ]; then
        print_msg "$YELLOW" "Some services already running, restarting..."
        docker compose down 2>/dev/null || true
    fi
    
    print_msg "$YELLOW" "Starting containers..."
    docker compose up -d postgres redis searxng 2>&1 | grep -v "^time=" || true
    
    # Wait for services to be healthy
    print_msg "$YELLOW" "Waiting for services to be healthy..."
    
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        local healthy=0
        
        # Check PostgreSQL
        if docker compose exec -T postgres pg_isready -U unsearch &>/dev/null; then
            healthy=$((healthy + 1))
        fi
        
        # Check Redis
        if docker compose exec -T redis redis-cli ping &>/dev/null; then
            healthy=$((healthy + 1))
        fi
        
        # Check SearXNG
        if curl -s http://localhost:8080/healthz &>/dev/null; then
            healthy=$((healthy + 1))
        fi
        
        if [ $healthy -eq 3 ]; then
            break
        fi
        
        attempt=$((attempt + 1))
        sleep 1
        printf "."
    done
    echo ""
    
    # Show status
    print_msg "$GREEN" "Docker services started:"
    docker compose ps --format "  {{.Name}}: {{.Status}}" 2>/dev/null || docker compose ps
}

# Stop Docker services
stop_docker() {
    print_header "Stopping Docker Services"
    
    cd "$PROJECT_DIR"
    docker compose down 2>&1 | grep -v "^time=" || true
    print_msg "$GREEN" "Docker services stopped"
}

# Start FastAPI application
start_api() {
    local mode="${1:-development}"
    
    print_header "Starting FastAPI Application ($mode)"

    cd "$BACKEND_DIR"
    source "$VENV_DIR/bin/activate"
    
    # Check if already running
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            print_msg "$YELLOW" "API already running (PID: $pid)"
            return 0
        fi
        rm -f "$PID_FILE"
    fi
    
    if [ "$mode" = "production" ]; then
        print_msg "$YELLOW" "Starting in production mode with $API_WORKERS workers..."
        nohup uvicorn app.main:app \
            --host "$API_HOST" \
            --port "$API_PORT" \
            --workers "$API_WORKERS" \
            --access-log \
            --log-level info \
            > "$LOG_DIR/api.log" 2>&1 &
    else
        print_msg "$YELLOW" "Starting in development mode with auto-reload..."
        nohup uvicorn app.main:app \
            --host "$API_HOST" \
            --port "$API_PORT" \
            --reload \
            --reload-dir app \
            --log-level debug \
            > "$LOG_DIR/api.log" 2>&1 &
    fi
    
    local pid=$!
    echo $pid > "$PID_FILE"
    
    # Wait for API to start
    sleep 2
    
    if kill -0 "$pid" 2>/dev/null; then
        print_msg "$GREEN" "API started (PID: $pid)"
        print_msg "$GREEN" "  URL: http://$API_HOST:$API_PORT"
        print_msg "$GREEN" "  Docs: http://$API_HOST:$API_PORT/docs"
        print_msg "$GREEN" "  Logs: $LOG_DIR/api.log"
    else
        print_msg "$RED" "Failed to start API. Check logs: $LOG_DIR/api.log"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Stop FastAPI application
stop_api() {
    print_header "Stopping FastAPI Application"
    
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            print_msg "$YELLOW" "Stopping API (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            
            # Wait for graceful shutdown
            local attempts=0
            while kill -0 "$pid" 2>/dev/null && [ $attempts -lt 10 ]; do
                sleep 1
                attempts=$((attempts + 1))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
        rm -f "$PID_FILE"
        print_msg "$GREEN" "API stopped"
    else
        # Try to find and kill uvicorn processes
        pkill -f "uvicorn app.main:app" 2>/dev/null || true
        print_msg "$YELLOW" "No PID file found, cleaned up any stray processes"
    fi
}

# Start API in foreground (useful for development)
start_api_foreground() {
    local mode="${1:-development}"
    
    print_header "Starting FastAPI Application (foreground, $mode)"

    cd "$BACKEND_DIR"
    source "$VENV_DIR/bin/activate"
    
    if [ "$mode" = "production" ]; then
        uvicorn app.main:app \
            --host "$API_HOST" \
            --port "$API_PORT" \
            --workers "$API_WORKERS" \
            --access-log \
            --log-level info
    else
        uvicorn app.main:app \
            --host "$API_HOST" \
            --port "$API_PORT" \
            --reload \
            --reload-dir app \
            --log-level debug
    fi
}

# Show status of all services
show_status() {
    print_header "Service Status"
    
    cd "$PROJECT_DIR"
    
    echo ""
    print_msg "$BLUE" "Docker Services:"
    if docker compose ps -q 2>/dev/null | grep -q .; then
        docker compose ps --format "  {{.Name}}: {{.Status}}" 2>/dev/null || docker compose ps
    else
        print_msg "$YELLOW" "  No Docker services running"
    fi
    
    echo ""
    print_msg "$BLUE" "FastAPI Application:"
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            print_msg "$GREEN" "  Running (PID: $pid)"
            print_msg "$GREEN" "  URL: http://$API_HOST:$API_PORT"
        else
            print_msg "$RED" "  Not running (stale PID file)"
            rm -f "$PID_FILE"
        fi
    else
        print_msg "$YELLOW" "  Not running"
    fi
    
    echo ""
    print_msg "$BLUE" "Health Checks:"
    
    # Check PostgreSQL
    if docker compose exec -T postgres pg_isready -U unsearch &>/dev/null 2>&1; then
        print_msg "$GREEN" "  PostgreSQL: healthy"
    else
        print_msg "$RED" "  PostgreSQL: not available"
    fi
    
    # Check Redis
    if docker compose exec -T redis redis-cli ping &>/dev/null 2>&1; then
        print_msg "$GREEN" "  Redis: healthy"
    else
        print_msg "$RED" "  Redis: not available"
    fi
    
    # Check SearXNG
    if curl -s http://localhost:8080/healthz &>/dev/null; then
        print_msg "$GREEN" "  SearXNG: healthy"
    else
        print_msg "$RED" "  SearXNG: not available"
    fi
    
    # Check API
    if curl -s http://localhost:$API_PORT/health &>/dev/null; then
        print_msg "$GREEN" "  API: healthy"
    else
        print_msg "$RED" "  API: not available"
    fi
}

# Show logs
show_logs() {
    local service="${1:-all}"
    local lines="${2:-50}"
    
    print_header "Logs ($service)"
    
    cd "$PROJECT_DIR"
    
    case "$service" in
        api)
            if [ -f "$LOG_DIR/api.log" ]; then
                tail -n "$lines" "$LOG_DIR/api.log"
            else
                print_msg "$YELLOW" "No API logs found"
            fi
            ;;
        docker|all)
            docker compose logs --tail="$lines" 2>&1 | grep -v "^time=" || true
            if [ "$service" = "all" ] && [ -f "$LOG_DIR/api.log" ]; then
                echo ""
                print_msg "$BLUE" "--- API Logs ---"
                tail -n "$lines" "$LOG_DIR/api.log"
            fi
            ;;
        postgres|redis|searxng)
            docker compose logs --tail="$lines" "$service" 2>&1 | grep -v "^time=" || true
            ;;
        *)
            print_msg "$RED" "Unknown service: $service"
            print_msg "$YELLOW" "Available: api, docker, postgres, redis, searxng, all"
            ;;
    esac
}

# Follow logs in real-time
follow_logs() {
    local service="${1:-api}"
    
    print_header "Following Logs ($service)"
    
    cd "$PROJECT_DIR"
    
    case "$service" in
        api)
            if [ -f "$LOG_DIR/api.log" ]; then
                tail -f "$LOG_DIR/api.log"
            else
                print_msg "$YELLOW" "No API logs found. Start the API first."
            fi
            ;;
        docker)
            docker compose logs -f 2>&1 | grep -v "^time=" || true
            ;;
        postgres|redis|searxng)
            docker compose logs -f "$service" 2>&1 | grep -v "^time=" || true
            ;;
        *)
            print_msg "$RED" "Unknown service: $service"
            ;;
    esac
}

# Run tests
run_tests() {
    local test_type="${1:-unit}"
    
    print_header "Running Tests ($test_type)"

    cd "$BACKEND_DIR"
    source "$VENV_DIR/bin/activate"
    
    case "$test_type" in
        unit)
            python -m pytest tests/unit/ -v --no-cov
            ;;
        integration)
            python -m pytest tests/integration/ -v --no-cov
            ;;
        rag)
            python -m pytest tests/unit/test_rag_service.py -v --no-cov
            ;;
        all)
            python -m pytest tests/ -v --no-cov
            ;;
        *)
            print_msg "$RED" "Unknown test type: $test_type"
            print_msg "$YELLOW" "Available: unit, integration, rag, all"
            ;;
    esac
}

# Initialize database
init_db() {
    print_header "Initializing Database"

    cd "$BACKEND_DIR"
    source "$VENV_DIR/bin/activate"

    # Run alembic migrations
    if [ -d "alembic" ]; then
        print_msg "$YELLOW" "Running database migrations..."
        alembic upgrade head
        print_msg "$GREEN" "Database initialized"
    else
        print_msg "$YELLOW" "No alembic directory found, skipping migrations"
    fi
}

# Clean up
cleanup() {
    print_header "Cleaning Up"
    
    cd "$PROJECT_DIR"
    
    # Stop all services
    stop_api
    stop_docker
    
    # Remove temporary files
    print_msg "$YELLOW" "Removing temporary files..."
    rm -rf "$PROJECT_DIR/__pycache__" 2>/dev/null || true
    rm -rf "$PROJECT_DIR/.pytest_cache" 2>/dev/null || true
    find "$PROJECT_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    
    print_msg "$GREEN" "Cleanup complete"
}

# Show help
show_help() {
    cat << EOF
UnSearch Service Manager

Usage: $0 <command> [options]

Commands:
  start [mode]      Start all services (mode: development|production, default: development)
  stop              Stop all services
  restart [mode]    Restart all services
  status            Show status of all services
  
  docker:start      Start Docker services only
  docker:stop       Stop Docker services only
  docker:restart    Restart Docker services only
  
  api:start [mode]  Start FastAPI in background
  api:stop          Stop FastAPI
  api:restart       Restart FastAPI
  api:dev           Start FastAPI in foreground (development)
  api:prod          Start FastAPI in foreground (production)
  
  pm2:start         Start all services via PM2 (production)
  pm2:stop          Stop PM2 services
  pm2:restart       Restart PM2 services
  pm2:status        Show PM2 status and health checks
  pm2:logs [svc]    Show PM2 logs (service: unsearch-backend|unsearch-frontend|all)
  pm2:follow [svc]  Follow PM2 logs in real-time
  
  deploy:backend    Kill & restart backend with latest code
  deploy:frontend   Rebuild & restart frontend (npm build + pm2 restart)
  deploy:searxng    Restart SearXNG Docker container
  deploy:all        Full redeploy: backend + frontend rebuild + searxng
  
  logs [service]    Show logs (service: api|docker|postgres|redis|searxng|all)
  logs:follow [svc] Follow logs in real-time
  
  test [type]       Run tests (type: unit|integration|rag|all)
  
  setup             Setup Python environment and install dependencies
  init-db           Initialize/migrate database
  cleanup           Stop services and clean temporary files
  
  help              Show this help message

Environment Variables:
  API_HOST          API host (default: 0.0.0.0)
  API_PORT          API port (default: 8000)
  API_WORKERS       Number of workers for production (default: 4)

Production URLs:
  https://unsearch.dev         Frontend
  https://api.unsearch.dev     Backend API
  https://api.unsearch.dev/docs API Documentation
  https://edge.unsearch.dev    Edge Worker

Examples:
  $0 start                    # Start all services in development mode
  $0 pm2:start                # Start production services via PM2
  $0 pm2:status               # Show PM2 status and health
  $0 pm2:logs unsearch-backend  # Show backend logs
  $0 pm2:follow               # Follow all PM2 logs
  $0 api:dev                  # Start API in foreground with auto-reload
  $0 logs api                 # Show API logs
  $0 test rag                 # Run RAG tests
  
  # Quick Deploy Commands
  $0 deploy:backend           # Restart backend with new code
  $0 deploy:frontend          # Rebuild and restart frontend
  $0 deploy:searxng           # Restart SearXNG
  $0 deploy:all               # Full redeploy everything
EOF
}

# PM2 Functions
pm2_start() {
    print_header "Starting Services via PM2"
    
    cd "$PROJECT_DIR"
    
    # Ensure Docker services are running
    start_docker
    
    # Load environment and start PM2
    source "$PROJECT_DIR/.env" 2>/dev/null || true
    
    if pm2 list 2>/dev/null | grep -q "unsearch"; then
        print_msg "$YELLOW" "PM2 services already running, restarting..."
        pm2 restart ecosystem.config.js
    else
        print_msg "$YELLOW" "Starting PM2 services..."
        pm2 start ecosystem.config.js
    fi
    
    pm2 save
    
    sleep 3
    pm2_status
}

pm2_stop() {
    print_header "Stopping PM2 Services"
    
    pm2 stop unsearch-backend unsearch-frontend 2>/dev/null || true
    pm2 save 2>/dev/null || true
    
    print_msg "$GREEN" "PM2 services stopped"
}

pm2_restart() {
    print_header "Restarting PM2 Services"
    
    cd "$PROJECT_DIR"
    source "$PROJECT_DIR/.env" 2>/dev/null || true
    
    # Stop unsearch PM2 services first
    print_msg "$YELLOW" "Stopping unsearch PM2 services..."
    pm2 stop unsearch-backend unsearch-frontend 2>/dev/null || true
    sleep 1
    
    # Kill any orphaned processes on port 8000
    print_msg "$YELLOW" "Cleaning up orphaned processes..."
    local port_pids=$(lsof -ti :8000 2>/dev/null || true)
    if [ -n "$port_pids" ]; then
        echo "$port_pids" | xargs kill -9 2>/dev/null || true
    fi
    pkill -9 -f "uvicorn app.main:app" 2>/dev/null || true
    sleep 2
    
    # Verify port 8000 is free
    if lsof -ti :8000 &>/dev/null; then
        print_msg "$RED" "Warning: Port 8000 still in use, forcing cleanup..."
        lsof -ti :8000 | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
    
    # Start unsearch PM2 services
    print_msg "$YELLOW" "Starting PM2 services..."
    pm2 restart unsearch-backend unsearch-frontend
    pm2 save
    
    sleep 5
    pm2_status
}

pm2_status() {
    print_header "PM2 Status"
    
    pm2 status
    
    echo ""
    print_msg "$BLUE" "Service Health:"
    
    # Check API
    if curl -s http://localhost:$API_PORT/health &>/dev/null; then
        print_msg "$GREEN" "  Backend API: healthy (http://localhost:$API_PORT)"
    else
        print_msg "$RED" "  Backend API: not responding"
    fi
    
    # Check Frontend
    if curl -s http://localhost:3000 &>/dev/null; then
        print_msg "$GREEN" "  Frontend: healthy (http://localhost:3000)"
    else
        print_msg "$RED" "  Frontend: not responding"
    fi
    
    echo ""
    print_msg "$BLUE" "Public URLs:"
    print_msg "$GREEN" "  https://unsearch.dev"
    print_msg "$GREEN" "  https://api.unsearch.dev"
    print_msg "$GREEN" "  https://api.unsearch.dev/docs"
    print_msg "$GREEN" "  https://edge.unsearch.dev"
}

pm2_logs() {
    local service="${1:-all}"
    local lines="${2:-50}"
    
    print_header "PM2 Logs ($service)"
    
    if [ "$service" = "all" ]; then
        pm2 logs --lines "$lines" --nostream
    else
        pm2 logs "$service" --lines "$lines" --nostream
    fi
}

pm2_follow() {
    local service="${1:-all}"
    
    print_header "Following PM2 Logs ($service)"
    
    if [ "$service" = "all" ]; then
        pm2 logs
    else
        pm2 logs "$service"
    fi
}

# Main entry point
main() {
    local command="${1:-help}"
    shift || true
    
    case "$command" in
        start)
            check_prerequisites
            setup_python
            start_docker
            start_api "${1:-development}"
            echo ""
            show_status
            ;;
        stop)
            stop_api
            stop_docker
            ;;
        restart)
            stop_api
            stop_docker
            sleep 2
            start_docker
            start_api "${1:-development}"
            show_status
            ;;
        status)
            show_status
            ;;
        docker:start)
            start_docker
            ;;
        docker:stop)
            stop_docker
            ;;
        docker:restart)
            stop_docker
            sleep 2
            start_docker
            ;;
        api:start)
            start_api "${1:-development}"
            ;;
        api:stop)
            stop_api
            ;;
        api:restart)
            stop_api
            sleep 1
            start_api "${1:-development}"
            ;;
        api:dev)
            start_api_foreground "development"
            ;;
        api:prod)
            start_api_foreground "production"
            ;;
        pm2:start)
            pm2_start
            ;;
        pm2:stop)
            pm2_stop
            ;;
        pm2:restart)
            pm2_restart
            ;;
        pm2:status)
            pm2_status
            ;;
        pm2:logs)
            pm2_logs "${1:-all}" "${2:-50}"
            ;;
        pm2:follow)
            pm2_follow "${1:-all}"
            ;;
        # Quick deploy commands
        deploy:backend)
            print_header "Redeploying Backend"
            
            # Step 1: Stop PM2 backend process first
            print_msg "$YELLOW" "Stopping PM2 backend process..."
            pm2 stop unsearch-backend 2>/dev/null || true
            sleep 1
            
            # Step 2: Kill any orphaned uvicorn/python processes on port 8000
            print_msg "$YELLOW" "Killing any processes on port 8000..."
            local port_pids=$(lsof -ti :8000 2>/dev/null || true)
            if [ -n "$port_pids" ]; then
                echo "$port_pids" | xargs kill -9 2>/dev/null || true
                sleep 1
            fi
            
            # Step 3: Kill any remaining uvicorn processes
            pkill -9 -f "uvicorn app.main:app" 2>/dev/null || true
            sleep 1
            
            # Step 4: Verify port is free
            if lsof -ti :8000 &>/dev/null; then
                print_msg "$RED" "Warning: Port 8000 still in use, forcing cleanup..."
                lsof -ti :8000 | xargs kill -9 2>/dev/null || true
                sleep 2
            fi
            
            # Step 5: Start backend via PM2
            print_msg "$YELLOW" "Starting backend via PM2..."
            pm2 start unsearch-backend
            
            # Step 6: Wait and verify
            sleep 5
            if curl -s http://localhost:8000/health &>/dev/null; then
                print_msg "$GREEN" "Backend redeployed successfully"
            else
                print_msg "$RED" "Backend health check failed"
                pm2 logs unsearch-backend --lines 20 --nostream
            fi
            ;;
        deploy:frontend)
            print_header "Rebuilding & Redeploying Frontend"
            cd "$PROJECT_DIR/apps/web"
            print_msg "$YELLOW" "Building frontend..."
            npm run build
            print_msg "$YELLOW" "Restarting frontend..."
            pm2 restart unsearch-frontend
            sleep 5
            if curl -s http://localhost:3000 &>/dev/null; then
                print_msg "$GREEN" "Frontend redeployed successfully"
            else
                print_msg "$RED" "Frontend health check failed"
            fi
            ;;
        deploy:searxng)
            print_header "Restarting SearXNG"
            cd "$PROJECT_DIR"
            docker compose restart searxng
            sleep 5
            if curl -s http://localhost:8080/healthz &>/dev/null; then
                print_msg "$GREEN" "SearXNG restarted successfully"
            else
                print_msg "$YELLOW" "SearXNG may still be starting..."
            fi
            ;;
        deploy:all)
            print_header "Full Redeploy - All Services"
            
            # Step 1: Stop unsearch PM2 services first
            print_msg "$YELLOW" "1/5 Stopping unsearch PM2 services..."
            pm2 stop unsearch-backend unsearch-frontend 2>/dev/null || true
            sleep 1
            
            # Step 2: Kill any orphaned processes on backend port
            print_msg "$YELLOW" "2/5 Cleaning up orphaned processes..."
            local port_pids=$(lsof -ti :8000 2>/dev/null || true)
            if [ -n "$port_pids" ]; then
                echo "$port_pids" | xargs kill -9 2>/dev/null || true
            fi
            pkill -9 -f "uvicorn app.main:app" 2>/dev/null || true
            sleep 2
            
            # Verify port 8000 is free
            if lsof -ti :8000 &>/dev/null; then
                print_msg "$RED" "Warning: Port 8000 still in use, forcing cleanup..."
                lsof -ti :8000 | xargs kill -9 2>/dev/null || true
                sleep 2
            fi
            
            # Step 3: Restart SearXNG
            print_msg "$YELLOW" "3/5 Restarting SearXNG..."
            cd "$PROJECT_DIR"
            docker compose restart searxng
            
            # Step 4: Rebuild frontend
            print_msg "$YELLOW" "4/5 Rebuilding frontend..."
            cd "$PROJECT_DIR/apps/web"
            npm run build
            
            # Step 5: Start unsearch PM2 services
            print_msg "$YELLOW" "5/5 Starting unsearch PM2 services..."
            cd "$PROJECT_DIR"
            pm2 restart unsearch-backend unsearch-frontend
            
            # Wait for services to initialize
            sleep 8
            
            # Health checks
            print_msg "$BLUE" "Health Checks:"
            curl -s http://localhost:8000/health &>/dev/null && print_msg "$GREEN" "  Backend: healthy" || print_msg "$RED" "  Backend: failed"
            curl -s http://localhost:3000 &>/dev/null && print_msg "$GREEN" "  Frontend: healthy" || print_msg "$RED" "  Frontend: failed"
            curl -s http://localhost:8080/healthz &>/dev/null && print_msg "$GREEN" "  SearXNG: healthy" || print_msg "$YELLOW" "  SearXNG: starting..."
            ;;
        logs)
            show_logs "${1:-all}" "${2:-50}"
            ;;
        logs:follow)
            follow_logs "${1:-api}"
            ;;
        test)
            run_tests "${1:-unit}"
            ;;
        setup)
            check_prerequisites
            setup_python
            ;;
        init-db)
            init_db
            ;;
        cleanup)
            cleanup
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_msg "$RED" "Unknown command: $command"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main
main "$@"
