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
1. Load image with OpenCV.
2. Convert to grayscale and apply thresholding for segmentation.
3. Find contours using `cv2.findContours`.
4. Filter contours by area and shape to identify regions.
5. Compute centroids and simplify polygons.
6. Optional: Apply K-Means for color-based segmentation.

---

## 🚀 Implementation - Phase 2: AI-Enhanced (with Deep Learning)

### Using YOLOv8 or U-Net
1. Preprocess image (resize, normalize).
2. Use pre-trained model for semantic segmentation (detect map elements).
3. Post-process masks to extract contours.
4. Integrate with GIS libraries for georeferencing.

### Example Code Snippet
```python
import cv2
import numpy as np
from shapely.geometry import Polygon

# Load image
img = cv2.imread('map.png')

# Simple segmentation
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
_, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Convert to GeoJSON-like structure
features = []
for cnt in contours:
    if cv2.contourArea(cnt) > 100:  # Filter small areas
        poly = Polygon(cnt.reshape(-1, 2))
        features.append({
            "type": "Feature",
            "geometry": poly.__geo_interface__,
            "properties": {"area": poly.area}
        })
```

---

## 🧪 Testing the Pipeline

### Unit Tests
- Test contour detection with sample images.
- Validate GeoJSON output structure.
- Check georeferencing accuracy.

### Integration Tests
- Run full pipeline on examples/ images.
- Compare outputs with expected GeoJSON.

Run tests: `python -m pytest ../tests/`

---

## ⚠️ Limitations & Challenges
- Accuracy depends on image quality (blurry maps fail).
- Georeferencing requires manual calibration for complex projections.
- AI models need GPU for real-time processing.
- Not suitable for 3D or vector maps.

---

## 🔮 Future Extensions
- Add web interface with Flask/Django.
- Integrate with QGIS for advanced editing.
- Support batch processing via CLI.
- Use cloud AI (e.g., Google Vision) for better accuracy.

---

## 📚 References
- OpenCV Docs: https://docs.opencv.org/
- PyTorch: https://pytorch.org/
- GeoPandas: https://geopandas.org/

See main README for usage.