# Webapp GIS Hybrid

Cartella sperimentale separata da `src/tests/webapp_modular`.

Questi moduli implementano il flusso proposto per passare da "estraggo tutto dal raster" a "uso la Computer Vision come guida e aggancio i risultati a geometrie GIS reali".

## Moduli

- `segmentation/segmenter.py`: `AdvancedSegmenter` con filtri su area relativa, aspect ratio, solidita' e report debug.
- `georeferencing/georeferencer.py`: `Georeferencer` affine con supporto GCP via `numpy.linalg.lstsq`.
- `georeferencing/aligner.py`: snap topologico con `shapely`/`geopandas` basato su IoU.
- `segmentation/sam_adapter.py`: backend SAM opzionale con fallback controllato su `AdvancedSegmenter`.
- `hybrid_pipeline.py`: esempio operativo CV -> georeferenziazione affine -> snap GIS.

## Uso rapido

```python
from segmentation import AdvancedSegmenter

segmenter = AdvancedSegmenter(image, debug=True)
regions = segmenter.segment(n_colors=20, min_area=500)
print(segmenter.get_debug_report())
```

```python
from georeferencing import Georeferencer

georef = Georeferencer(width, height, bounds)
georef.estimate_transform_from_gcp(
    [(0, 0), (100, 0), (0, 100)],
    [(10, 45), (11, 45.1), (10.1, 44)],
)
coords = georef.contour_to_coords(region.contour)
```

```python
from georeferencing import TerritoryAligner

aligner = TerritoryAligner(reference_geojson, iou_threshold=0.6)
aligned_features = aligner.align_all(features, snap_strength=1.0)
```

```python
from hybrid_pipeline import run_hybrid_extraction

geojson = run_hybrid_extraction(
    image,
    bounds={"north": 47.1, "south": 35.5, "east": 18.5, "west": 6.6},
    reference_geojson=my_reference,
    debug=True,
)
```

## Note di migrazione

La cartella e' intenzionalmente autonoma. Dopo il confronto sui casi reali, i file possono sostituire gradualmente gli omonimi dentro `webapp_modular`, mantenendo `MapSegmenter`, `Georeferencer` e `TerritoryAligner` come nomi compatibili.
