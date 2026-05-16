"""
⚙️ Configuration Module
Configurazione centralizzata dell'applicazione

Author: Map to GeoJSON Converter Project
"""

import tempfile
from pathlib import Path

# ==================== App Settings ====================

APP_NAME = "Map to GeoJSON"
APP_VERSION = "2.0.0"
APP_DESCRIPTION = "Converti immagini di mappe in GeoJSON - Versione Modulare"

# ==================== Directories ====================

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = Path(tempfile.gettempdir()) / "map_to_geojson"
UPLOAD_DIR.mkdir(exist_ok=True)

# ==================== Image Settings ====================

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_CONTENT_TYPES = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
ALLOWED_IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".jpe", ".jfif", ".webp", ".bmp", ".tif", ".tiff"]
THUMBNAIL_MAX_DIM = 1200
SESSION_TTL_SECONDS = 60 * 60 * 4  # 4h

# ==================== Segmentation Defaults ====================

DEFAULT_N_COLORS = 40
DEFAULT_MIN_AREA = 500
MIN_REGION_AREA = 100

# Opt-in robust segmentation defaults
ROBUST_SEGMENTATION_DEFAULTS = {
    "denoise_strength": 10.0,
    "clahe_clip_limit": 2.5,
    "adaptive_block_size": 41,
    "adaptive_c": 2.0,
    "text_suppression": True,
    "morphology_kernel": 5,
    # Contour hardening settings (safe defaults keep current behavior)
    "contour_min_points": 4,
    "contour_solidity_min": 0.3,
    "contour_smoothing_epsilon_scale": 0.002,
    "artifact_min_component_area": 0,
}

# Optional geometry sanitization defaults (disabled for backward compatibility)
GEOMETRY_SANITIZE_DEFAULTS = {
    "enabled": False,
    "min_polygon_area": 0.0,
    "simplify_tolerance": 0.0,
    "keep_multipolygons": True,
}

# ==================== Geo Presets ====================

GEO_PRESETS = {
    "italy": {"north": 47.1, "south": 35.5, "east": 18.5, "west": 6.6, "name": "Italia"},
    "europe": {"north": 71.5, "south": 34.5, "east": 40.0, "west": -25.0, "name": "Europa"},
    "world": {"north": 85.0, "south": -85.0, "east": 180.0, "west": -180.0, "name": "Mondo"},
    "usa": {"north": 49.5, "south": 24.5, "east": -66.5, "west": -125.0, "name": "USA"},
    "germany": {"north": 55.1, "south": 47.3, "east": 15.0, "west": 5.9, "name": "Germania"},
    "france": {"north": 51.1, "south": 41.3, "east": 9.6, "west": -5.2, "name": "Francia"},
    "spain": {"north": 43.8, "south": 36.0, "east": 4.3, "west": -9.3, "name": "Spagna"}
}

# ==================== CORS Settings ====================

CORS_ORIGINS = ["*"]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]
