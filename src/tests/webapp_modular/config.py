"""
⚙️ Configuration Module
Configurazione centralizzata dell'applicazione

Author: Map to GeoJSON Converter Project
"""

from pathlib import Path
import tempfile

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
THUMBNAIL_MAX_DIM = 1200

# ==================== Segmentation Defaults ====================

DEFAULT_N_COLORS = 40
DEFAULT_MIN_AREA = 500
MIN_REGION_AREA = 100

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
