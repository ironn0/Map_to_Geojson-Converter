# ­ƒñû SAM (Segment Anything Model) Test

This folder contains a test implementation using Meta's **Segment Anything Model (SAM)** for extracting region boundaries from map images.

## Why SAM?

| Feature | K-Means (current) | SAM |
|---------|-------------------|-----|
| Accuracy | ~60-70% | ~90%+ |
| Training | None | Pre-trained on 1B masks |
| Edge detection | Poor | Excellent |
| Complex shapes | Struggles | Handles well |
| Speed | Fast | Slower (needs GPU) |

## Installation

```bash
# Install PyTorch (with CUDA if you have GPU)
pip install torch torchvision

# Install transformers and other dependencies
pip install transformers pillow numpy opencv-python

# For region identification (optional but recommended)
pip install geopandas shapely
```

### GPU Support (Recommended)

For CUDA support, install PyTorch with CUDA:
```bash
# For CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

## Usage

### GUI Mode (Recommended)

```bash
python sam_gui.py
```

Features:
- Load map images
- Choose SAM model (base/large/huge)
- Automatic or point-click segmentation
- Load geographic database (Natural Earth or GADM Italy)
- Auto-identify regions by matching with database
- Export to GeoJSON with real geographic coordinates

### Basic Usage (Python)

```python
from sam_segmenter import SAMSegmenter

# Initialize (auto-detects GPU)
segmenter = SAMSegmenter(model_name="facebook/sam-vit-base")

# Automatic segmentation
regions = segmenter.segment_automatic("path/to/map.png")

# Visualize results
segmenter.visualize_regions("path/to/map.png", regions, "output.png")

# Export to GeoJSON
segmenter.export_geojson(regions, "output.geojson")
```

### Interactive Segmentation (click points)

```python
# Segment specific points clicked by user
points = [(100, 200), (300, 400), (500, 300)]
regions = segmenter.segment_with_points("path/to/map.png", points)
```

### Region Identification with Database

```python
from sam_segmenter import SAMSegmenter, RegionMatcher

# Segment the image
segmenter = SAMSegmenter()
regions = segmenter.segment_automatic("italy_map.png")

# Load geographic database
matcher = RegionMatcher(
    shapefile_path="geodata/gadm_italy/gadm41_ITA_1.shp",
    name_field="NAME_1"
)

# Define map bounds (lat/lon)
geo_bounds = {
    'north': 47.1,
    'south': 35.5,
    'east': 18.5,
    'west': 6.6
}

# Identify regions
results = matcher.identify_regions(regions, geo_bounds, image_size=(1000, 800))
# results = {0: "Lombardia", 1: "Piemonte", 2: "Veneto", ...}

# Export with names
segmenter.export_geojson(
    regions, 
    "output.geojson",
    geo_bounds=geo_bounds,
    image_size=(1000, 800),
    region_names=results
)
```

## Available Models

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `facebook/sam-vit-base` | 93M | Fast | Good |
| `facebook/sam-vit-large` | 312M | Medium | Better |
| `facebook/sam-vit-huge` | 641M | Slow | Best |

## Geographic Databases

The region matcher supports:

| Database | Coverage | Regions | Path |
|----------|----------|---------|------|
| Natural Earth | Worldwide | ~4,600 | `test comparison/geodata/ne_10m_admin_1_states_provinces/` |
| GADM Italy | Italy | 20 | `georeferencer/geodata/gadm_italy/gadm41_ITA_1.shp` |

## Output

The segmenter produces:
- **Visualization**: PNG with colored region overlays
- **GeoJSON**: Polygon geometries with properties (id, name, area, color, score)

### Sample GeoJSON Output

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "id": 1,
        "name": "Lombardia",
        "area_pixels": 45678,
        "color": "#ff5733",
        "score": 0.95
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[9.5, 45.8], [10.2, 46.1], ...]]
      }
    }
  ]
}
```

## Demo

Run the demo:
```bash
python sam_segmenter.py
```

## Notes

- First run will download the model (~400MB for base)
- GPU is strongly recommended for speed
- Works best on maps with clear region boundaries
- Can handle stylized/artistic maps better than K-Means
- Region identification requires `geopandas` and `shapely`
