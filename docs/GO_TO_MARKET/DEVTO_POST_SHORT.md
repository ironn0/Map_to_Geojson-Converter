# From Scanned Maps to Valid GeoJSON (Short Version)

Most map-image conversion demos stop at "polygon extraction".  
Real usage starts when the output is georeferenced correctly and opens without errors in tools like geojson.io.

That is the focus of `Map_to_Geojson-Converter`:

- convert raster maps (PNG/JPG/WebP) and SVG to GeoJSON,
- support noisy/historical scans with robust segmentation options,
- assist georeferencing with manual controls and optional `cv_auto` fallback flow,
- export stable GeoJSON with coordinate clamping and JSON numeric sanitization.

Repository: https://github.com/ironn0/Map_to_Geojson-Converter

## What changed recently

- Guided wizard UX (Upload -> Segment -> Georef/Circle -> Export)
- Project history and job-status views
- Background jobs with retry/timeout
- Circle-only extraction mode
- Export guardrails for invalid coordinate edge cases

## Quick start

```bash
git clone https://github.com/ironn0/Map_to_Geojson-Converter.git
cd Map_to_Geojson-Converter
pip install -r requirements.txt
cd src/tests/webapp_modular
uvicorn main:app --reload
```

Open `http://localhost:8000`.

## Reliability gates

Before release, run:

```bash
python scripts/verify.py
```

This runs lint, tests, and benchmark thresholds.

---

If you work with GIS or historical map digitization, I would love feedback on difficult map samples and georeferencing workflows.
