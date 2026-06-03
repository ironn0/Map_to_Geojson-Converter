"""
📤 Upload Routes
Endpoint per il caricamento delle immagini

Author: Map to GeoJSON Converter Project
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import cv2
import numpy as np
import uuid

from config import UPLOAD_DIR, ALLOWED_CONTENT_TYPES, MAX_IMAGE_SIZE, PROCESSING_MAX_DIM
from segmentation import MapSegmenter
from utils import image_to_base64, resize_image, safe_filename
from session_manager import sessions

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """Carica un'immagine per l'elaborazione"""
    
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(400, f"Tipo file non supportato. Usa: PNG, JPG, WebP")
    
    session_id = str(uuid.uuid4())
    filename = safe_filename(file.filename)
    file_path = UPLOAD_DIR / f"{session_id}_{filename}"
    
    content = await file.read(MAX_IMAGE_SIZE + 1)
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(413, "Immagine troppo grande. Limite massimo: 25MB")
    
    image = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(400, "Impossibile leggere l'immagine")
    
    original_height, original_width = image.shape[:2]
    
    # L'app lavora su una copia ridimensionata: canvas, segmentazione ed export
    # condividono le stesse coordinate pixel, evitando errori di scala.
    processed = resize_image(image, PROCESSING_MAX_DIM)
    height, width = processed.shape[:2]
    cv2.imwrite(str(file_path), processed)
    
    sessions[session_id] = {
        "file_path": str(file_path),
        "filename": filename,
        "original_width": original_width,
        "original_height": original_height,
        "width": width,
        "height": height,
        "image": processed,
        "regions": [],
        "segmenter": MapSegmenter(processed)
    }
    
    return {
        "session_id": session_id,
        "filename": filename,
        "original_width": original_width,
        "original_height": original_height,
        "width": width,
        "height": height,
        "image": image_to_base64(processed)
    }
