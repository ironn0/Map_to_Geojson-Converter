"""
🛣️ Routes Package
API endpoints organizzati in moduli

Author: Map to GeoJSON Converter Project
"""

from .alignment import router as alignment_router
from .export import router as export_router
from .segmentation import router as segmentation_router
from .upload import router as upload_router

__all__ = [
    'upload_router',
    'segmentation_router', 
    'export_router',
    'alignment_router'
]
