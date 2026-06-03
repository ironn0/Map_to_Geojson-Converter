# From Scanned Maps to Valid GeoJSON: How We Built a Reliable Conversion Pipeline

## Hook

Most "image to polygon" demos stop at contour detection. Real-world usage starts when your output opens correctly in geojson.io and lands in the right place on Earth.

That is exactly what we optimized in `Map_to_Geojson-Converter`: map image -> stable segmentation -> assisted georeferencing -> valid GeoJSON export.

Repository: https://github.com/ironn0/Map_to_Geojson-Converter

---

## The Problem

We started with a simple goal: convert historical or scanned maps into usable GeoJSON without paid datasets.

The hard part was not extracting polygons. The hard part was making output reliable across edge cases:

- noisy scans and low-contrast borders,
- map warping and misalignment,
- invalid coordinates breaking geojson.io and map renderers.

---

## What We Built

### 1) Segmentation for "messy" maps

We support both legacy and robust segmentation paths:

- denoise + CLAHE + adaptive threshold options,
- contour hardening controls,
- manual edit/draw tools when automation is not enough.

### 2) Georeferencing with fallback strategy

- default bounds-based georeferencing for speed,
- optional `cv_auto` (feature matching + confidence checks),
- automatic fallback to safe mode with metadata so results are traceable.

### 3) Circle georeferencing workflow

For maps using circles as boundaries:

- detect circle,
- georeference center + radius in meters,
- export circle as GeoJSON geometry,
- optional circle-only export mode.

### 4) Export guardrails

To avoid invalid payloads, export now includes:

- coordinate clamping (lat/lon ranges),
- NaN/Infinity sanitization,
- geometry sanitization metadata in response properties.

---

## Product-Oriented Improvements

We recently added:

- guided wizard UX (next action, quality messages),
- project history timeline,
- background jobs with retry/timeout,
- operational error dashboard endpoints.

This turned a prototype into a tool people can use repeatedly.

---

## How to Run It

```bash
git clone https://github.com/ironn0/Map_to_Geojson-Converter.git
cd Map_to_Geojson-Converter
pip install -r requirements.txt
cd src/tests/webapp_modular
uvicorn main:app --reload
```

Open `http://localhost:8000`.

---

## Validation

We gate changes with:

- automated test suite,
- benchmark thresholds for precision/recall/spatial error/runtime,
- export validity checks.

```bash
python scripts/verify.py
```

---

## Looking for Feedback

If you work with GIS, historical maps, or map digitization pipelines, I would love feedback on:

- georeferencing UX,
- difficult map examples,
- export compatibility with your tooling.

If this is useful, a GitHub star helps others discover the project.

Repository: https://github.com/ironn0/Map_to_Geojson-Converter
