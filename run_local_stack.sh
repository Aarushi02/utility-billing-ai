#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'
trap 'echo "❌ Failed at line $LINENO: $BASH_COMMAND" >&2' ERR

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$ROOT_DIR/.pids"
API_PID_FILE="$PID_DIR/api.pid"
UI_PID_FILE="$PID_DIR/streamlit.pid"
API_LOG="$ROOT_DIR/logs/api.local.log"
UI_LOG="$ROOT_DIR/logs/streamlit.local.log"
API_HOST="127.0.0.1"
API_PORT="8000"
UI_PORT="8501"

mkdir -p "$PID_DIR" "$ROOT_DIR/logs"

detect_venv_python() {
  # Linux/macOS
  if [[ -x "$ROOT_DIR/venv/bin/python" ]]; then
    echo "$ROOT_DIR/venv/bin/python"
    return 0
  fi

  # Windows (PowerShell-created venv)
  if [[ -x "$ROOT_DIR/venv/Scripts/python.exe" ]]; then
    echo "$ROOT_DIR/venv/Scripts/python.exe"
    return 0
  fi

  # Sometimes Git Bash exposes a non-.exe shim
  if [[ -x "$ROOT_DIR/venv/Scripts/python" ]]; then
    echo "$ROOT_DIR/venv/Scripts/python"
    return 0
  fi

  return 1
}

VENV_PY=""
require_python() {
  if ! VENV_PY="$(detect_venv_python)"; then
    echo "❌ Missing venv python."
    echo "Expected one of:"
    echo "  - $ROOT_DIR/venv/bin/python"
    echo "  - $ROOT_DIR/venv/Scripts/python.exe"
    echo ""
    echo "Create it first:"
    echo "  python -m venv venv"
    echo "  (Windows)  .\\venv\\Scripts\\pip install -r requirements.txt"
    echo "  (Linux/Mac) ./venv/bin/pip install -r requirements.txt"
    exit 1
  fi
}

have_cmd() { command -v "$1" >/dev/null 2>&1; }

is_pid_running() {
  local pid="$1"
  [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null
}

read_pid() {
  local file="$1"
  [[ -f "$file" ]] && cat "$file"
}

kill_from_pid_file() {
  local file="$1"
  local name="$2"
  local pid
  pid="$(read_pid "$file" || true)"

  if [[ -n "${pid:-}" ]] && is_pid_running "$pid"; then
    kill "$pid" 2>/dev/null || true
    sleep 1
    if is_pid_running "$pid"; then
      kill -9 "$pid" 2>/dev/null || true
    fi
    echo "🛑 Stopped $name (PID $pid)"
  fi

  rm -f "$file"
}

api_is_healthy() {
  local url="http://${API_HOST}:${API_PORT}/api/v1/health/live"

  if have_cmd curl; then
    curl -fsS --max-time 2 "$url" >/dev/null 2>&1
    return $?
  fi

  # Fallback if curl isn't available: try python request
  "$VENV_PY" - <<PY >/dev/null 2>&1 || return 1
import urllib.request
urllib.request.urlopen("${url}", timeout=2).read()
PY
}

wait_for_api() {
  local attempts=30
  local url="http://${API_HOST}:${API_PORT}/api/v1/health/live"
  for ((i=1; i<=attempts; i++)); do
    if api_is_healthy; then
      echo "✅ API is healthy: $url"
      return 0
    fi
    sleep 1
  done
  echo "❌ API did not become healthy in time. Check: $API_LOG"
  return 1
}

start_api() {
  if api_is_healthy; then
    echo "ℹ️ API already reachable at http://${API_HOST}:${API_PORT}"
    return
  fi

  echo "▶️ Starting API on ${API_HOST}:${API_PORT} ..."
  nohup "$VENV_PY" -m uvicorn src.api.main:app --host "$API_HOST" --port "$API_PORT" >"$API_LOG" 2>&1 &
  local pid=$!
  echo "$pid" > "$API_PID_FILE"

  wait_for_api
  echo "🌐 Swagger: http://${API_HOST}:${API_PORT}/docs"
}

start_ui() {
  local existing_pid
  existing_pid="$(read_pid "$UI_PID_FILE" || true)"

  if [[ -n "${existing_pid:-}" ]] && is_pid_running "$existing_pid"; then
    echo "ℹ️ Streamlit already running on http://127.0.0.1:${UI_PORT} (PID $existing_pid)"
    return
  fi

  echo "▶️ Starting Streamlit on 127.0.0.1:${UI_PORT} ..."
  nohup env API_BASE_URL="http://${API_HOST}:${API_PORT}" \
    "$VENV_PY" -m streamlit run "$ROOT_DIR/app/streamlit_app.py" \
      --server.address 127.0.0.1 \
      --server.port "$UI_PORT" >"$UI_LOG" 2>&1 &
  local pid=$!
  echo "$pid" > "$UI_PID_FILE"
  echo "🌐 Streamlit: http://127.0.0.1:${UI_PORT}"
}

ui_is_listening() {
  # Prefer lsof if available
  if have_cmd lsof; then
    lsof -nP -iTCP:"$UI_PORT" -sTCP:LISTEN >/dev/null 2>&1
    return $?
  fi

  # Fallback: try HTTP request to Streamlit root
  if have_cmd curl; then
    curl -fsS --max-time 2 "http://127.0.0.1:${UI_PORT}" >/dev/null 2>&1
    return $?
  fi

  # Last fallback: python urllib
  "$VENV_PY" - <<PY >/dev/null 2>&1 || return 1
import urllib.request
urllib.request.urlopen("http://127.0.0.1:${UI_PORT}", timeout=2).read()
PY
}

print_status() {
  echo ""
  echo "📌 Stack status"

  if api_is_healthy; then
    echo "- API: UP    (http://${API_HOST}:${API_PORT})"
    echo "- Docs:      http://${API_HOST}:${API_PORT}/docs"
  else
    echo "- API: DOWN"
  fi

  if ui_is_listening; then
    echo "- UI:  UP    (http://127.0.0.1:${UI_PORT})"
  else
    echo "- UI:  DOWN"
  fi

  echo "- API log: $API_LOG"
  echo "- UI log:  $UI_LOG"
}

cmd_start() { require_python; start_api; start_ui; print_status; }
cmd_stop()  { kill_from_pid_file "$UI_PID_FILE" "Streamlit"; kill_from_pid_file "$API_PID_FILE" "API"; echo "✅ Local stack stopped"; }
cmd_restart(){ cmd_stop; cmd_start; }

cmd_logs() {
  echo "== API log (tail) =="
  tail -n 40 "$API_LOG" 2>/dev/null || echo "No API log yet"
  echo ""
  echo "== Streamlit log (tail) =="
  tail -n 40 "$UI_LOG" 2>/dev/null || echo "No Streamlit log yet"
}

usage() {
  cat <<EOF
Usage: ./run_local_stack.sh <command>

Commands:
  start    Start API + Streamlit locally
  stop     Stop API + Streamlit started by this script
  restart  Restart both services
  status   Show current status
  logs     Tail recent API/UI logs
EOF
}

case "${1:-}" in
  start) cmd_start ;;
  stop) cmd_stop ;;
  restart) cmd_restart ;;
  status) require_python; print_status ;;
  logs) cmd_logs ;;
  *) usage; exit 1 ;;
esac