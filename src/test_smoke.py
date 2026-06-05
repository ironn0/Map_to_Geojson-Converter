import asyncio
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from models import BrushResegmentRequest, EraseSegmentRequest, ExportRequest  # noqa: E402
from routes.export import export_geojson  # noqa: E402
from routes.segmentation import erase_and_segment, resegment_with_brush  # noqa: E402
from segmentation import MapSegmenter  # noqa: E402
from session_manager import sessions  # noqa: E402


def overlay_test_image():
    image = np.full((500, 700, 3), (240, 238, 232), np.uint8)

    # Simula strade/confini/label sotto a forme semitrasparenti.
    for x in range(50, 650, 70):
        cv2.line(image, (x, 0), (x + 120, 500), (190, 170, 160), 1)
    for y in range(50, 450, 60):
        cv2.line(image, (0, y), (700, y + 40), (180, 210, 180), 2)
    cv2.putText(image, "Niger", (360, 260), cv2.FONT_HERSHEY_SIMPLEX, 1, (80, 80, 80), 2)

    overlay = image.copy()
    cv2.rectangle(overlay, (380, 140), (560, 390), (160, 80, 120), -1)
    cv2.circle(overlay, (250, 200), 80, (170, 90, 130), -1)
    image = cv2.addWeighted(overlay, 0.45, image, 0.55, 0)
    cv2.rectangle(image, (380, 140), (560, 390), (160, 0, 160), 3)
    cv2.circle(image, (250, 200), 80, (160, 0, 160), 3)
    return image


def test_segmenter_detects_colored_regions_without_full_background():
    image = np.full((120, 160, 3), 255, np.uint8)
    cv2.rectangle(image, (20, 20), (70, 90), (0, 0, 255), -1)
    cv2.rectangle(image, (90, 25), (140, 95), (0, 180, 0), -1)

    regions = MapSegmenter(image).segment(n_colors=4, min_area=150)

    assert len(regions) >= 2
    assert all(region.area < image.shape[0] * image.shape[1] * 0.65 for region in regions)


def test_segmenter_prefers_external_overlay_shapes_over_internal_map_lines():
    image = overlay_test_image()

    regions = MapSegmenter(image).segment(n_colors=10, min_area=3000)
    large_regions = [region for region in regions if region.area > 15000]

    assert len(large_regions) == 2
    assert all(len(region.contour) < 80 for region in large_regions)


def test_click_mode_does_not_capture_the_whole_map_on_overlay_shapes():
    segmenter = MapSegmenter(overlay_test_image())

    circle = segmenter.segment_at_point(250, 200)
    rectangle = segmenter.segment_at_point(470, 240)

    assert circle is not None
    assert rectangle is not None
    assert 15000 < circle.area < 30000
    assert 35000 < rectangle.area < 60000


def test_click_mode_on_overlay_border_selects_the_whole_shape():
    segmenter = MapSegmenter(overlay_test_image())

    circle_border = segmenter.segment_at_point(250, 120)
    rectangle_border = segmenter.segment_at_point(380, 240)

    assert circle_border is not None
    assert rectangle_border is not None
    assert 15000 < circle_border.area < 30000
    assert 35000 < rectangle_border.area < 60000


def test_click_mode_prefers_parent_overlay_over_internal_fragments():
    image = overlay_test_image()
    cv2.line(image, (470, 145), (470, 385), (160, 0, 160), 5)
    segmenter = MapSegmenter(image)

    region = segmenter.segment_at_point(470, 240)

    assert region is not None
    assert 35000 < region.area < 60000


def test_export_uses_visible_editor_state_for_areas_and_points():
    session_id = "smoke-export"
    sessions[session_id] = {
        "width": 220,
        "height": 160,
        "regions": [],
    }

    try:
        result = asyncio.run(
            export_geojson(
                ExportRequest(
                    session_id=session_id,
                    bounds={"north": 10, "south": 0, "east": 20, "west": 0},
                    regions=[
                        {
                            "id": 0,
                            "name": "Area influenza",
                            "color": "#ef4444",
                            "type": "regno",
                            "description": "Area storica",
                            "properties": {"periodo": "1800", "fonte": "test"},
                            "points": [[20, 20], [100, 20], [100, 120], [20, 120]],
                        }
                    ],
                    points=[
                        {
                            "id": 0,
                            "name": "Ospedale",
                            "type": "poi",
                            "color": "#2563eb",
                            "description": "Punto notevole",
                            "properties": {"rank": 1},
                            "x": 60,
                            "y": 70,
                        }
                    ],
                )
            )
        )
    finally:
        sessions.pop(session_id, None)

    features = result["features"]
    assert [feature["geometry"]["type"] for feature in features] == ["Polygon", "Point"]
    assert features[0]["properties"]["name"] == "Area influenza"
    assert features[0]["properties"]["type"] == "regno"
    assert features[0]["properties"]["description"] == "Area storica"
    assert features[0]["properties"]["periodo"] == "1800"
    assert features[1]["properties"]["name"] == "Ospedale"
    assert features[1]["properties"]["type"] == "poi"
    assert features[1]["properties"]["color"] == "#2563eb"
    assert features[1]["properties"]["rank"] == 1


