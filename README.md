# Map to GeoJSON Converter
[![Status](https://img.shields.io/badge/status-prototype-orange)](https://github.com/)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-UNKNOWN-lightgrey)](LICENSE)

A lightweight prototype to extract polygons from map images and export them as GeoJSON — ideal for quick inspection, prototyping and research.

---

## Table of Contents
- [Highlights](#highlights)
- [Quick Start](#quick-start)
- [Usage (interactive)](#usage-interactive)
- [CLI / Automation hint](#cli--automation-hint)
- [Algorithm (overview)](#algorithm-overview)
- [Calibration & Projection](#calibration--projection)
- [Outputs](#outputs)
- [Limitations & Next Steps](#limitations--next-steps)
- [Contributing](#contributing)
- [References](#references)

---

## Highlights
- 🎨 K-Means color segmentation + contour extraction  
- 🧭 Optional linear pixel → lon/lat calibration (Italy preset)  
- 📦 Exports GeoJSON FeatureCollection and debug images (_segmented.png, _regions.png_)  
- 🔬 Prototype for research; roadmap in FEASIBILITY folder

---

## Quick Start
Prereqs: Python 3.8+, OpenCV, NumPy, Shapely (GeoPandas optional)

Install (example):
```bash
pip install opencv-python numpy shapely
# GeoPandas/rasterio recommended via conda if needed
```

Run prototype (interactive):
```bash
python "test con ai/image_to_geojson_auto.py"
```

---

## Usage (interactive)
1. Start the script and enter the image path when prompted.  
2. Choose calibration:
   - 1 — Italy preset (lat 36.0–47.5, lon 6.5–18.5)
   - 2 — Manual bounds
   - 3 — Skip (pixel coordinates)
3. Results are written next to the image:
   - image_segmented.png — K-Means visualization  
   - image_regions.png — annotated polygons and centroids  
   - image.geojson — GeoJSON FeatureCollection

Tip: wrap paths in quotes if they contain spaces.

---

## CLI / Automation hint
The script is interactive; for automation add argparse with flags, e.g.:
```
--image PATH --n_colors N --min_area PIXELS --calibration [italy|manual|none] --lat_min --lat_max --lon_min --lon_max
```
Implementing this enables batch processing and CI-friendly runs.

---

## Algorithm (overview)
- Read image with OpenCV and reshape pixels for clustering.  
- K-Means clustering groups pixels into N colors.  
- For each cluster: build mask → find contours → filter by area and color heuristics (remove water/white/black) → simplify contour → compute centroid.  
- Deduplicate overlapping regions and export top candidates as polygons.  
- Optional linear pixel→lat/lon mapping using bounding box.

---

## Calibration & Projection
- Italy preset: lat 36.0–47.5, lon 6.5–18.5 (linear map).
- Manual: provide lat/lon bounds at runtime.
> Note: calibration is linear and does not handle rotation/skew — for production use GCPs + GDAL/pyproj/affine transforms are required.

---

## Outputs
GeoJSON Feature properties:
- id: region_x  
- color: average RGB string (rgb(r,g,b))  
- area_pixels: integer

Debug artifacts:
- *_segmented.png — visual cluster map  
- *_regions.png — polygons + centroids overlay

Open GeoJSON at: https://geojson.io for quick visualization.

---

## Limitations & Next Steps
- Fragile on complex maps (labels, textures).  
- No topology validation (overlaps, holes).  
- Linear calibration only.  
Recommended improvements:
- Semantic segmentation (U-Net / DeepLab).  
- Robust georeferencing (GCPs, affine, GDAL).  
- Integration with GeoPandas for reprojection and topology cleaning.  
- Add CLI, tests and batch processing.

---

## Contributing
Contributions welcome: improve segmentation, add CLI, integrate reprojection, provide sample images. Please open issues / PRs with reproducible steps and sample data.

---

## References
- Prototype script: `test con ai/image_to_geojson_auto.py`  
- Feasibility study: `FEASIBILITY/StudioDiFattibilità.md`  
- Changelog: `CHANGELOG.md`

---