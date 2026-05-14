import base64

import cv2
import numpy as np
import pytest
from georeferencing import Georeferencer
from models import GeoBounds


def test_geobounds_rejects_invalid_order():
    with pytest.raises(ValueError):
        GeoBounds(north=40, south=41, east=10, west=5)


def test_geobounds_rejects_non_finite_numbers():
    with pytest.raises(ValueError):
        GeoBounds(north=float("nan"), south=35, east=18, west=6)


def test_georeferencer_rejects_invalid_image_size():
    with pytest.raises(ValueError):
        Georeferencer(0, 400, {"north": 47, "south": 35, "east": 18, "west": 6})


def test_contour_to_coords_requires_at_least_three_points():
    georef = Georeferencer(100, 100, {"north": 50, "south": 40, "east": 20, "west": 10})
    contour = np.array([[10, 10], [20, 20]], dtype=np.int32)

    with pytest.raises(ValueError):
        georef.contour_to_coords(contour)


def test_georeferencer_affine_transform_with_gcps():
    georef = Georeferencer(
        100,
        100,
        {"north": 10, "south": 0, "east": 10, "west": 0},
        georeferencing={
            "mode": "affine",
            "gcps": [
                {"pixel_x": 0, "pixel_y": 0, "lon": 1, "lat": 2},
                {"pixel_x": 100, "pixel_y": 0, "lon": 11, "lat": 2},
                {"pixel_x": 0, "pixel_y": 100, "lon": 1, "lat": -8},
            ],
        },
    )
    lon, lat = georef.pixel_to_coord(50, 50)
    assert lon == pytest.approx(6.0, abs=1e-3)
    assert lat == pytest.approx(-3.0, abs=1e-3)
    assert georef.get_transform_metrics()["mode"] == "affine"


def test_georeferencer_auto_selects_homography():
    georef = Georeferencer(
        100,
        100,
        {"north": 10, "south": 0, "east": 10, "west": 0},
        georeferencing={
            "mode": "auto",
            "gcps": [
                {"pixel_x": 0, "pixel_y": 0, "lon": 0, "lat": 10},
                {"pixel_x": 100, "pixel_y": 0, "lon": 10, "lat": 10},
                {"pixel_x": 100, "pixel_y": 100, "lon": 10, "lat": 0},
                {"pixel_x": 0, "pixel_y": 100, "lon": 0, "lat": 0},
            ],
        },
    )
    assert georef.get_transform_metrics()["mode"] == "homography"
    px = georef.coord_to_pixel(5, 5)
    assert px[0] == pytest.approx(50, abs=2)
    assert px[1] == pytest.approx(50, abs=2)


def test_georeferencer_rejects_poor_transform_quality():
    with pytest.raises(ValueError, match="errore residuo troppo elevato"):
        Georeferencer(
            100,
            100,
            {"north": 10, "south": 0, "east": 10, "west": 0},
            georeferencing={
                "mode": "affine",
                "max_rmse_ratio": 0.01,
                "validate_quality": True,
                "gcps": [
                    {"pixel_x": 0, "pixel_y": 0, "lon": 0, "lat": 10},
                    {"pixel_x": 100, "pixel_y": 0, "lon": 10, "lat": 10},
                    {"pixel_x": 0, "pixel_y": 100, "lon": 8, "lat": 0},
                    {"pixel_x": 100, "pixel_y": 100, "lon": 10, "lat": 0},
                ],
            },
        )


def test_georeferencer_cv_auto_falls_back_to_bounds_when_registration_fails():
    source = np.full((128, 128, 3), 255, dtype=np.uint8)
    ref = np.zeros((128, 128, 3), dtype=np.uint8)
    success, encoded = cv2.imencode(".png", ref)
    assert success
    ref_b64 = base64.b64encode(encoded.tobytes()).decode("ascii")

    georef = Georeferencer(
        128,
        128,
        {"north": 10, "south": 0, "east": 10, "west": 0},
        georeferencing={
            "mode": "cv_auto",
            "allow_fallback": True,
            "min_matches": 20,
            "inlier_threshold": 3.0,
            "confidence_threshold": 0.4,
            "cv_reference_image_base64": ref_b64,
            "cv_reference_bounds": {"north": 10, "south": 0, "east": 10, "west": 0},
        },
        source_image=source,
    )
    metrics = georef.get_transform_metrics()
    assert metrics["mode"] == "bounds"
    assert metrics["fallback_from"] == "cv_auto"
