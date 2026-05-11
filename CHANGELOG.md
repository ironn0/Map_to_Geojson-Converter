# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Combined changelog for Map to GeoJSON Converter.

## [Unreleased]

### Added

- Added backend validation guards for geographic bounds and invalid/degenerate contours during export/alignment.
- Added quality baseline: `pytest` test suite, `ruff` lint configuration, `requirements-dev.txt`, unified `scripts/verify.py`, and GitHub Actions CI workflow.
- Added roadmap document for v1.0 milestones and acceptance criteria (`docs/ROADMAP_V1.md`).

### Changed

- Updated README and module docs to align run instructions and current repository structure (`webapp_modular` as primary app).
- Clarified georeferencing limitation: export supports axis-aligned bounds (rotation must be 0° when applying georef).

---

## [0.0.9](https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.9) (2026-02-13)

### 🎉 Features

- Complete webapp UI redesign with modern light theme and step-by-step workflow
- New sidebar layout with 4-step progress indicator (Upload → Segment → Georef → Export)
- Enhanced polygon editor toolbar with multiple tools: Select, Edit, Move, Scale
- Shape manipulation actions: Simplify (Douglas-Peucker), Smooth (Laplacian), Duplicate, Delete
- Right-click context menu for quick polygon actions
- Keyboard shortcuts for tools (V=Select, E=Edit, M=Move, S=Scale, Del=Delete, Ctrl+D=Duplicate)
- Added project icon (icon.svg) to webapp and README
- Favicon support for browser tab

### 🛠️ Fixes

- Removed cluttered regions sidebar list - now click directly on shapes to select
- Improved mouse interactions: single-click to select, double-click to edit vertices
- Fixed cursor states for different tools (pointer, move, crosshair, resize)
- Better visual feedback with toast notifications when changing tools

### 🎨 UI/UX

- New CSS variables system with light color palette
- Inter font family from Google Fonts
- Smooth animations and transitions
- Responsive panel design with collapsible sidebar
- Modern button styles with hover effects

### 📄 Documentation

- Updated README with centered icon and badges
- Fixed image URLs for examples (italy_input.png, italy_output.png)

---

## [0.0.8] (2025-12-06)

### 🎉 Features

- SAM (Segment Anything Model) integration with facebook/sam-vit-huge for automatic region segmentation
- Leaflet-based interactive map for drag-and-drop image georeferencing
- Territory selection interface - users can click to toggle territories on/off before export
- Bounds refinement feature - preview territories as green overlays and adjust bounds interactively
- Optimized SAM performance with 8 points_per_side (4x speed improvement)

### 🛠️ Fixes

- Download management - fixed duplicate file creation (bounds.json, selected_territories.json always overwrite)
- UI layout improvements - 2-column scrollable layout for better visibility of all controls
- Image preview integration with Leaflet georeferencing workflow

### 📄 Documentation

- Updated README.md with new SAM workflow and interactive features
- Added feature documentation for bounds refinement and territory selection

---

## [0.0.6](https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.6) (2025-11-28)

### 🎉 Features

- New Map Georeferencer tool with visual world map for geographic area selection
- Interactive checkbox system to include/exclude extracted regions before export
- Multiple test approaches for map-to-GeoJSON conversion (SVG parser, AI-assisted, shape matching)
- GADM Italy database integration for automatic region identification

### 🛠️ Fixes

- Improved region extraction accuracy with adjustable cluster count
- Better visual feedback for selected/deselected regions

### 📄 Documentation

- Updated feasibility study with revised technical approach and project timeline
- Added Gantt chart milestones and updated attachments section

---

## [0.0.5](https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.5) (2025-11-17)

### 🎉 Features

- Interactive region selection mode - users can manually approve/reject detected regions
- Higher precision contour detection with improved K-Means segmentation algorithm

### 🛠️ Fixes

- Missing region detection 
- Border precision and fidelity to original map boundaries

### ♻️ Chores

- Updated segmentation parameters (n_colors=60, min_area=300) for better region detection
- Improved contour simplification (epsilon=0.0002) for more accurate boundary representation
- Minimized color filtering system to reduce false positives while preserving all map regions

---

## [0.0.4](https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.4) (2025-11-14)

### 🎉 Features

- Visual examples in README and examples/ folder with Italy map input/output images
- Sample images (italy_input.png, italy_output.png) for GitHub preview

### 🛠️ Fixes

- Module installation issues for opencv-python, numpy, and shapely

### ♻️ Chores

- Python virtual environment support (.venv) with proper .gitignore configuration
- CONTRIBUTING.md with guidelines for contributions and development setup
- requirements.txt with project dependencies
- tests/ and examples/ folders structure

### 📄 Documentation

- examples/README.md with detailed visual demonstration of tool capabilities
- Updated README badge for GPL-3.0 license

---

## [0.0.3](https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.3) (2025-11-13)

### 🎉 Features

- Requirements gathering documents (Competitor_Analysis.md, Casual_Suggestions.md)

### ♻️ Chores

- Translated documentation files to English
- Improved project structure and organization

### 📄 Documentation

- Updated README.md

---

## [0.0.2](https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.2) (2025-11-11)

### 📄 Documentation

- Updated README.md with comprehensive project description
- Improved documentation links and references

---

## [0.0.1](https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.1) (2025-11-11)

### 🎉 Features

- Main conversion from GIS formats to GeoJSON (core CLI)
- Initial support for shapefile (.shp/.shx/.dbf) as input
- Option to specify output coordinate reference system (CRS)
- Saving GeoJSON output to file

### 🛠️ Fixes

- Handling of null attributes in input records

### ♻️ Chores

- .gitignore for Python project (ignores cache, venv, debug images)
- requirements.txt with project dependencies (opencv, numpy, shapely, etc.)
- CONTRIBUTING.md with guidelines for contributions and development setup
- examples/ folder with README for sample inputs/outputs
- tests/ folder with basic unit test for GeoJSON validity
- Improved project structure with better organization and documentation links

### 📄 Documentation

- README with installation instructions and usage examples
- Updated README.md to reflect student-focused project, free alternative to paid databases

---

### Notes

- Use the `main` branch for stable releases.
- Update the "Unreleased" section before publishing a new version.
- To report bugs or propose features, open an issue with a title and reproduction steps.