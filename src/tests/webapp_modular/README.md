# Map to GeoJSON - Modular Version

Versione modulare della webapp per digitalizzare mappe raster in GeoJSON. L'obiettivo e' essere piu' utile di un editor GeoJSON generico quando si parte da immagini: mappe tecniche, scansioni, aree di influenza, mappe storiche o tavole tematiche.

## Cosa Fa

- Carica immagini PNG, JPG o WebP fino a 25MB.
- Ridimensiona l'immagine di lavoro mantenendo coordinate canvas/export coerenti.
- Estrae aree colorate con segmentazione assistita.
- Permette di disegnare aree manuali sopra la mappa.
- Permette di modificare vertici, spostare, scalare, semplificare, arrotondare, duplicare, eliminare e rinominare aree.
- Permette di aggiungere punti di interesse, trascinarli, rinominarli ed esportarli.
- Esporta un GeoJSON che include esattamente aree e punti presenti nell'editor.

## 🗂️ Struttura del Progetto

```
webapp_modular/
├── __init__.py                 # Package init
├── config.py                   # Configurazione centralizzata
├── models.py                   # Modelli Pydantic e dataclass
├── utils.py                    # Utility functions
├── session_manager.py          # Gestione sessioni in memoria
├── main.py                     # Entry point FastAPI
│
├── segmentation/               # Modulo segmentazione
│   ├── __init__.py
│   └── segmenter.py           # MapSegmenter (K-Means, edge detection)
│
├── georeferencing/             # Modulo georeferenziazione
│   ├── __init__.py
│   ├── georeferencer.py       # Conversione coordinate
│   └── aligner.py             # Allineamento ai confini
│
├── routes/                     # Endpoint API
│   ├── __init__.py
│   ├── upload.py              # /api/upload
│   ├── segmentation.py        # /api/segment, /api/segment-point
│   ├── export.py              # /api/export
│   └── alignment.py           # /api/align
│
└── static/
    ├── index.html             # Template HTML
    │
    ├── css/                   # Stili modulari
    │   ├── base.css           # Reset, variabili, tipografia
    │   ├── layout.css         # Sidebar, canvas wrapper
    │   ├── components.css     # Button, input, form, cards
    │   ├── steps.css          # Multi-step wizard
    │   ├── upload.css         # Area upload
    │   ├── modal.css          # Modal dialog
    │   ├── editor.css         # SVG editor, toolbar
    │   └── utilities.css      # Loading, toast, helpers
    │
    └── js/                    # JavaScript modulare (ES6)
        ├── app.js             # Entry point principale
        ├── state.js           # Stato applicazione
        ├── dom.js             # Riferimenti DOM
        ├── api.js             # Chiamate API
        ├── ui.js              # Toast, loading, step
        ├── cookies.js         # Cookie manager GDPR
        ├── editor.js          # Editor poligoni
        ├── georef.js          # Georeferenziazione
        ├── export.js          # Export GeoJSON
        ├── drawing.js         # Disegno manuale
        └── rename.js          # Rinomina elementi
```

## 🚀 Avvio

```bash
# Dalla root del repository
python3 -m venv .venv
.venv/bin/python -m pip install -r src/tests/webapp_modular/requirements.txt
src/tests/webapp_modular/run_local.sh
```

Poi apri http://127.0.0.1:8000.

### Server di Casa con ngrok

`start.sh` e' riservato al server domestico/pubblico via ngrok:

```bash
cd src/tests/webapp_modular
./start.sh
```

Variabili utili:

```bash
PORT=8001 ./start.sh
NGROK_DOMAIN=cider-esquire-tinkling.ngrok-free.dev ./start.sh
```

Per test e sviluppo locale usa `run_local.sh`, che non avvia ngrok e sceglie automaticamente una porta libera.

## 📦 Moduli Backend

### config.py
Configurazione centralizzata: paths, presets geografici, CORS settings.

### models.py
- `GeoBounds`: Coordinate geografiche (Pydantic)
- `SegmentRequest`: Richiesta segmentazione
- `ExportRequest`: Richiesta export
- `AlignRequest`: Richiesta allineamento con regioni editate
- `ExtractedRegion`: Regione estratta (dataclass)

### segmentation/segmenter.py
Classe `MapSegmenter` per:
- Clustering K-Means dei colori
- Rilevamento bordi (Canny edge detection)
- Estrazione contorni (cv2.findContours)
- Approssimazione poligoni (Douglas-Peucker)

### georeferencing/georeferencer.py
Classe `GeoReferencer` per la conversione coordinate pixel → geo.

### georeferencing/aligner.py
Classe `TerritoryAligner` per allineare le regioni a confini reali.

### routes/
Endpoint FastAPI organizzati per funzionalità:
- `upload.py`: Caricamento immagini
- `segmentation.py`: Segmentazione automatica e manuale
- `export.py`: Export GeoJSON
- `alignment.py`: Allineamento ai confini

## 🎨 Moduli Frontend

### state.js
Stato centralizzato dell'applicazione (ES6 export).

### api.js
Wrapper per chiamate API fetch.

### ui.js
Funzioni UI: toast notifications, loading overlay, step navigation.

### editor.js
Editor SVG per modifica poligoni: selezione, modifica vertici, spostamento, scala.

### georef.js
Georeferenziazione interattiva con Leaflet.js.

### export.js
Generazione e download GeoJSON usando lo stato visibile nell'editor: aree automatiche, aree manuali e punti di interesse.

### drawing.js
Disegno manuale di poligoni e punti.

## 🎯 Vantaggi della Modularizzazione

1. **Manutenibilità**: Ogni modulo ha una responsabilità specifica
2. **Testing**: Moduli isolati più facili da testare
3. **Riutilizzo**: Componenti riutilizzabili in altri progetti
4. **Collaborazione**: Sviluppatori possono lavorare su moduli diversi
5. **Debug**: Più facile trovare e correggere bug
6. **Scalabilità**: Facile aggiungere nuove funzionalità

## 📋 Differenze dalla Versione Originale

| Aspetto | Originale | Modulare |
|---------|-----------|----------|
| Backend | 1 file (991 righe) | 15+ file specializzati |
| Frontend JS | 1 file (1948 righe) | 11 moduli ES6 |
| CSS | 1 file (1667 righe) | 8 file tematici |
| Import | Script globale | ES6 modules |
| Routing | In main file | Router separati |

## 🔧 Sviluppo

Per aggiungere una nuova funzionalità:

1. **Backend**: Crea un nuovo file in `routes/` o un nuovo modulo
2. **Frontend**: Aggiungi un modulo in `static/js/`
3. **CSS**: Estendi il file tematico appropriato o creane uno nuovo
4. **Import**: Aggiorna gli import in `main.py` e `app.js`

## Note

- Il JavaScript usa ES6 modules (`type="module"`)
- Il CSS usa variabili CSS per theming consistente
- Le API seguono convenzioni REST.
- La sessione e' gestita in memoria: per un deploy pubblico servono persistenza, autenticazione e limiti di utilizzo.
- La georeferenziazione usa una trasformazione lineare sui bounds nord/sud/est/ovest; per proiezioni complesse serve un passo GIS dedicato.
