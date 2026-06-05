# Map2Geo Source

Questa cartella contiene la beta finale dell'applicazione.

## Componenti

- `main.py`: applicazione FastAPI e mount dei file statici.
- `config.py`: configurazione, preset geografici e directory.
- `models.py`: modelli Pydantic/dataclass.
- `session_manager.py`: sessioni temporanee in memoria.
- `routes/`: endpoint upload, segmentazione, export e allineamento.
- `segmentation/`: estrazione regioni da immagini raster.
- `georeferencing/`: conversione pixel/coordinate e allineamento.
- `static/`: frontend HTML/CSS/JS.
- `start.sh`: avvio server con ngrok.
- `run_local.sh`: avvio locale senza ngrok.
- `test_smoke.py`: test end-to-end essenziali.

## Avvio

Da root repository:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r src/requirements.txt
src/run_local.sh
```

Server con ngrok:

```bash
./start.sh
```
