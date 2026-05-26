#!/bin/bash

# Vai nella cartella del progetto
cd "$HOME/Map_to_Geojson-Converter/src/tests/webapp_modular" || exit

# Attiva virtual environment
source env/bin/activate

# Chiude eventuali processi vecchi
pkill -f "uvicorn main:app" 2>/dev/null
pkill -f "ngrok http 8000" 2>/dev/null

sleep 1

# Avvia FastAPI in background
nohup uvicorn main:app --host 127.0.0.1 --port 8000 > uvicorn.log 2>&1 &

# Aspetta che il server salga
sleep 4

# Verifica che FastAPI risponda
if ! curl -s http://127.0.0.1:8000 > /dev/null; then
    echo "Errore: FastAPI non risponde"
    echo "Controlla uvicorn.log"
    exit 1
fi

# Avvia ngrok in background
nohup ngrok http 8000 > ngrok.log 2>&1 &

# Aspetta ngrok
sleep 4

# Recupera URL pubblico
URL=$(curl -s http://127.0.0.1:4040/api/tunnels | grep -o 'https://[^"]*ngrok-free.app' | head -n 1)

echo ""
echo "=============================="
echo " SERVER PUBBLICO ATTIVO "
echo "=============================="
echo "URL:"
echo "$URL"
echo ""
echo "FASTAPI DOCS:"
echo "$URL/docs"
echo ""
echo "Chiudi SSH pure: resta attivo."