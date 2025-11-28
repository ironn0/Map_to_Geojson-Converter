# Changelog

Combined changelog for Map to GeoJSON Converter.

## [Unreleased && TODO]

- Improved: input validation and error messages.
- Fixed: minor issues with exporting multipart geometries.
- Documentation: usage examples and CLI options to be completed.

---

## [0.0.6](https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.6) (2025-11-28)

### 🎉 Features

* New Map Georeferencer tool with visual world map for geographic area selection
* Interactive checkbox system to include/exclude extracted regions before export
* Multiple test approaches for map-to-GeoJSON conversion (SVG parser, AI-assisted, shape matching)
* GADM Italy database integration for automatic region identification

### 🛠️ Fixes

* Improved region extraction accuracy with adjustable cluster count
* Better visual feedback for selected/deselected regions

### 📄 Documentation

* Updated feasibility study with revised technical approach and project timeline
* Added Gantt chart milestones and updated attachments section

---

## [0.0.5](https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.5) (2025-11-17)

### 🎉 Features

* Interactive region selection mode - users can manually approve/reject detected regions
* Higher precision contour detection with improved K-Means segmentation algorithm

### 🛠️ Fixes

* Missing region detection 
* Border precision and fidelity to original map boundaries

### ♻️ Chores

* Updated segmentation parameters (n_colors=60, min_area=300) for better region detection
* Improved contour simplification (epsilon=0.0002) for more accurate boundary representation
* Minimized color filtering system to reduce false positives while preserving all map regions

---

## [0.0.4](https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.4) (2025-11-14)

### 🎉 Features

* Visual examples in README and examples/ folder with Italy map input/output images
* Sample images (italy_input.png, italy_output.png) for GitHub preview

### 🛠️ Fixes

* Module installation issues for opencv-python, numpy, and shapely

### ♻️ Chores

* Python virtual environment support (.venv) with proper .gitignore configuration
* CONTRIBUTING.md with guidelines for contributions and development setup
* requirements.txt with project dependencies
* tests/ and examples/ folders structure

### 📄 Documentation

* examples/README.md with detailed visual demonstration of tool capabilities
* Updated README badge for GPL-3.0 license

---

## [0.0.3](https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.3) (2025-11-13)

### 🎉 Features

* Requirements gathering documents (Competitor_Analysis.md, Casual_Suggestions.md)

### ♻️ Chores

* Translated documentation files to English
* Improved project structure and organization

### 📄 Documentation

* Updated README.md

---

## [0.0.2](https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.2) (2025-11-11)

### 📄 Documentation

* Updated README.md with comprehensive project description
* Improved documentation links and references

---

## [0.0.1](https://github.com/ironn0/Map_to_Geojson-Converter/releases/tag/v0.0.1) (2025-11-11)

### 🎉 Features

* Main conversion from GIS formats to GeoJSON (core CLI)
* Initial support for shapefile (.shp/.shx/.dbf) as input
* Option to specify output coordinate reference system (CRS)
* Saving GeoJSON output to file 

### 🛠️ Fixes

* Handling of null attributes in input records

### ♻️ Chores

* .gitignore for Python project (ignores cache, venv, debug images)
* requirements.txt with project dependencies (opencv, numpy, shapely, etc.)
* CONTRIBUTING.md with guidelines for contributions and development setup
* examples/ folder with README for sample inputs/outputs
* tests/ folder with basic unit test for GeoJSON validity
* Improved project structure with better organization and documentation links

### 📄 Documentation

* README with installation instructions and usage examples
* Updated README.md to reflect student-focused project, free alternative to paid databases

---

### Notes

* Use the `main` branch for stable releases.
* Update the "Unreleased" section before publishing a new version.
* To report bugs or propose features, open an issue with a title and reproduction steps.