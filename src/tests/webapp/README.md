# 🗺️ Map to GeoJSON Web App

Applicazione web per convertire immagini di mappe in formato GeoJSON con editing interattivo delle regioni.

## 🎯 Funzionalità

- **Upload Immagini**: Supporto PNG, JPG, WebP (drag & drop)
- **Segmentazione Automatica**: K-Means color clustering
- **Modalità Click**: Aggiungi regioni cliccando sull'immagine
- **Georeferenziazione**: Preset per Italia, Europa, USA, ecc.
- **Anteprima Real-time**: Visualizza GeoJSON generato
- **Export**: Scarica file o copia negli appunti

## 🏗️ Struttura

```
webapp/
├── app.py              # Server FastAPI + logica segmentazione
├── requirements.txt    # Dipendenze Python
├── static/
│   ├── index.html     # Pagina principale
│   ├── styles.css     # Stili UI dark mode
│   └── app.js         # Logica frontend
├── CRITICAL_POINTS.md  # Punti critici e miglioramenti
└── README.md
```

## 🚀 Quick Start

```bash
cd webapp

# Crea ambiente virtuale
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Installa dipendenze
pip install -r requirements.txt

# Avvia server
python app.py
```

Apri **http://localhost:8000** nel browser.

## 📖 Come Usare

1. **Carica un'immagine** - Trascina o clicca "Carica Immagine"
2. **Regola parametri** - Numero colori e area minima
3. **Segmenta** - Clicca "Segmenta Automaticamente"
4. **Raffina** - Attiva "Modalità Click" per aggiungere regioni manualmente
5. **Georeferenzia** - Seleziona preset o inserisci coordinate personalizzate
6. **Esporta** - Scarica il GeoJSON

## 📖 Use Cases

1. **Infrastrutture Comunali** - Mappa reti fibra ottica, condutture
2. **Confini Amministrativi** - Digitalizza confini comunali/regionali
3. **Mappe Storiche** - Converti mappe antiche in GeoJSON
4. **Parchi e Aree Verdi** - Crea inventario aree pubbliche

## 🔧 API Endpoints

| Endpoint | Method | Descrizione |
|----------|--------|-------------|
| `/api/upload` | POST | Carica immagine |
| `/api/segment` | POST | Segmentazione automatica |
| `/api/segment-point` | POST | Aggiungi regione da click |
| `/api/delete-region/{id}` | POST | Elimina regione |
| `/api/export` | POST | Genera GeoJSON |
| `/api/presets` | GET | Preset geografici |

## ⚠️ Punti Critici & Miglioramenti

Vedi [CRITICAL_POINTS.md](./CRITICAL_POINTS.md) per dettagli.
