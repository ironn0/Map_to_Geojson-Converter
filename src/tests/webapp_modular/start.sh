#!/bin/bash

cd "$HOME/Map_to_Geojson-Converter/src/tests/webapp_modular" || exit

source env/bin/activate

# Chiude processi vecchi
pkill -f "uvicorn" 2>/dev/null
pkill -f "ngrok" 2>/dev/null

sleep 2

# Avvia FastAPI
nohup uvicorn main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 &

sleep 5

# Verifica FastAPI
curl -s http://127.0.0.1:8000 > /dev/null
if [ $? -ne 0 ]; then
    echo "Errore: FastAPI non parte"
    cat uvicorn.log
    exit 1
fi

# Avvia ngrok
nohup ngrok http 8000 > ngrok.log 2>&1 &

sleep 5

# Recupera URL pubblico (metodo robusto)
URL=$(curl -s http://127.0.0.1:4040/api/tunnels | sed -n 's/.*"public_url":"\(https:[^"]*\)".*/\1/p' | head -n 1)

echo ""
echo "=============================="
echo " SERVER PUBBLICO ATTIVO "
echo "=============================="

if [ -n "$URL" ]; then
    echo "URL:"
    echo "$URL"
    echo ""
    echo "FASTAPI DOCS:"
    echo "$URL/docs"
else
    echo "Ngrok è partito ma URL non trovato."
    echo "Prova:"
    echo "curl http://127.0.0.1:4040/api/tunnels"
fi

echo ""
echo "Chiudi SSH pure: resta attivo."