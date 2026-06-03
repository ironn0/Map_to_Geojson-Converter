# Community Launch Copy (Ready to Paste)

## Show HN Draft

Title:

Show HN: Convert scanned maps to valid GeoJSON with assisted georeferencing

Body:

I built an open-source tool to convert map images (PNG/JPG/WebP/SVG) into GeoJSON.

Main focus: reliability on real maps, not just clean demos.

What it includes:

- robust segmentation options for noisy/historical scans,
- manual + CV-assisted georeferencing (`cv_auto`) with fallback metadata,
- circle detection/georeferencing (center + radius + geometry),
- export guardrails (coordinate clamping + NaN/Infinity sanitization) for better compatibility with geojson.io and map renderers.

Repo: https://github.com/ironn0/Map_to_Geojson-Converter

Quick start:

```bash
git clone https://github.com/ironn0/Map_to_Geojson-Converter.git
cd Map_to_Geojson-Converter
pip install -r requirements.txt
cd src/tests/webapp_modular
uvicorn main:app --reload
```

Would love feedback from people working with GIS, historical map digitization, or georeferencing workflows.

---

## Reddit Draft (`r/gis` / `r/opensource` / language subreddit)

Title:

Open-source map image -> GeoJSON converter (with assisted georeferencing)

Post:

I am sharing an open-source project I have been improving recently:

https://github.com/ironn0/Map_to_Geojson-Converter

It converts raster map images into GeoJSON and focuses on edge-case reliability:

- segmentation for noisy/historical maps,
- manual + CV-assisted georeferencing (`cv_auto` with fallback),
- circle detection and export,
- export sanitization to avoid invalid coordinates in downstream tools.

If you have sample maps that usually break converters, I would appreciate test cases/feedback.

---

## LinkedIn / X Short Post

I just improved my open-source `Map_to_Geojson-Converter` project.

Goal: convert scanned maps into GeoJSON that is actually usable in real workflows.

Recent improvements:

- guided UX flow + project/job status,
- circle-only extraction mode,
- georeferencing stability fixes,
- export guardrails for coordinate validity.

Repo: https://github.com/ironn0/Map_to_Geojson-Converter

Feedback from GIS and mapping developers is very welcome.

#opensource #gis #geojson #python #computervision
