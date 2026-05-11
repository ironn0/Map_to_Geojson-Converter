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
