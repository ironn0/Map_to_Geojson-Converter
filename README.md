# Map to GeoJSON Converter
[![Status](https://img.shields.io/badge/status-prototype-orange)](https://github.com/)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-GPL--3.0-blue)](LICENSE)

A free, open-source tool to convert map images (PNG, JPG) and SVG files into GeoJSON format, using AI and computer vision. Born as an alternative to expensive databases like Geochron (500€), enabling accessible geospatial data creation.

---

## Table of Contents
- [Highlights](#highlights)
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
- 🎨 **AI-Powered**: Uses segmentation and contour detection for automatic polygon extraction.
- 🗺️ **Multiple Inputs**: Supports images (PNG, JPG) and SVG files.
- 📦 **GeoJSON Export**: Outputs standard GeoJSON FeatureCollection.
- 🔬 **Prototype**: Extensible for research and education.

---

## Background
This project was created by students to provide free access to geospatial data. Commercial services like Geochron charge 500€ for databases, making them inaccessible for educational projects. Our tool leverages open-source libraries (OpenCV, GDAL, PyTorch) to convert simple map images into usable GeoJSON files.

### 🎯 What It Does

Transform map images into GeoJSON automatically:

| Input Map | Output (Detected Regions) |
|-----------|---------------------------|
| ![Input](examples/italy_input.png) | ![Output](examples/italy_output.png) |

The tool extracts colored regions, identifies boundaries, and generates GeoJSON files ready for use in GIS applications.

---

## Quick Start
### Prerequisites
- Python 3.8+
- Libraries: OpenCV, NumPy, Shapely, PyTorch (optional for AI)

### Installation
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Run
```bash
# Image to GeoJSON with AI
python "src/test con ai/image_to_geojson_auto.py"

# SVG to GeoJSON
python "src/test svg to geojson/Svg_to_Geojson_Converter.py"
```

---

## Usage
1. Prepare your map image or SVG file.
2. Run the appropriate script.
3. Choose calibration (Italy preset or manual).
4. Outputs: GeoJSON file and debug images.

For detailed pipeline, see `src/test con ai/pipeline.md`.

---

## Features
- **Image Conversion**: Extract polygons from map images using K-Means segmentation and contour detection.
- **SVG Support**: Convert SVG paths to GeoJSON.
- **Georeferencing**: Optional pixel-to-lat/lon calibration.
- **AI Integration**: Prototype with deep learning for better segmentation.
- **Debug Visuals**: Segmented and region overlay images.

---

## Algorithm Overview
- **Preprocessing**: Image segmentation with K-Means or AI models.
- **Contour Detection**: Use OpenCV to find shapes.
- **Filtering**: Remove noise, water, etc., based on heuristics.
- **Georeferencing**: Map pixels to coordinates.
- **Export**: Generate GeoJSON with properties (id, color, area).

See `src/test con ai/pipeline.md` for full architecture.

---

## Outputs
- **GeoJSON File**: FeatureCollection with polygons.
- **Debug Images**: `_segmented.png` (clusters), `_regions.png` (polygons).
- Visualize at https://geojson.io.

---

## Limitations & Roadmap
- Works best on simple maps; complex ones may need manual tweaks.
- Linear calibration; advanced georeferencing planned.
- Future: Web interface, batch processing, better AI models.

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
- **Feasibility Study**: `docs/feasibility/StudioDiFattibilità.md`
- **Requirements**: `docs/feasibility/requirements/Analisi_Concorrenza.md`, `Suggerimenti_Spontanei.md`
- **Pipeline**: `src/test con ai/pipeline.md`
- **Contributing**: `CONTRIBUTING.md`
- **Examples**: `examples/`
- **Tests**: `tests/`
- **Changelog**: `CHANGELOG.md`

---

## References
- Scripts: `src/test con ai/`, `src/test svg to geojson/`
- Inspired by open-source GIS tools like QGIS and GDAL.
- For feedback, open GitHub Discussions.

---