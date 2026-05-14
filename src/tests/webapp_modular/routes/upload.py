"""
📤 Upload Routes
Endpoint per il caricamento delle immagini

Author: Map to GeoJSON Converter Project
"""

import uuid
from pathlib import Path

import cv2
import numpy as np
from config import ALLOWED_CONTENT_TYPES, MAX_IMAGE_SIZE, THUMBNAIL_MAX_DIM, UPLOAD_DIR
from fastapi import APIRouter, File, HTTPException, UploadFile
from segmentation import MapSegmenter
from session_manager import create_session, prune_expired_sessions
from utils import image_to_base64, resize_image

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """Carica un'immagine per l'elaborazione"""
    
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(400, "Tipo file non supportato. Usa: PNG, JPG, WebP")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(400, "File immagine vuoto")
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(413, f"Immagine troppo grande. Limite: {MAX_IMAGE_SIZE // (1024 * 1024)}MB")

    nparr = np.frombuffer(content, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(400, "Impossibile leggere l'immagine")

    session_id = str(uuid.uuid4())
    safe_name = Path(file.filename or "image_upload").name
    file_path = UPLOAD_DIR / f"{session_id}_{safe_name}"
    with open(file_path, "wb") as f:
        f.write(content)
    
    height, width = image.shape[:2]
    
    # Crea thumbnail
    thumb = resize_image(image, THUMBNAIL_MAX_DIM)
    
    prune_expired_sessions()
    create_session(session_id, {
        "file_path": str(file_path),
        "filename": safe_name,
        "width": width,
        "height": height,
        "image": image,
        "regions": [],
        "segmenter": MapSegmenter(image)
    })
    
    return {
        "session_id": session_id,
        "filename": safe_name,
        "width": width,
        "height": height,
        "image": image_to_base64(thumb)
    }
