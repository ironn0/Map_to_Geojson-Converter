# 🗺️ AI Map Extractor - From Images to GeoJSON

## 🎯 Objective
Convert map images (PNG, JPG, SVG) to GeoJSON files using AI for:
1. Automatically detect borders
2. Identify regions/countries
3. Georeference coordinates

---

## 🏗️ System Architecture

### Pipeline in 4 phases:

```
Map Image
    ↓
[1] Preprocessing & Segmentation (AI)
    ↓
[2] Contour Detection (OpenCV)
    ↓
[3] Georeferencing (Calibration)
    ↓
[4] Export GeoJSON
```

---

## 🛠️ Technology Stack

### Python Libraries (all open source):

```python
# Computer Vision
opencv-python          # Contour detection
Pillow                # Image processing

# AI/Machine Learning
torch                 # Deep Learning
torchvision          # Pre-trained models
segment-anything     # Meta SAM (optional, heavy)
ultralytics          # YOLOv8 (lighter alternative)

# GIS
shapely              # Geometries
geopy                # Geocoding
pyproj               # Map projections

# Utilities
numpy
scipy
matplotlib
```

---

## 📦 Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install base dependencies
pip install opencv-python pillow numpy scipy matplotlib shapely geopy pyproj

# Install AI (optional, requires GPU)
pip install torch torchvision ultralytics
```

---

## 🚀 Implementation - Phase 1: Base (without heavy AI)

### Approach with OpenCV (light and fast)