# 🗺️ AI Map Extractor - Da Immagini a GeoJSON

## 🎯 Obiettivo
Convertire immagini di mappe (PNG, JPG, SVG) in file GeoJSON usando AI per:
1. Rilevare confini automaticamente
2. Identificare regioni/paesi
3. Georeferenziare le coordinate

---

## 🏗️ Architettura del Sistema

### Pipeline in 4 fasi:

```
Immagine Mappa
    ↓
[1] Preprocessing & Segmentazione (AI)
    ↓
[2] Contour Detection (OpenCV)
    ↓
[3] Georeferenziazione (Calibrazione)
    ↓
[4] Export GeoJSON
```

---

## 🛠️ Stack Tecnologico

### Librerie Python (tutte open source):

```python
# Computer Vision
opencv-python          # Contour detection
Pillow                # Image processing

# AI/Machine Learning
torch                 # Deep Learning
torchvision          # Pre-trained models
segment-anything     # Meta SAM (opzionale, pesante)
ultralytics          # YOLOv8 (alternativa più leggera)

# GIS
shapely              # Geometrie
geopy                # Geocoding
pyproj               # Proiezioni cartografiche

# Utilities
numpy
scipy
matplotlib
```

---

## 📦 Installazione

```bash
# Crea virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Installa dipendenze base
pip install opencv-python pillow numpy scipy matplotlib shapely geopy pyproj

# Installa AI (opzionale, richiede GPU)
pip install torch torchvision ultralytics
```

---

## 🚀 Implementazione - Fase 1: Base (senza AI pesante)

### Approccio con OpenCV (leggero e veloce)