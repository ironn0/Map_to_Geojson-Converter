# Map to GeoJSON Converter

Convert scanned maps and raster images into valid GeoJSON, with assisted georeferencing and export guardrails designed to work cleanly in tools like geojson.io.

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
- [Project Management Workflow](#project-management-workflow)
- [Contributing](#contributing)
- [Documentation](#documentation)
- [References](#references)

---

## Highlights

- 🆓 **Free & Open-Source**: No costs, ideal for students and researchers.
- 🌐 **Web Interface**: Modern browser-based app with interactive georeferencing.
- 🎨 **AI-Powered**: Uses K-Means segmentation with optional robust preprocessing for noisy/historical maps.
- 🗺️ **Multiple Inputs**: Supports images (PNG, JPG, WebP) and SVG files.
- 📦 **GeoJSON Export**: Outputs standard GeoJSON FeatureCollection with optional geometry sanitization.
- 🔄 **Real-time Preview**: See your regions on a real map before exporting.

### Why teams use this project

- Handles difficult map inputs (historical scans, noisy borders, skewed pages) with robust segmentation options.
- Provides guided georeferencing, including optional CV-assisted registration (`cv_auto`) with fallback metadata.
- Includes circle detection + georeferencing workflow when the map uses circular boundaries.
- Enforces export validity with coordinate normalization and JSON numeric sanitization.
- Ships with automated quality gates (`pytest` + benchmark thresholds) to reduce regressions.

---

## Background

This project was created by students to provide free access to geospatial data. Commercial services charge money for databases, making them inaccessible for educational projects. Our tool leverages open-source libraries (OpenCV, GDAL, PyTorch) to convert simple map images into usable GeoJSON files.

### 🎯 What It Does

Transform map images into GeoJSON automatically:


| Input Map | Output (Detected Regions) |
| --------- | ------------------------- |
| Input     | Output                    |


The tool extracts colored regions, identifies boundaries, and generates GeoJSON files ready for use in GIS applications.

---

## 🌐 Web App (New!)

The latest version includes a **full-featured web interface** for easy map conversion:


| Input: Historical Map | Output: Georeferenced GeoJSON |
| --------------------- | ----------------------------- |
| Input                 | Output                        |


### Key Features

- 🖼️ **Drag & Drop Upload**: Simply drop your map image
- 🎯 **Interactive Segmentation**: Adjust colors and sensitivity in real-time
- 🗺️ **Visual Georeferencing**: Drag corners on a real map to align your image
- 📍 **Advanced Georeferencing (opt-in)**: GCP affine/homography + CV semi-automatic registration (`cv_auto`) with confidence/fallback
- ✏️ **Polygon Editor**: Edit, merge, split, and rename regions
- 💾 **One-Click Export**: Download GeoJSON ready for GIS software

### Quick Demo Flow

1. Upload map image
2. Run segmentation (or click-to-add regions)
3. Georeference (manual bounds or `cv_auto`)
4. Optional: detect and export circle-only geometry
5. Export GeoJSON and open in geojson.io

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

Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## Quick Start

### Prerequisites

- Python 3.8+ ([Download](https://www.python.org/downloads/))

### Required Libraries


| Library            | Purpose                         |
| ------------------ | ------------------------------- |
| `fastapi`          | Web framework for the app       |
| `uvicorn`          | ASGI server to run the app      |
| `opencv-python`    | Image processing & segmentation |
| `numpy`            | Array operations                |
| `Pillow`           | Image loading                   |
| `shapely`          | Polygon operations              |
| `pydantic`         | Data validation                 |
| `python-multipart` | File upload handling            |


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

Then open **[http://localhost:8000](http://localhost:8000)** in your browser.

### Trust & Quality Checks

Run the full verification pipeline before releases:

```bash
python scripts/verify.py
```

This runs lint, test suite, and benchmark thresholds.

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
- **Guided Wizard UX**: Recommended next action, project history timeline, and clearer quality feedback for non-technical users.
- **Image Conversion**: Extract polygons from map images using legacy or robust segmentation profiles.
- **SVG Support**: Convert SVG paths to GeoJSON.
- **Interactive Georeferencing**: Bounds-based conversion by default, optional GCP affine/homography, and opt-in `cv_auto` with confidence checks.
- **Polygon Editor**: Select, edit vertices, merge, split, duplicate, rename regions.
- **Manual Drawing**: Add custom polygons and points directly.
- **Real-time Preview**: See regions on actual geographic map before export.
- **Debug Visuals**: Segmented and region overlay images.
- **Benchmark Harness**: KPI-based benchmark checks for precision/recall, spatial error, runtime, and legacy vs `cv_auto` georeferencing delta.
- **State Consistency**: Geometry edits are synchronized to backend before export to avoid UI/output mismatch.
- **Operational Reliability Scaffolding**: Background job queue with retry/timeout, job status API, and operational error dashboard endpoints.
- **GeoJSON Validity Guardrails**: Coordinate clamping and JSON numeric sanitization to prevent invalid lat/lon payloads.

---

## Algorithm Overview

- **Preprocessing**: Legacy path (K-Means + edges) or robust path (denoise + CLAHE + adaptive threshold + text suppression + contour hardening controls).
- **Contour Detection**: Use OpenCV to find shapes.
- **Filtering**: Remove noise, water, etc., based on heuristics.
- **Georeferencing**: Bounds-based linear conversion, optional GCP affine/homography, or opt-in CV registration (`cv_auto`) against a georeferenced raster.
- **Session Safety**: In-memory sessions use TTL-based cleanup to reduce stale state and temp file accumulation.
- **Export**: Generate GeoJSON with optional validation/sanitization (invalid rings, self-intersections, multipolygons, simplification).

See `src/tests/webapp_modular/README.md` for module-level architecture.

---

## Compatibility & Fallback Behavior

- **Legacy default remains unchanged**: if you do not send `georeferencing`, export/alignment still use bounds-based mapping.
- **`cv_auto` is opt-in**: enabled only when `georeferencing.mode = cv_auto` with reference raster + reference bounds.
- **Safety fallback**: if CV registration quality is low (or registration fails), backend automatically falls back to bounds when `allow_fallback=true`.
- **Traceable metrics**: responses include georeferencing metadata (`mode`, `cv_confidence`, inlier stats, fallback reason) in GeoJSON `properties`.

---

## Outputs

- **GeoJSON File**: FeatureCollection with polygons.
- **Debug Images**: `_segmented.png` (clusters), `_regions.png` (polygons).
- Visualize at [https://geojson.io](https://geojson.io).
- Export payload includes quality metadata (`georeferencing`, `geometry_sanitize`, `circle_only_mode`) for easier triage.

---

## Limitations & Roadmap

- Works best on maps with distinct colored regions.
- Complex historical maps may need manual polygon editing.
- ✅ ~~Web interface~~ - **Completed!**
- Next focus: stronger georeferencing UX, production auth/billing persistence, and larger benchmark datasets.

See `docs/feasibility/README.md` for the feasibility study.

---

## Contributing

We welcome contributions! Open issues or PRs. Focus areas:

- Improve AI segmentation.
- Add more input formats.
- Enhance georeferencing.

For requirements gathering, see `docs/feasibility/requirements/`.

Use the repository PM workflow defined in `docs/PROJECT _MANAGEMENT/GITHUB_PROJECTS_WORKFLOW.md`:

- Open issues using the provided templates and required labels.
- Assign each issue to roadmap milestones M1-M4.
- Link PRs to issues and move work across board states.

Local release checks:

```bash
python scripts/verify.py
```

---

## Project Management Workflow

The project uses a GitHub Projects-centered workflow for planning and delivery:

- Board columns: `Backlog`, `Ready`, `In Progress`, `In Review`, `Done`.
- Required labels: `type:`*, `area:*`, `prio:*`, plus `ready` when refined.
- Milestone alignment: `M1 Core Reliability` to `M4 v1 Product Readiness`.

Bootstrap labels/milestones quickly:

```bash
python scripts/bootstrap_github_pm.py
```

Full process guide: `docs/PROJECT _MANAGEMENT/GITHUB_PROJECTS_WORKFLOW.md`.

---

## Documentation

- **Web App (current)**: `src/tests/webapp_modular/README.md`
- **Web App (legacy)**: `src/tests/webapp/README.md`
- **Feasibility Study**: `docs/feasibility/README.md`
- **Requirements**: `docs/feasibility/requirements/`
- **v1.0 Roadmap**: `docs/ROADMAP_V1.md`
- **PM Workflow Guide**: `docs/PROJECT _MANAGEMENT/GITHUB_PROJECTS_WORKFLOW.md`
- **PM Foundation Doc**: `docs/PROJECT _MANAGEMENT/README.md`
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

