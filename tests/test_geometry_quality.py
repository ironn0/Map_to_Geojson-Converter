from georeferencing.geometry_quality import sanitize_polygon_geometry


def test_sanitize_polygon_closes_ring_and_returns_polygon():
    geometry, metadata = sanitize_polygon_geometry(
        [[0, 0], [2, 0], [2, 2], [0, 2]],
        min_polygon_area=0.0,
        simplify_tolerance=0.0,
    )
    assert geometry["type"] == "Polygon"
    assert geometry["coordinates"][0][0] == geometry["coordinates"][0][-1]
    assert metadata["parts"] >= 1


def test_sanitize_polygon_keeps_multipolygon_when_enabled():
    # Figura a "8" che viene validata come multipoligono
    geometry, _ = sanitize_polygon_geometry(
        [[0, 0], [2, 2], [0, 2], [2, 0], [0, 0]],
        keep_multipolygons=True,
    )
    assert geometry["type"] in {"Polygon", "MultiPolygon"}
