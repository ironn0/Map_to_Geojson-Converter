#!/bin/bash

cd "$HOME/Map_to_Geojson-Converter/src/tests/webapp_modular" || exit

source env/bin/activate

# Chiude processi vecchi
echo "Spegnimento vecchi processi..."
pkill -f "uvicorn" 2>/dev/null
pkill -f "ngrok" 2>/dev/null

sleep 2

# Avvia FastAPI
echo "Avvio FastAPI..."
nohup uvicorn main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 &

sleep 5

# Verifica FastAPI
curl -s http://127.0.0.1:8000 > /dev/null
if [ $? -ne 0 ]; then
    echo "Errore: FastAPI non parte"
    cat uvicorn.log
    exit 1