def test_erase_and_segment_updates_session_image_and_regions():
    session_id = "smoke-erase"
    image = overlay_test_image()
    sessions[session_id] = {
        "width": image.shape[1],
        "height": image.shape[0],
        "image": image,
        "original_image": image.copy(),
        "regions": [],
        "segmenter": MapSegmenter(image),
    }

    try:
        result = asyncio.run(
            erase_and_segment(
                EraseSegmentRequest(
                    session_id=session_id,
                    strokes=[[[470, 145], [470, 385]]],
                    radius=12,
                    n_colors=10,
                    min_area=3000,
                )
            )
        )
    finally:
        sessions.pop(session_id, None)

    assert result["success"] is True
    assert result["num_regions"] >= 1
    assert result["image"]
    assert result["visualization"]


def test_brush_resegment_uses_alternative_seed_outside_marked_area():
    session_id = "smoke-brush-resegment"
    image = overlay_test_image()
    sessions[session_id] = {
        "width": image.shape[1],
        "height": image.shape[0],
        "image": image,
        "original_image": image.copy(),
        "regions": [],
        "segmenter": MapSegmenter(image),
    }

    region = {
        "id": 0,
        "name": "Rettangolo",
        "color": "#2563eb",
        "featureType": "area",
        "properties": {"fonte": "manuale"},
        "points": [[380, 140], [560, 140], [560, 390], [380, 390]],
    }

    try:
        result = asyncio.run(
            resegment_with_brush(
                BrushResegmentRequest(
                    session_id=session_id,
                    regions=[region],
                    strokes=[[[545, 230], [555, 260]]],
                    radius=18,
                    selected_region_id=0,
                    n_colors=10,
                    min_area=3000,
                )
            )
        )
    finally:
        sessions.pop(session_id, None)

    assert result["success"] is True
    assert result["selected_region_id"] == 0
    assert result["seed"][0] < 540
    assert result["regions"][0]["name"] == "Rettangolo"
    assert result["regions"][0]["properties"]["fonte"] == "manuale"
    assert result["image"]


def test_brush_resegment_excludes_marked_side_lobe_like_label():
    session_id = "smoke-brush-lobe"
    image = np.full((180, 240, 3), (240, 238, 232), np.uint8)
    polygon = np.array(
        [[60, 40], [150, 40], [150, 76], [188, 76], [188, 104], [150, 104], [150, 140], [60, 140]],
        dtype=np.int32,
    )
    overlay = image.copy()
    cv2.fillPoly(overlay, [polygon], (160, 80, 120))
    image = cv2.addWeighted(overlay, 0.45, image, 0.55, 0)
    cv2.polylines(image, [polygon], True, (160, 0, 160), 3)
    cv2.putText(image, "Chad", (158, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (70, 70, 70), 1)

    sessions[session_id] = {
        "width": image.shape[1],
        "height": image.shape[0],
        "image": image,
        "original_image": image.copy(),
        "regions": [],
        "segmenter": MapSegmenter(image),
    }

    region = {
        "id": 0,
        "name": "Regione con label",
        "color": "#2563eb",
        "featureType": "area",
        "properties": {},
        "points": polygon.astype(float).tolist(),
    }

    try:
        result = asyncio.run(
            resegment_with_brush(
                BrushResegmentRequest(
                    session_id=session_id,
                    regions=[region],
                    strokes=[[[166, 84], [182, 98]]],
                    radius=16,
                    selected_region_id=0,
                    n_colors=10,
                    min_area=500,
                )
            )
        )
    finally:
        sessions.pop(session_id, None)

    xs = [point[0] for point in result["regions"][0]["points"]]
    assert result["success"] is True
    assert max(xs) <= 154
    assert result["seed"][0] < 145


def test_erase_and_segment_restore_uses_original_image_pixels():
    session_id = "smoke-restore"
    original = overlay_test_image()
    edited = original.copy()
    cv2.rectangle(edited, (430, 180), (520, 260), (255, 255, 255), -1)
    sessions[session_id] = {
        "width": edited.shape[1],
        "height": edited.shape[0],
        "image": edited,
        "original_image": original.copy(),
        "regions": [],
        "segmenter": MapSegmenter(edited),
    }

    try:
        result = asyncio.run(
            erase_and_segment(
                EraseSegmentRequest(
                    session_id=session_id,
                    strokes=[[[450, 200], [500, 240]]],
                    radius=20,
                    mode="restore",
                    n_colors=10,
                    min_area=3000,
                )
            )
        )
        restored = sessions[session_id]["image"]
    finally:
        sessions.pop(session_id, None)

    assert result["success"] is True
    assert np.mean(restored[200:240, 450:500]) < 245
