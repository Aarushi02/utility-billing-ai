#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$ROOT_DIR/venv/bin/python"
PID_DIR="$ROOT_DIR/.pids"
API_PID_FILE="$PID_DIR/api.pid"
UI_PID_FILE="$PID_DIR/streamlit.pid"
API_LOG="$ROOT_DIR/logs/api.local.log"
UI_LOG="$ROOT_DIR/logs/streamlit.local.log"
API_HOST="127.0.0.1"
API_PORT="8000"
UI_PORT="8501"

mkdir -p "$PID_DIR" "$ROOT_DIR/logs"

require_python() {
  if [[ ! -x "$VENV_PY" ]]; then
    echo "❌ Missing venv python at: $VENV_PY"
    echo "Create it first: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
  fi
}

is_pid_running() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

read_pid() {
  local file="$1"
  if [[ -f "$file" ]]; then
    cat "$file"
  fi
}

kill_from_pid_file() {
  local file="$1"
  local name="$2"
  local pid
  pid="$(read_pid "$file" || true)"
  if [[ -n "${pid:-}" ]] && is_pid_running "$pid"; then
    kill "$pid" || true
    sleep 1
    if is_pid_running "$pid"; then
      kill -9 "$pid" || true
    fi
    echo "🛑 Stopped $name (PID $pid)"
  fi
  rm -f "$file"
}

wait_for_api() {
  local attempts=30
  local url="http://${API_HOST}:${API_PORT}/api/v1/health/live"
  for ((i=1; i<=attempts; i++)); do
    if curl -fsS --max-time 2 "$url" >/dev/null 2>&1; then
      echo "✅ API is healthy: $url"
      return 0
    fi
    sleep 1
  done
  echo "❌ API did not become healthy in time. Check: $API_LOG"
  return 1
}

start_api() {
  if curl -fsS --max-time 2 "http://${API_HOST}:${API_PORT}/api/v1/health/live" >/dev/null 2>&1; then
    echo "ℹ️ API already reachable at http://${API_HOST}:${API_PORT}"
    return
  fi

  echo "▶️ Starting API on ${API_HOST}:${API_PORT} ..."
  nohup "$VENV_PY" -m uvicorn src.api.main:app --host "$API_HOST" --port "$API_PORT" >"$API_LOG" 2>&1 &
  local pid=$!
  echo "$pid" > "$API_PID_FILE"

  if ! wait_for_api; then
    exit 1
  fi

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
  nohup env API_BASE_URL="http://${API_HOST}:${API_PORT}" "$VENV_PY" -m streamlit run "$ROOT_DIR/app/streamlit_app.py" --server.address 127.0.0.1 --server.port "$UI_PORT" >"$UI_LOG" 2>&1 &
  local pid=$!
  echo "$pid" > "$UI_PID_FILE"
  echo "🌐 Streamlit: http://127.0.0.1:${UI_PORT}"
}

print_status() {
  echo "\n📌 Stack status"
  if curl -fsS --max-time 2 "http://${API_HOST}:${API_PORT}/api/v1/health/live" >/dev/null 2>&1; then
    echo "- API: UP    (http://${API_HOST}:${API_PORT})"
    echo "- Docs:      http://${API_HOST}:${API_PORT}/docs"
  else
    echo "- API: DOWN"
  fi

  if lsof -nP -iTCP:"$UI_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "- UI:  UP    (http://127.0.0.1:${UI_PORT})"
  else
    echo "- UI:  DOWN"
  fi

  echo "- API log: $API_LOG"
  echo "- UI log:  $UI_LOG"
}

cmd_start() {
  require_python
  start_api
  start_ui
  print_status
}

cmd_stop() {
  kill_from_pid_file "$UI_PID_FILE" "Streamlit"
  kill_from_pid_file "$API_PID_FILE" "API"
  echo "✅ Local stack stopped"
}

cmd_restart() {
  cmd_stop
  cmd_start
}

cmd_logs() {
  echo "== API log (tail) =="
  tail -n 40 "$API_LOG" 2>/dev/null || echo "No API log yet"
  echo "\n== Streamlit log (tail) =="
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

Examples:
  ./run_local_stack.sh start
  ./run_local_stack.sh status
  ./run_local_stack.sh logs
  ./run_local_stack.sh stop
EOF
}

case "${1:-}" in
  start) cmd_start ;;
  stop) cmd_stop ;;
  restart) cmd_restart ;;
  status) print_status ;;
  logs) cmd_logs ;;
  *) usage ; exit 1 ;;
esac
