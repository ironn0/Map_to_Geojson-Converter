"""
🔧 Utility Functions Module
Funzioni di utilità comuni

Author: Map to GeoJSON Converter Project
"""

import cv2
import base64
import numpy as np
from typing import Dict
from models import ExtractedRegion


def image_to_base64(image: np.ndarray) -> str:
    """Converte un'immagine numpy in stringa base64"""
    _, buffer = cv2.imencode('.png', image)
    return base64.b64encode(buffer).decode('utf-8')


def base64_to_image(base64_str: str) -> np.ndarray:
    """Converte una stringa base64 in immagine numpy"""
    if base64_str.startswith('data:'):
        base64_str = base64_str.split(',')[1]
    img_bytes = base64.b64decode(base64_str)
    nparr = np.frombuffer(img_bytes, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)


def region_to_dict(region: ExtractedRegion, idx: int) -> Dict:
    """Converte una ExtractedRegion in dizionario JSON-compatibile"""
    return {
        "id": idx,
        "name": region.name or f"Regione {idx + 1}",
        "area": region.area,
        "centroid": list(region.centroid),
        "bbox": list(region.bbox),
        "color": f"#{region.color[2]:02x}{region.color[1]:02x}{region.color[0]:02x}",
        "points": region.contour.reshape(-1, 2).tolist()
    }


def resize_image(image: np.ndarray, max_dim: int = 1200) -> np.ndarray:
    """Ridimensiona un'immagine mantenendo le proporzioni"""
    height, width = image.shape[:2]
    if max(width, height) > max_dim:
        scale = max_dim / max(width, height)
        return cv2.resize(image, None, fx=scale, fy=scale)
    return image


def validate_bounds(bounds: Dict) -> bool:
    """Valida i confini geografici"""
    required = ['north', 'south', 'east', 'west']
    if not all(k in bounds for k in required):
        return False
    
    if bounds['north'] <= bounds['south']:
        return False
    if bounds['east'] <= bounds['west']:
        return False
    
    return True


def validate_contour(contour: np.ndarray) -> bool:
    """Valida un contorno OpenCV prima della conversione geospaziale."""
    if contour is None:
        return False

    if not isinstance(contour, np.ndarray):
        return False

    if contour.size == 0:
        return False

    # Accept both OpenCV contour shapes: (N, 1, 2) and (N, 2)
    if contour.ndim == 3 and contour.shape[-2:] != (1, 2):
        return False
    if contour.ndim == 2 and contour.shape[-1] != 2:
        return False
    if contour.ndim not in (2, 3):
        return False

    points = contour.reshape(-1, 2)
    if len(points) < 3:
        return False

    return np.isfinite(points).all()


def color_hex_to_bgr(hex_color: str) -> tuple:
    """Converte colore hex in BGR"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return (b, g, r)


def color_bgr_to_hex(bgr: tuple) -> str:
    """Converte colore BGR in hex"""
    return f"#{bgr[2]:02x}{bgr[1]:02x}{bgr[0]:02x}"
