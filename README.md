<p align="center">
  <img src="https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/icon.svg" alt="Map to GeoJSON Converter" width="200"/>
</p>

<h1 align="center">Map to GeoJSON Converter</h1>

<p align="center">
  <a href="https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.9"><img src="https://img.shields.io/badge/version-0.0.9-blue" alt="Version"/></a>
  <a href="https://github.com/ironn0/Map_to_Geojson-Converter"><img src="https://img.shields.io/badge/status-beta-green" alt="Status"/></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.8%2B-blue" alt="Python"/></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-blue" alt="License"/></a>
</p>

<p align="center">
  A free, open-source tool to convert map images (PNG, JPG) and SVG files into GeoJSON format, using AI and computer vision. Born as an alternative to expensive databases like Geochron (500€), enabling accessible geospatial data creation.
</p>

---

## Table of Contents
- [Highlights](#highlights)
- [Web App (New!)](#-web-app-new)
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
- � **Web Interface**: Modern browser-based app with interactive georeferencing.
- 🎨 **AI-Powered**: Uses K-Means segmentation and edge detection for automatic polygon extraction.
- 🗺️ **Multiple Inputs**: Supports images (PNG, JPG, WebP) and SVG files.
- 📦 **GeoJSON Export**: Outputs standard GeoJSON FeatureCollection.
- 🔄 **Real-time Preview**: See your regions on a real map before exporting.

---

## Background
This project was created by students to provide free access to geospatial data. Commercial services charge money for databases, making them inaccessible for educational projects. Our tool leverages open-source libraries (OpenCV, GDAL, PyTorch) to convert simple map images into usable GeoJSON files.

### 🎯 What It Does

Transform map images into GeoJSON automatically:

| Input Map | Output (Detected Regions) |
|-----------|---------------------------|
| ![Input](https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/italy_input.png) | ![Output](https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/italy_output.png) |

The tool extracts colored regions, identifies boundaries, and generates GeoJSON files ready for use in GIS applications.

---

## 🌐 Web App (New!)

The latest version includes a **full-featured web interface** for easy map conversion:

| Input: Historical Map | Output: Georeferenced GeoJSON |
|----------------------|-------------------------------|
| ![Input](https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/img_raw_webapp.png) | ![Output](https://raw.githubusercontent.com/ironn0/ironn0/main/assets/Map_to_Geojson/img_result_geojson.png) |

### Key Features
- 🖼️ **Drag & Drop Upload**: Simply drop your map image
- 🎯 **Interactive Segmentation**: Adjust colors and sensitivity in real-time
- 🗺️ **Visual Georeferencing**: Drag corners on a real map to align your image
- ✏️ **Polygon Editor**: Edit, merge, split, and rename regions
- 💾 **One-Click Export**: Download GeoJSON ready for GIS software

### Repository Layout (Current)
- `src/tests/webapp_modular/` → main FastAPI web application (actively maintained)
- `src/tests/webapp/` → legacy monolithic web app (reference only)
- `src/tests/test SAM/` → experimental CLI/SAM scripts
- `docs/` → feasibility, project management, and policy docs

### Quick Start (Web App)
```bash
pip install -r requirements.txt
cd src/tests/webapp_modular
uvicorn main:app --reload
```
Open http://localhost:8000 in your browser.

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
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt && cd src/tests/webapp_modular && uvicorn main:app --reload
```

### Step-by-Step Installation
```bash
# 1. Clone the repository
git clone https://github.com/ironn0/Map_to_Geojson-Converter.git
cd Map_to_Geojson-Converter

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the web app
cd src/tests/webapp_modular
uvicorn main:app --reload
```

Then open **http://localhost:8000** in your browser.

### Run CLI Scripts (Alternative)
```bash
# Image to GeoJSON with AI
python "src/tests/test SAM/map_to_geojson.py"
```

---

## Usage
1. Prepare your map image or SVG file.
2. Run the appropriate script.
3. Choose calibration (Italy preset or manual).
4. Outputs: GeoJSON file and debug images.

For implementation details, see `src/tests/webapp_modular/README.md`.

---

## Features
- **Web Interface**: Modern, responsive UI with step-by-step workflow.
- **Image Conversion**: Extract polygons from map images using K-Means segmentation and edge detection.
- **SVG Support**: Convert SVG paths to GeoJSON.
- **Interactive Georeferencing**: Visual corner-dragging on Leaflet map for precise alignment.
- **Polygon Editor**: Select, edit vertices, merge, split, duplicate, rename regions.
- **Manual Drawing**: Add custom polygons and points directly.
- **Real-time Preview**: See regions on actual geographic map before export.
- **Debug Visuals**: Segmented and region overlay images.

---

## Algorithm Overview
- **Preprocessing**: Image segmentation with K-Means or AI models.
- **Contour Detection**: Use OpenCV to find shapes.
- **Filtering**: Remove noise, water, etc., based on heuristics.
- **Georeferencing**: Map pixels to coordinates.
- **Export**: Generate GeoJSON with properties (id, color, area).

See `src/tests/webapp_modular/README.md` for module-level architecture.

---

## Outputs
- **GeoJSON File**: FeatureCollection with polygons.
- **Debug Images**: `_segmented.png` (clusters), `_regions.png` (polygons).
- Visualize at https://geojson.io.

---

## Limitations & Roadmap
- Works best on maps with distinct colored regions.
- Complex historical maps may need manual polygon editing.
- ✅ ~~Web interface~~ - **Completed!**
- Future: Batch processing, AI-assisted labeling, territory alignment with official borders.

See `docs/feasibility/README.md` for the feasibility study.

---

## Contributing
We welcome contributions! Open issues or PRs. Focus areas:
- Improve AI segmentation.
- Add more input formats.
- Enhance georeferencing.

For requirements gathering, see `docs/feasibility/requirements/`.

---

## Documentation
- **Web App (current)**: `src/tests/webapp_modular/README.md`
- **Web App (legacy)**: `src/tests/webapp/README.md`
- **Feasibility Study**: `docs/feasibility/README.md`
- **Requirements**: `docs/feasibility/requirements/`
- **v1.0 Roadmap**: `docs/ROADMAP_V1.md`
- **Contributing**: `CONTRIBUTING.md`
- **Examples**: `examples/`
- **Changelog**: `CHANGELOG.md`

---

## References
- **Web App (current)**: `src/tests/webapp_modular/` - modular FastAPI app + static frontend
- **Web App (legacy)**: `src/tests/webapp/` - previous monolithic implementation
- **CLI Tools / Experiments**: `src/tests/test SAM/` - command-line and prototype scripts
- Inspired by open-source GIS tools like QGIS and GDAL.
- For feedback, open GitHub Issues or Discussions.

---