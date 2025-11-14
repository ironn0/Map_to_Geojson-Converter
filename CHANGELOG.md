# Changelog

All notable changes to this project are documented in this file.  
Follow Semantic Versioning: https://semver.org

## [Unreleased]
- Added: planned support for additional input formats (CSV, KML).
- Improved: input validation and error messages.
- Fixed: minor issues with exporting multipart geometries.
- Documentation: usage examples and CLI options to be completed.

## [0.0.2] - 2025-11-14
- Added: .gitignore for Python project (ignores cache, venv, debug images).
- Added: requirements.txt with project dependencies (opencv, numpy, shapely, etc.).
- Added: CONTRIBUTING.md with guidelines for contributions and development setup.
- Added: examples/ folder with README for sample inputs/outputs.
- Added: tests/ folder with basic unit test for GeoJSON validity.
- Updated: README.md to reflect student-focused project, free alternative to paid databases, with references to new files.
- Translated: Documentation files to English (Analisi_Concorrenza.md, Suggerimenti_Spontanei.md, pipeline.md).
- Improved: Project structure with better organization and documentation links.

## [0.0.1] - 2025-11-8
- Added: main conversion from GIS formats to GeoJSON (core CLI).
- Added: initial support for shapefile (.shp/.shx/.dbf) as input.
- Added: option to specify output coordinate reference system (CRS).
- Added: saving GeoJSON output to file or stdout.
- Added: basic integration tests and build scripts.
- Documentation: README with installation instructions and usage examples.
- Fixed: handling of null attributes in input records.

### Notes
- Use the `main` branch for stable releases.  
- Update the "Unreleased" section before publishing a new version.
- To report bugs or propose features, open an issue with a title and reproduction steps.