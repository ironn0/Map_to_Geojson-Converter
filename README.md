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

<p align="center">
  A free, open-source tool to digitize map images (PNG, JPG, WebP) into editable, georeferenced GeoJSON using computer vision plus manual tracing.
</p>

---

## Table of Contents
- [Highlights](#highlights)
- [Web App](#web-app)
- [Background](#background)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Features](#features)
- [Algorithm Overview](#algorithm-overview)
- [Outputs](#outputs)
- [Limitations & Roadmap](#limitations--roadmap)
- [Contributing](#contributing)
- [Documentation](#documentation)
- [References](#references)

---

## Highlights
- 🆓 **Free & Open-Source**: No costs, ideal for students and researchers.
- **Web Interface**: Modern browser-based app with interactive georeferencing.
- 🎨 **Assisted Extraction**: Uses K-Means segmentation and edge detection for automatic polygon extraction.
- 🗺️ **Multiple Inputs**: Supports images (PNG, JPG, WebP) and SVG files.
- 📦 **GeoJSON Export**: Outputs standard GeoJSON FeatureCollection.
- 🔄 **Real-time Preview**: See your regions on a real map before exporting.

---

## Background
This project was created by students to provide free access to geospatial data. Commercial services charge money for databases, making them inaccessible for educational projects. The modular web app uses OpenCV and a browser editor to convert simple map images into usable GeoJSON files.

### 🎯 What It Does

Transform map images into GeoJSON automatically:

| Input Map | Output (Detected Regions) |
|-----------|---------------------------|
| ![Input](https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/italy_input.png) | ![Output](https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/italy_output.png) |

The tool extracts colored regions, identifies boundaries, and generates GeoJSON files ready for use in GIS applications.

---

## Web App

The modular web app is designed as a practical image-to-GeoJSON digitizing tool: upload a map, trace or auto-detect areas, edit vertices by hand, add points of interest, georeference the result, and export a GeoJSON that matches the visible edits.

| Input: Historical Map | Output: Georeferenced GeoJSON |
|----------------------|-------------------------------|
| ![Input](https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/img_raw_webapp.png) | ![Output](https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/img_result_geojson.png) |

### Key Features
- **Map image tracing**: Use scanned maps, technical drawings, thematic maps, or influence-area images as a digitizing base.
- **Assisted segmentation**: Extract colored regions with K-Means and refine them manually.
- **Manual editing**: Draw polygons, move/scale/simplify/smooth shapes, edit vertices, duplicate, delete, and rename areas.
- **Points of interest**: Add, drag, rename, delete, and export POIs together with areas.
- **Georeferenced export**: Export a GeoJSON FeatureCollection using the bounds you set in the app.

### Quick Start (Web App)
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r src/tests/webapp_modular/requirements.txt
src/tests/webapp_modular/run_local.sh
```
Open http://localhost:8000 in your browser.

For the home server/ngrok deployment use:

```bash
cd src/tests/webapp_modular
./start.sh
```

Default public URL: `https://cider-esquire-tinkling.ngrok-free.dev/`.

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

### One-Command Installation & Run (Windows)
```bash
# Clone the repository
git clone https://github.com/ironn0/Map_to_Geojson-Converter.git
cd Map_to_Geojson-Converter

# Create virtual environment, install deps, and run
python -m venv .venv && .venv\Scripts\activate && pip install -r src\tests\webapp_modular\requirements.txt && cd src\tests\webapp_modular && uvicorn main:app --reload
```

### Step-by-Step Installation
```bash
# 1. Clone the repository
git clone https://github.com/ironn0/Map_to_Geojson-Converter.git
cd Map_to_Geojson-Converter

# 2. Create virtual environment 
#Windows
python3 -m venv .venv
#Linux
 apt install python3.12-venv


# 3. Activate virtual environment
.venv\Scripts\Activate.ps1   # Windows (PowerShell)
.venv\Scripts\activate       # Windows (cmd.exe)
# Linux / macOS (bash, zsh)
source .venv/bin/activate
# Fish shell
source .venv/bin/activate.fish
# To deactivate the virtual environment
deactivate

# 4. Install dependencies
pip install -r src/tests/webapp_modular/requirements.txt

# 5. Run the web app
src/tests/webapp_modular/run_local.sh
```

Then open **http://localhost:8000** in your browser.

### Run CLI Scripts (Alternative)
```bash
# Image to GeoJSON command-line prototype
python "src/tests/test SAM/map_to_geojson.py"

# SVG to GeoJSON
python "src/test svg to geojson/Svg_to_Geojson_Converter.py"
```

---

## Usage
1. Prepare your map image or SVG file.
2. Run the appropriate script.
3. Choose calibration (Italy preset or manual).
4. Outputs: GeoJSON file with polygons and points of interest.

For detailed pipeline, see `src/test con ai/pipeline.md`.

---

## Features
- **Web Interface**: Modern, responsive UI with step-by-step workflow.
- **Image Conversion**: Extract polygons from map images using K-Means segmentation and edge detection.
- **SVG Support**: Convert SVG paths to GeoJSON.
- **Interactive Georeferencing**: Visual corner-dragging on Leaflet map for precise alignment.
- **Polygon Editor**: Select, edit vertices, move, scale, simplify, smooth, duplicate, delete, and rename regions.
- **Manual Drawing**: Add custom polygons and draggable points of interest directly.
- **Consistent Export**: Manual edits and POIs are included in the exported GeoJSON.
- **Geographic Bounds**: Use presets or custom north/south/east/west bounds.

---

## Algorithm Overview
- **Preprocessing**: Image resizing for consistent canvas/export coordinates.
- **Segmentation**: K-Means color clustering plus edge detection.
- **Contour Detection**: Use OpenCV to find shapes.
- **Filtering**: Remove noise, water, etc., based on heuristics.
- **Georeferencing**: Map pixels to coordinates.
- **Export**: Generate GeoJSON with properties (id, color, area).

See `src/test con ai/pipeline.md` for full architecture.

---

## Outputs
- **GeoJSON File**: FeatureCollection with polygons and points of interest.
- **Properties**: Feature name, type, color, id, pixel area when available, bounds metadata.
- Visualize at https://geojson.io.

---

## Limitations & Roadmap
- Works best on maps with distinct colored regions.
- Complex historical maps may need manual polygon editing.
- ✅ ~~Web interface~~ - **Completed!**
- Future: Batch processing, AI-assisted labeling, territory alignment with official borders.

See `docs/feasibility/StudioDiFattibilità.md` for detailed feasibility study.

---

## Contributing
We welcome contributions! Open issues or PRs. Focus areas:
- Improve AI segmentation.
- Add more input formats.
- Enhance georeferencing.

For requirements gathering, see `docs/feasibility/requirements/`.

---

## Documentation
- **Web App**: `src/tests/webapp/README.md`
- **Modular Version**: `src/tests/webapp_modular/README.md`
- **Feasibility Study**: `docs/feasibility/README.md`
- **Requirements**: `docs/feasibility/requirements/`
- **Contributing**: `CONTRIBUTING.md`
- **Examples**: `examples/`
- **Changelog**: `CHANGELOG.md`

---

## References
- **Web App**: `src/tests/webapp/` - Full-featured browser interface
- **Modular Version**: `src/tests/webapp_modular/` - Refactored codebase
- **CLI Tools**: `src/tests/test SAM/` - Command-line scripts
- Inspired by open-source GIS tools like QGIS and GDAL.
- For feedback, open GitHub Issues or Discussions.

---
