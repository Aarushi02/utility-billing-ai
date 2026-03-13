#!/usr/bin/env bash

# Utility Billing AI Local Stack Runner
# This script manages the local development stack (API + Streamlit UI)

set -e

# Configuration
API_HOST="127.0.0.1"
API_PORT="8000"
UI_PORT="8501"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect venv activate path for Linux/macOS vs Windows Git Bash
if [ -f "$SCRIPT_DIR/venv/Scripts/activate" ]; then
    VENV_ACTIVATE="$SCRIPT_DIR/venv/Scripts/activate"
elif [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    VENV_ACTIVATE="$SCRIPT_DIR/venv/bin/activate"
else
    VENV_ACTIVATE=""
fi

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

# Function to check if a command exists
has_cmd() {
    command -v "$1" >/dev/null 2>&1
}

# Function to activate virtual environment
activate_venv() {
    if [ -z "$VENV_ACTIVATE" ]; then
        print_error "Virtual environment activate script not found."
        print_error "Expected one of:"
        print_error "  $SCRIPT_DIR/venv/Scripts/activate"
        print_error "  $SCRIPT_DIR/venv/bin/activate"
        exit 1
    fi

    # shellcheck disable=SC1090
    source "$VENV_ACTIVATE"
}

# Function to check if a port is in use
check_port() {
    local port=$1

    if has_cmd lsof; then
        lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1
        return $?
    elif has_cmd netstat; then
        netstat -an 2>/dev/null | grep -E "[\.:]$port .*LISTEN" >/dev/null 2>&1
        return $?
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
    while true; do
        if has_cmd curl && curl -s --max-time 2 "$url" >/dev/null 2>&1; then
            break
        fi

        if [ "$count" -ge "$timeout" ]; then
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

    if check_port "$API_PORT"; then
        print_warning "Port $API_PORT is already in use. Skipping API start."
        return 0
    fi

    cd "$SCRIPT_DIR"
    activate_venv
    mkdir -p logs
    nohup python -m uvicorn src.api.main:app --host "$API_HOST" --port "$API_PORT" > logs/api.log 2>&1 &
    echo $! > .api_pid

    wait_for_service "http://$API_HOST:$API_PORT/api/v1/health/live"
}

# Function to start UI
start_ui() {
    print_status "Starting Streamlit UI..."

    if check_port "$UI_PORT"; then
        print_warning "Port $UI_PORT is already in use. Skipping UI start."
        return 0
    fi

    cd "$SCRIPT_DIR"
    activate_venv
    export API_BASE_URL="http://$API_HOST:$API_PORT"
    mkdir -p logs
    nohup streamlit run app/streamlit_app.py --server.address "$API_HOST" --server.port "$UI_PORT" > logs/ui.log 2>&1 &
    echo $! > .ui_pid

    wait_for_service "http://$API_HOST:$UI_PORT"
}

# Function to open browser
open_browser() {
    local url=$1
    print_status "Opening browser at $url"

    # Linux
    if has_cmd xdg-open; then
        xdg-open "$url" >/dev/null 2>&1 &
        return 0
    fi

    # macOS
    if has_cmd open; then
        open "$url" >/dev/null 2>&1 &
        return 0
    fi

    # Windows PowerShell
    if has_cmd powershell.exe; then
        powershell.exe -NoProfile -Command "Start-Process '$url'" >/dev/null 2>&1 &
        return 0
    fi

    # Windows cmd
    if has_cmd cmd.exe; then
        cmd.exe /c start "" "$url" >/dev/null 2>&1
        return 0
    fi

    print_warning "Could not automatically open browser. Please visit $url manually."
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."

    if [ -f .api_pid ]; then
        kill "$(cat .api_pid)" 2>/dev/null || true
        rm -f .api_pid
        print_status "API stopped"
    fi

    if [ -f .ui_pid ]; then
        kill "$(cat .ui_pid)" 2>/dev/null || true
        rm -f .ui_pid
        print_status "UI stopped"
    fi
}

# Function to check status
check_status() {
    print_status "Checking service status..."

    if check_port "$API_PORT"; then
        print_status "API is running on port $API_PORT"
    else
        print_warning "API is not running on port $API_PORT"
    fi

    if check_port "$UI_PORT"; then
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
        open_browser "http://$API_HOST:$UI_PORT"
        ;;
    status)
        check_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac