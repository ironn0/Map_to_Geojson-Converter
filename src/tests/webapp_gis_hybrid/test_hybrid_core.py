import sys
from pathlib import Path

import cv2
import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).parent))

from georeferencing import Georeferencer, align_with_reference  # noqa: E402
from hybrid_pipeline import run_hybrid_extraction  # noqa: E402
from segmentation import AdvancedSegmenter, MapSegmenter  # noqa: E402


def test_advanced_segmenter_filters_text_like_shapes_and_logs_reasons():
    image = np.full((200, 300, 3), 245, np.uint8)
    cv2.rectangle(image, (40, 40), (125, 130), (30, 80, 220), -1)
    cv2.rectangle(image, (160, 50), (280, 62), (20, 20, 220), -1)

    segmenter = AdvancedSegmenter(image, min_area_ratio=0.001, max_aspect_ratio=4.0, debug=True)
    regions = segmenter.segment(n_colors=6, min_area=50)
    report = segmenter.get_debug_report()

    assert regions
    assert all(region.bbox[2] / region.bbox[3] <= 4.0 for region in regions)
    assert any(entry["status"] == "REJECTED" for entry in report)
    assert any("aspect_ratio" in entry["reason"] for entry in report)


def test_map_segmenter_name_remains_backward_compatible():
    image = np.full((80, 80, 3), 255, np.uint8)
    cv2.circle(image, (40, 40), 20, (0, 0, 255), -1)

    assert isinstance(MapSegmenter(image), AdvancedSegmenter)


def test_georeferencer_estimates_affine_transform_from_gcps():
    georef = Georeferencer(100, 100, {"north": 10, "south": 0, "east": 10, "west": 0})
    georef.estimate_transform_from_gcp(
        [(0, 0), (100, 0), (0, 100), (100, 100)],
        [(10, 45), (12, 46), (9, 43), (11, 44)],
    )

    assert georef.pixel_to_coord(50, 50) == (10.5, 44.5)
    assert georef.coord_to_pixel(10.5, 44.5) == (50, 50)


def test_align_with_reference_replaces_extracted_geometry_on_high_iou():
    extracted = Polygon([(0, 0), (10, 0), (10, 9), (0, 9), (0, 0)])
    official = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    reference = gpd.GeoDataFrame({"name": ["official"]}, geometry=[official], crs="EPSG:4326")

    aligned = align_with_reference(extracted, reference, iou_threshold=0.6)

    assert aligned.equals_exact(official, tolerance=0)


def test_align_with_reference_keeps_original_when_iou_is_low():
    extracted = Polygon([(30, 30), (40, 30), (40, 40), (30, 40), (30, 30)])
    official = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    reference = gpd.GeoDataFrame({"name": ["official"]}, geometry=[official], crs="EPSG:4326")

    aligned = align_with_reference(extracted, reference, iou_threshold=0.6)

    assert aligned.equals_exact(extracted, tolerance=0)


def test_hybrid_pipeline_returns_feature_collection_with_debug_report():
    image = np.full((120, 160, 3), 245, np.uint8)
    cv2.rectangle(image, (30, 30), (90, 90), (20, 80, 220), -1)

    result = run_hybrid_extraction(
        image,
        bounds={"north": 10, "south": 0, "east": 20, "west": 0},
        n_colors=4,
        min_area=50,
        debug=True,
    )

    assert result["type"] == "FeatureCollection"
    assert result["features"]
    assert result["properties"]["debug"]
