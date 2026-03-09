#!/bin/bash

# Utility Billing AI Local Stack Runner
# This script manages the local development stack (API + Streamlit UI)

set -e

# Configuration
API_HOST="127.0.0.1"
API_PORT="8000"
UI_PORT="8501"
VENV_PATH="./venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local timeout=30
    local count=0

    print_status "Waiting for service at $url..."
    while ! curl -s --max-time 2 "$url" > /dev/null; do
        if [ $count -ge $timeout ]; then
            print_error "Service at $url did not start within $timeout seconds"
            return 1
        fi
        sleep 1
        count=$((count + 1))
    done
    print_status "Service is ready!"
}

# Function to start API
start_api() {
    print_status "Starting API server..."

    if check_port $API_PORT; then
        print_warning "Port $API_PORT is already in use. Skipping API start."
        return 0
    fi

    cd "$SCRIPT_DIR"
    source "$VENV_PATH/bin/activate"
    nohup python -m uvicorn src.api.main:app --host $API_HOST --port $API_PORT > logs/api.log 2>&1 &
    echo $! > .api_pid

    wait_for_service "http://$API_HOST:$API_PORT/api/v1/health/live"
}

# Function to start UI
start_ui() {
    print_status "Starting Streamlit UI..."

    if check_port $UI_PORT; then
        print_warning "Port $UI_PORT is already in use. Skipping UI start."
        return 0
    fi

    cd "$SCRIPT_DIR"
    source "$VENV_PATH/bin/activate"
    export API_BASE_URL="http://$API_HOST:$API_PORT"
    nohup streamlit run app/streamlit_app.py --server.address $API_HOST --server.port $UI_PORT > logs/ui.log 2>&1 &
    echo $! > .ui_pid

    wait_for_service "http://$API_HOST:$UI_PORT"
}

# Function to open browser
open_browser() {
    local url=$1
    print_status "Opening browser at $url"

    # Cross-platform browser opening
    if command -v xdg-open > /dev/null; then
        xdg-open "$url" 2>/dev/null &
    elif command -v open > /dev/null; then
        open "$url" 2>/dev/null &
    elif command -v start > /dev/null; then
        start "$url" 2>/dev/null &
    else
        print_warning "Could not automatically open browser. Please visit $url manually."
    fi
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."

    if [ -f .api_pid ]; then
        kill $(cat .api_pid) 2>/dev/null || true
        rm .api_pid
        print_status "API stopped"
    fi

    if [ -f .ui_pid ]; then
        kill $(cat .ui_pid) 2>/dev/null || true
        rm .ui_pid
        print_status "UI stopped"
    fi
}

# Function to check status
check_status() {
    print_status "Checking service status..."

    if check_port $API_PORT; then
        print_status "API is running on port $API_PORT"
    else
        print_warning "API is not running on port $API_PORT"
    fi

    if check_port $UI_PORT; then
        print_status "UI is running on port $UI_PORT"
    else
        print_warning "UI is not running on port $UI_PORT"
    fi
}

# Main logic
case "${1:-start}" in
    start)
        print_status "Starting Utility Billing AI local stack..."
        mkdir -p logs
        start_api
        start_ui
        print_status "All services started successfully!"
        open_browser "http://$API_HOST:$UI_PORT"
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        start_api
        start_ui
        ;;
    status)
        check_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac