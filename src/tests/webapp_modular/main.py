"""
🗺️ Map to GeoJSON Web App - Modular Version
Entry point dell'applicazione FastAPI

Author: Map to GeoJSON Converter Project
"""

import sys
from pathlib import Path

# Add the current directory to sys.path for absolute imports
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_HEADERS,
    CORS_ALLOW_METHODS,
    CORS_ORIGINS,
    STATIC_DIR,
)
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from routes import (
    alignment_router,
    circle_router,
    export_router,
    segmentation_router,
    upload_router,
)
from session_manager import delete_session

# ==================== App Initialization ====================

app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION
)

# ==================== Middleware ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)

# ==================== Routers ====================

app.include_router(upload_router)
app.include_router(segmentation_router)
app.include_router(export_router)
app.include_router(alignment_router)
app.include_router(circle_router)

# ==================== Static Pages ====================

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve la pagina HTML principale"""
    html_path = STATIC_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding='utf-8'))
    return HTMLResponse(content="<h1>Frontend not found. Create static/index.html</h1>")


@app.get("/privacy", response_class=HTMLResponse)
async def serve_privacy():
    """Serve la pagina Privacy & Cookie Policy"""
    html_path = STATIC_DIR / "privacy.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding='utf-8'))
    return HTMLResponse(content="<h1>Privacy page not found</h1>")


# ==================== Session Management ====================

@app.delete("/api/session/{session_id}")
async def delete_user_session(session_id: str):
    """Elimina una sessione e i file temporanei"""
    success = delete_session(session_id)
    return {"success": success}


# ==================== Static Files ====================

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ==================== Main ====================

if __name__ == "__main__":
    import uvicorn
    print(f"\n🗺️  {APP_NAME} v{APP_VERSION}")
    print("   Versione Modulare")
    print("   Apri http://localhost:8000 nel browser\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
