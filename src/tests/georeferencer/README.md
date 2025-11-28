# 🗺️ Map Georeferencer

## Installation Guide

### Step 1: Install Python (if not installed)

**Windows:**
```bash
# Download from https://www.python.org/downloads/
# Or using winget:
winget install Python.Python.3.12
```

**macOS:**
```bash
brew install python
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

### Step 2: Clone the Repository
```bash
git clone https://github.com/ironn0/Map_to_Geojson-Converter.git
cd Map_to_Geojson-Converter
```

### Step 3: Create a Virtual Environment (Recommended)
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### Step 4: Install Dependencies
```bash
pip install opencv-python numpy geopandas shapely pillow
```

### Step 5: Run the Tool
```bash
cd src/tests/georeferencer
python map_georeferencer.py
```

---

## Approach
This tool uses **direct georeferencing** instead of shape matching:

1. **Calibration**: User selects 4 reference points on the map with their real coordinates
2. **Extraction**: K-Means extracts colored regions
3. **Point-in-Polygon**: For each region, the centroid is converted to geographic coordinates and matched against the GADM database
4. **Result**: ~100% accuracy if calibration is correct

## Why It Works
- Does not depend on region shapes (which are always different in stylized maps)
- Uses precise mathematical geometry (point-in-polygon)
- GADM database contains REAL administrative boundaries

## Usage

1. Open a map image
2. Click "🌍 Select Area" and choose the geographic region on the world map
3. Click "Extract Regions" to detect colored areas
4. Use checkboxes to select/deselect regions to include
5. Click "Identify" to match regions with GADM database
6. Export to GeoJSON
