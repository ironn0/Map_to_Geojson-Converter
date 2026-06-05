<p align="center">
	<img src="docs/icon.svg" alt="Map to GeoJSON Converter" width="200"/>
</p>

<h1 align="center">Map to GeoJSON Converter</h1>

<p align="center">
	<a href="https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.1.3"><img src="https://img.shields.io/badge/version-0.1.3-blue" alt="Version"/></a>
	<a href="https://github.com/ironn0/Map_to_Geojson-Converter"><img src="https://img.shields.io/badge/status-beta-green" alt="Status"/></a>
	<a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python"/></a>
	<a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-blue" alt="License"/></a>
</p>

Web editor to convert raster maps to GeoJSON: upload an image, segment or draw regions, refine boundaries, georeference on a map and download a `FeatureCollection`.

---

## Table of Contents
- [Highlights](#highlights)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Features](#features)
- [Project Structure](#project-structure)
- [Local Startup](#local-startup)
- [Server Startup](#server-startup)
- [Test](#test)
- [Contributing](#contributing)

---

## Highlights
- 🆓 **Free & Open-Source**: No costs, ideal for students and researchers.
- **Web Interface**: Modern browser-based app with interactive georeferencing.
- 🎨 **Assisted Extraction**: Uses K-Means segmentation and edge detection for automatic polygon extraction.
- 🗺️ **Multiple Inputs**: Supports images (PNG, JPG, WebP) and SVG files.
- 📦 **GeoJSON Export**: Outputs standard GeoJSON FeatureCollection.

---

## Quick Start

### Prerequisites
- Python 3.8+ ([Download](https://www.python.org/downloads/))

### Required Libraries
| Library | Purpose |
|---------|---------|
| `fastapi` | Web framework for the app |
| `uvicorn` | ASGI server to run the app |
| `opencv-python` | Image processing & segmentation |
| `numpy` | Array operations |
| `Pillow` | Image loading |
| `shapely` | Polygon operations |
| `pydantic` | Data validation |
| `python-multipart` | File upload handling |

### One-Command (Linux/Mac)
```bash
# create venv, install deps and run local server
python3 -m venv .venv
.venv/bin/python -m pip install -r src/requirements.txt
./src/run_local.sh
```

Then open `http://127.0.0.1:8000` in your browser. If the port is busy, `run_local.sh` will choose the next available port.

---

## Local Startup

Use the local script to develop and test the app:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r src/requirements.txt
./src/run_local.sh
```

---

## Server Startup

`start.sh` is designed to expose the server using `ngrok` (optional):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r src/requirements.txt
./start.sh
```

Useful environment variables:

```bash
PORT=8001 ./start.sh
NGROK_DOMAIN=cider-esquire-tinkling.ngrok-free.dev ./start.sh
NGROK_DOMAIN= ./start.sh          # use a random ngrok URL
START_NGROK=0 ./start.sh          # only FastAPI, no tunnel
```

A public tunnel requires `ngrok` installed and configured on the host.

---

## Usage
1. Prepare your map image or SVG file.
2. Run the appropriate script (see Quick Start).
3. Choose calibration (preset or manual).
4. Export GeoJSON: FeatureCollection with polygons and points of interest.

For the detailed pipeline, see `src/test con ai/pipeline.md`.

---

## Features
- **Map image tracing**: usa scansioni, disegni tecnici o mappe tematiche come base.
- **Assisted segmentation**: estrazione delle regioni colorate con tecniche di clustering.
- **Manual editing**: modifica vertici, duplica, elimina e rinomina aree.
- **POI**: aggiungi, trascina, rinomina ed esporta punti di interesse.
- **Georeferenced export**: esporta GeoJSON georeferenziato con i bounds impostati.
 - **Map image tracing**: use scans, technical drawings, or thematic maps as a digitizing base.
 - **Assisted segmentation**: extract colored regions using clustering techniques.
 - **Manual editing**: edit vertices, duplicate, delete, and rename areas.
 - **POI**: add, drag, rename, and export points of interest.
 - **Georeferenced export**: export georeferenced GeoJSON using the set bounds.

---

## Project Structure

The beta lives in `src/`:

- `src/main.py`: FastAPI entrypoint
- `src/start.sh`: server launcher with ngrok
- `src/run_local.sh`: local launcher
- `src/static/`: web UI
- `src/routes/`: API endpoints
- `src/segmentation/`: raster segmentation
- `src/georeferencing/`: coordinate conversion and alignment
- `src/test_smoke.py`: final smoke test

---

## Test

```bash
.venv/bin/python -m pytest src/test_smoke.py -q
```

---

## Contributing
Contributions welcome: open issues or PRs. Focus areas: improve segmentation, add input formats, enhance georeferencing.

---

## References
- Visualize GeoJSON at https://geojson.io
- See `docs/feasibility/` for feasibility studies and requirements.

---

© Map to GeoJSON Converter Project
