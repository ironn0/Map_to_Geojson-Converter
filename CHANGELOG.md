# Changelog

All notable changes to this project are documented in this file.  
Follow Semantic Versioning: https://semver.org

## [Unreleased]
- Added: planned support for additional input formats (CSV, KML).
- Improved: input validation and error messages.
- Fixed: minor issues with exporting multipart geometries.
- Documentation: usage examples and CLI options to be completed.

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