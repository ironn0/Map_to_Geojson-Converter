#!/usr/bin/env bash
set -euo pipefail

# Home-server launcher: starts FastAPI and exposes it with ngrok.
# For local tests/development use ./run_local.sh instead.

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$APP_DIR/.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
START_NGROK="${START_NGROK:-1}"
NGROK_DOMAIN="${NGROK_DOMAIN-cider-esquire-tinkling.ngrok-free.dev}"
NGROK_DOMAIN="${NGROK_DOMAIN#https://}"
NGROK_DOMAIN="${NGROK_DOMAIN#http://}"
NGROK_DOMAIN="${NGROK_DOMAIN%/}"
RUNTIME_DIR="$APP_DIR/.runtime"
LOG_DIR="$APP_DIR/logs"
UVICORN_PID="$RUNTIME_DIR/uvicorn.pid"

cd "$APP_DIR"
mkdir -p "$RUNTIME_DIR" "$LOG_DIR"

if [[ -x "$APP_DIR/.venv/bin/python" ]]; then
    PYTHON="$APP_DIR/.venv/bin/python"
elif [[ -x "$REPO_DIR/.venv/bin/python" ]]; then
    PYTHON="$REPO_DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

require_deps() {
    if ! "$PYTHON" -c "import fastapi, uvicorn, cv2, numpy, pydantic" >/dev/null 2>&1; then
        echo "Dipendenze mancanti. Installa con:"
        echo "  cd $REPO_DIR"
        echo "  python3 -m venv .venv"
        echo "  .venv/bin/python -m pip install -r src/requirements.txt"
        exit 1
    fi
    if [[ "$START_NGROK" == "1" ]] && ! command -v ngrok >/dev/null 2>&1; then
        echo "ngrok non trovato. Installa/configura ngrok sul server di casa prima di usare start.sh."
        exit 1
    fi
}

port_in_use() {
    (echo > "/dev/tcp/127.0.0.1/$PORT") >/dev/null 2>&1
}

http_ready() {
    "$PYTHON" - "$HOST" "$PORT" <<'PY' >/dev/null 2>&1
import sys
from urllib.request import urlopen

host, port = sys.argv[1], sys.argv[2]
url_host = "127.0.0.1" if host == "0.0.0.0" else host
with urlopen(f"http://{url_host}:{port}/", timeout=2) as response:
    if response.status != 200:
        raise SystemExit(1)
PY
}

stop_previous_uvicorn() {
    if [[ -f "$UVICORN_PID" ]]; then
        old_pid="$(cat "$UVICORN_PID")"
        if [[ -n "$old_pid" ]] && kill -0 "$old_pid" >/dev/null 2>&1; then
            echo "Fermo la vecchia istanza FastAPI avviata da start.sh (PID $old_pid)..."
            kill "$old_pid" >/dev/null 2>&1 || true
            sleep 1
        fi
        rm -f "$UVICORN_PID"
    fi
}

cleanup() {
    if [[ -f "$UVICORN_PID" ]]; then
        pid="$(cat "$UVICORN_PID")"
        if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
            kill "$pid" >/dev/null 2>&1 || true
        fi
        rm -f "$UVICORN_PID"
    fi
}

require_deps
stop_previous_uvicorn

if port_in_use; then
    echo "La porta $PORT e' gia' occupata da un altro processo."
    echo "Per test locali usa: PORT=8001 ./run_local.sh"
    echo "Per il server ngrok libera la porta o imposta PORT=<porta>."
    exit 1
fi

trap cleanup EXIT INT TERM

echo "Avvio FastAPI su http://$HOST:$PORT ..."
"$PYTHON" -m uvicorn main:app --host "$HOST" --port "$PORT" > "$LOG_DIR/uvicorn.log" 2>&1 &
echo "$!" > "$UVICORN_PID"

for _ in {1..30}; do
    if port_in_use && http_ready; then
        break
    fi
    if ! kill -0 "$(cat "$UVICORN_PID")" >/dev/null 2>&1; then
        echo "FastAPI non e' partito. Log:"
        cat "$LOG_DIR/uvicorn.log"
        exit 1
    fi
    sleep 0.5
done

if ! port_in_use || ! http_ready; then
    echo "FastAPI non risponde sulla porta $PORT. Log:"
    cat "$LOG_DIR/uvicorn.log"
    exit 1
fi

echo "FastAPI pronto."
if [[ "$START_NGROK" != "1" ]]; then
    echo "START_NGROK=0: tunnel ngrok disattivato."
    echo "Server disponibile su http://$HOST:$PORT"
    wait "$(cat "$UVICORN_PID")"
    exit 0
fi

echo "Avvio tunnel ngrok..."

if [[ -n "$NGROK_DOMAIN" ]]; then
    ngrok http --domain="$NGROK_DOMAIN" "http://$HOST:$PORT"
else
    ngrok http "http://$HOST:$PORT"
fi
