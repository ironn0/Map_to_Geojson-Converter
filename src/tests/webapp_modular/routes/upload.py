"""
📤 Upload Routes
Endpoint per il caricamento delle immagini

Author: Map to GeoJSON Converter Project
"""

import uuid
from pathlib import Path

import cv2
import numpy as np
from billing_store import consume_quota
from config import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_IMAGE_EXTENSIONS,
    MAX_IMAGE_SIZE,
    THUMBNAIL_MAX_DIM,
    UPLOAD_DIR,
)
from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from segmentation import MapSegmenter
from session_manager import create_session, prune_expired_sessions
from utils import image_to_base64, resize_image

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    authorization: str = Header(default="", alias="Authorization"),
):
    """Carica un'immagine per l'elaborazione"""

    content_type = (file.content_type or "").lower()
    suffix = Path(file.filename or "").suffix.lower()
    if not _is_supported_upload(content_type, suffix):
        raise HTTPException(
            400,
            (
                "Tipo file non supportato. "
                f"Ricevuto content-type '{content_type or 'n/d'}' e estensione '{suffix or 'n/d'}'. "
                "Usa PNG, JPG, WebP, BMP o TIFF."
            ),
        )

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
    try:
        consume_quota(authorization, metric="uploads", amount=1)
    except PermissionError as exc:
        raise HTTPException(429, str(exc))
    except ValueError:
        pass
    
    return {
        "session_id": session_id,
        "filename": safe_name,
        "width": width,
        "height": height,
        "image": image_to_base64(thumb)
    }


def _is_supported_upload(content_type: str, suffix: str) -> bool:
    if content_type in ALLOWED_CONTENT_TYPES:
        return True
    # Alcuni browser/OS inviano MIME non standard (es. image/pjpeg) oppure vuoto/octet-stream.
    if content_type.startswith("image/"):
        return True
    if content_type in ("", "application/octet-stream") and suffix in ALLOWED_IMAGE_EXTENSIONS:
        return True
    return False
