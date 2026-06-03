#!/usr/bin/env bash
set -euo pipefail

# Local test/development launcher: starts only FastAPI, no ngrok.

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$APP_DIR/../../.." && pwd)"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-0}"

cd "$APP_DIR"

if [[ -x "$APP_DIR/.venv/bin/python" ]]; then
    PYTHON="$APP_DIR/.venv/bin/python"
elif [[ -x "$REPO_DIR/.venv/bin/python" ]]; then
    PYTHON="$REPO_DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

if ! "$PYTHON" -c "import fastapi, uvicorn, cv2, numpy, pydantic" >/dev/null 2>&1; then
    echo "Dipendenze mancanti. Installa con:"
    echo "  cd $REPO_DIR"
    echo "  python3 -m venv .venv"
    echo "  .venv/bin/python -m pip install -r src/tests/webapp_modular/requirements.txt"
    exit 1
fi

port_in_use() {
    (echo > "/dev/tcp/127.0.0.1/$1") >/dev/null 2>&1
}

if [[ "${AUTO_PORT:-1}" == "1" ]]; then
    while port_in_use "$PORT"; do
        PORT="$((PORT + 1))"
    done
elif port_in_use "$PORT"; then
    echo "La porta $PORT e' gia' occupata. Usa PORT=8001 ./run_local.sh oppure AUTO_PORT=1."
    exit 1
fi

echo "Map to GeoJSON Modular - local test"
echo "Apri http://$HOST:$PORT"

if [[ "$RELOAD" == "1" ]]; then
    exec "$PYTHON" -m uvicorn main:app --host "$HOST" --port "$PORT" --reload
else
    exec "$PYTHON" -m uvicorn main:app --host "$HOST" --port "$PORT"
fi
