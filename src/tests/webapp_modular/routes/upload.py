"""
📤 Upload Routes
Endpoint per il caricamento delle immagini

Author: Map to GeoJSON Converter Project
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import cv2
import uuid
from pathlib import Path

from config import UPLOAD_DIR, ALLOWED_CONTENT_TYPES, THUMBNAIL_MAX_DIM
from segmentation import MapSegmenter
from utils import image_to_base64, resize_image
from session_manager import sessions

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """Carica un'immagine per l'elaborazione"""
    
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(400, f"Tipo file non supportato. Usa: PNG, JPG, WebP")
    
    session_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{session_id}_{file.filename}"
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    image = cv2.imread(str(file_path))
    if image is None:
        raise HTTPException(400, "Impossibile leggere l'immagine")
    
    height, width = image.shape[:2]
    
    # Crea thumbnail
    thumb = resize_image(image, THUMBNAIL_MAX_DIM)
    
    sessions[session_id] = {
        "file_path": str(file_path),
        "filename": file.filename,
        "width": width,
        "height": height,
        "image": image,
        "regions": [],
        "segmenter": MapSegmenter(image)
    }
    
    return {
        "session_id": session_id,
        "filename": file.filename,
        "width": width,
        "height": height,
        "image": image_to_base64(thumb)
    }
