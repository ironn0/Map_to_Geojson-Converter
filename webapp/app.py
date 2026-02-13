"""
🗺️ Map to GeoJSON Web App
Applicazione web per convertire immagini di mappe in formato GeoJSON

Author: Map to GeoJSON Converter Project
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Tuple
import numpy as np
import cv2
from PIL import Image
import json
import base64
import uuid
from pathlib import Path
import tempfile
import os
from dataclasses import dataclass

# ==================== Configuration ====================

app = FastAPI(
    title="Map to GeoJSON",
    description="Converti immagini di mappe in GeoJSON",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory per file temporanei
UPLOAD_DIR = Path(tempfile.gettempdir()) / "map_to_geojson"
UPLOAD_DIR.mkdir(exist_ok=True)

# Storage sessioni (in memoria)
sessions: Dict[str, Dict] = {}


# ==================== Data Models ====================

@dataclass
class ExtractedRegion:
    """Regione estratta dalla mappa"""
    contour: np.ndarray
    centroid: Tuple[float, float]
    area: float
    bbox: Tuple[int, int, int, int]
    color: Tuple[int, int, int]
    name: Optional[str] = None


class GeoBounds(BaseModel):
    north: float = 47.1
    south: float = 35.5
    east: float = 18.5
    west: float = 6.6


class SegmentRequest(BaseModel):
    session_id: str
    n_colors: int = 40
    min_area: int = 500


class PointRequest(BaseModel):
    session_id: str
    x: int
    y: int


class ExportRequest(BaseModel):
    session_id: str
    bounds: GeoBounds
    region_names: Optional[Dict[int, str]] = None


class UpdateRegionRequest(BaseModel):
    session_id: str
    region_id: int
    points: List[List[float]]


class AlignRequest(BaseModel):
    session_id: str
    bounds: GeoBounds
    reference_geojson: Optional[Dict] = None
    snap_strength: float = 0.5


# ==================== Segmentation Engine ====================

class MapSegmenter:
    """Motore di segmentazione avanzato con edge detection e watershed"""
    
    def __init__(self, image: np.ndarray):
        self.image = image
        self.height, self.width = image.shape[:2]
        self.regions: List[ExtractedRegion] = []
        self.edges = None
        self._preprocess()
    
    def _preprocess(self):
        """Pre-elaborazione dell'immagine per migliorare la segmentazione"""
        # Converti in grayscale
        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        
        # Applica bilateral filter per preservare i bordi riducendo il rumore
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Edge detection con Canny
        self.edges = cv2.Canny(filtered, 50, 150)
        
        # Dilata leggermente i bordi per chiuderli meglio
        kernel = np.ones((2, 2), np.uint8)
        self.edges = cv2.dilate(self.edges, kernel, iterations=1)
    
    def segment(self, n_colors: int = 40, min_area: int = 500) -> List[ExtractedRegion]:
        """Segmenta usando un approccio ibrido: K-Means + Edge Detection"""
        
        # Converti in LAB per miglior clustering dei colori
        lab = cv2.cvtColor(self.image, cv2.COLOR_BGR2LAB)
        pixels = lab.reshape((-1, 3)).astype(np.float32)
        
        # K-Means clustering
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(
            pixels, n_colors, None, criteria, 10, cv2.KMEANS_PP_CENTERS
        )
        
        # Ricostruisci immagine segmentata
        segmented = centers[labels.flatten()].reshape(self.image.shape).astype(np.uint8)
        segmented = cv2.cvtColor(segmented, cv2.COLOR_LAB2BGR)
        
        regions = []
        processed_masks = []  # Per evitare regioni duplicate
        
        for color_idx in range(n_colors):
            # Maschera per questo colore
            mask = (labels.flatten() == color_idx).reshape((self.height, self.width))
            mask = mask.astype(np.uint8) * 255
            
            # Applica operazioni morfologiche per pulire la maschera
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            
            # Sottrai i bordi rilevati per separare meglio le regioni
            mask = cv2.subtract(mask, self.edges)
            
            # Trova contorni
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < min_area:
                    continue
                
                # Verifica convessità e compattezza
                hull = cv2.convexHull(contour)
                hull_area = cv2.contourArea(hull)
                if hull_area > 0:
                    solidity = area / hull_area
                    if solidity < 0.3:  # Troppo frammentato
                        continue
                
                # Colore medio dalla regione originale
                mask_single = np.zeros((self.height, self.width), dtype=np.uint8)
                cv2.drawContours(mask_single, [contour], 0, 255, -1)
                mean_color = cv2.mean(self.image, mask=mask_single)[:3]
                b, g, r = mean_color
                
                # Filtra bianco/nero puro e grigio uniforme
                if min(r, g, b) > 235 or max(r, g, b) < 25:
                    continue
                if abs(r - g) < 10 and abs(g - b) < 10 and abs(r - b) < 10:
                    if r > 200 or r < 50:  # Grigio chiaro/scuro
                        continue
                
                # Semplifica contorno preservando la forma
                perimeter = cv2.arcLength(contour, True)
                epsilon = 0.002 * perimeter
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Assicurati minimo 4 punti
                if len(approx) < 4:
                    approx = contour
                
                # Centroide
                M = cv2.moments(contour)
                if M["m00"] <= 0:
                    continue
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
                
                x, y, w, h = cv2.boundingRect(contour)
                
                regions.append(ExtractedRegion(
                    contour=approx,
                    centroid=(float(cx), float(cy)),
                    area=float(area),
                    bbox=(x, y, w, h),
                    color=(int(b), int(g), int(r))
                ))
        
        # Rimuovi regioni duplicate o sovrapposte
        regions = self._remove_overlapping(regions)
        
        # Ordina per area
        regions.sort(key=lambda r: r.area, reverse=True)
        self.regions = regions
        return regions
    
    def _remove_overlapping(self, regions: List[ExtractedRegion], overlap_threshold: float = 0.7) -> List[ExtractedRegion]:
        """Rimuove regioni che si sovrappongono troppo"""
        if len(regions) <= 1:
            return regions
        
        # Ordina per area (tieni le più grandi)
        regions = sorted(regions, key=lambda r: r.area, reverse=True)
        keep = []
        
        for region in regions:
            is_duplicate = False
            for kept in keep:
                # Calcola IoU approssimato usando bounding box
                x1, y1, w1, h1 = region.bbox
                x2, y2, w2, h2 = kept.bbox
                
                # Intersezione
                xi = max(x1, x2)
                yi = max(y1, y2)
                wi = min(x1 + w1, x2 + w2) - xi
                hi = min(y1 + h1, y2 + h2) - yi
                
                if wi > 0 and hi > 0:
                    inter_area = wi * hi
                    union_area = w1 * h1 + w2 * h2 - inter_area
                    iou = inter_area / union_area if union_area > 0 else 0
                    
                    if iou > overlap_threshold:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                keep.append(region)
        
        return keep
    
    def segment_at_point(self, x: int, y: int, tolerance: int = 25) -> Optional[ExtractedRegion]:
        """Segmenta una regione partendo da un punto cliccato usando magic wand"""
        
        if not (0 <= x < self.width and 0 <= y < self.height):
            return None
        
        target_color = self.image[y, x].astype(np.float32)
        
        # Usa LAB per miglior matching dei colori
        lab_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2LAB).astype(np.float32)
        target_lab = cv2.cvtColor(np.uint8([[target_color]]), cv2.COLOR_BGR2LAB).astype(np.float32)[0, 0]
        
        # Calcola differenza colore per ogni pixel
        diff = np.sqrt(np.sum((lab_image - target_lab) ** 2, axis=2))
        
        # Crea maschera basata sulla tolleranza
        mask = (diff < tolerance * 2).astype(np.uint8) * 255
        
        # Flood fill per connettere solo regioni adiacenti
        flood_mask = np.zeros((self.height + 2, self.width + 2), np.uint8)
        cv2.floodFill(mask, flood_mask, (x, y), 255, 0, 0, cv2.FLOODFILL_MASK_ONLY)
        region_mask = flood_mask[1:-1, 1:-1]
        
        # Operazioni morfologiche
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        region_mask = cv2.morphologyEx(region_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(region_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None
        
        # Prendi il contorno che contiene il punto cliccato
        for contour in sorted(contours, key=cv2.contourArea, reverse=True):
            if cv2.pointPolygonTest(contour, (x, y), False) >= 0:
                largest = contour
                break
        else:
            largest = max(contours, key=cv2.contourArea)
        
        area = cv2.contourArea(largest)
        
        if area < 100:
            return None
        
        # Semplifica
        epsilon = 0.002 * cv2.arcLength(largest, True)
        approx = cv2.approxPolyDP(largest, epsilon, True)
        
        M = cv2.moments(largest)
        if M["m00"] > 0:
            cx = M["m10"] / M["m00"]
            cy = M["m01"] / M["m00"]
        else:
            return None
        
        bx, by, bw, bh = cv2.boundingRect(largest)
        
        return ExtractedRegion(
            contour=approx,
            centroid=(float(cx), float(cy)),
            area=float(area),
            bbox=(bx, by, bw, bh),
            color=tuple(int(c) for c in target_color[::-1])
        )
    
    def visualize(self, regions: List[ExtractedRegion] = None) -> np.ndarray:
        """Crea visualizzazione con overlay colorati"""
        
        if regions is None:
            regions = self.regions
        
        overlay = self.image.copy()
        
        np.random.seed(42)
        colors = [
            (np.random.randint(100, 255), np.random.randint(100, 255), np.random.randint(100, 255))
            for _ in range(max(len(regions), 1))
        ]
        
        for i, region in enumerate(regions):
            color = colors[i % len(colors)]
            cv2.drawContours(overlay, [region.contour], -1, color, -1)
            cv2.drawContours(overlay, [region.contour], -1, (255, 255, 255), 2)
            
            cx, cy = int(region.centroid[0]), int(region.centroid[1])
            cv2.circle(overlay, (cx, cy), 6, (0, 0, 0), -1)
            cv2.circle(overlay, (cx, cy), 4, (255, 255, 0), -1)
            
            label = region.name or f"R{i+1}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(overlay, (cx - tw//2 - 3, cy - 28), (cx + tw//2 + 3, cy - 12), (0, 0, 0), -1)
            cv2.putText(overlay, label, (cx - tw//2, cy - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return cv2.addWeighted(self.image, 0.4, overlay, 0.6, 0)


# ==================== Georeferencing ====================

class Georeferencer:
    """Converte coordinate pixel in coordinate geografiche"""
    
    def __init__(self, width: int, height: int, bounds: Dict):
        self.width = width
        self.height = height
        self.north = bounds.get('north', 90)
        self.south = bounds.get('south', -90)
        self.east = bounds.get('east', 180)
        self.west = bounds.get('west', -180)
        
        self.lon_per_pixel = (self.east - self.west) / self.width
        self.lat_per_pixel = (self.north - self.south) / self.height
    
    def pixel_to_coord(self, x: int, y: int) -> Tuple[float, float]:
        lon = self.west + (x * self.lon_per_pixel)
        lat = self.north - (y * self.lat_per_pixel)
        return (round(lon, 6), round(lat, 6))
    
    def contour_to_coords(self, contour: np.ndarray) -> List[List[float]]:
        points = contour.reshape(-1, 2) if len(contour.shape) == 3 else contour
        coords = [list(self.pixel_to_coord(int(x), int(y))) for x, y in points]
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        return coords


# ==================== Territory Alignment ====================

class TerritoryAligner:
    """Allinea le regioni estratte ai confini geografici di riferimento"""
    
    def __init__(self, reference_geojson: Dict = None):
        self.reference_features = []
        if reference_geojson:
            self.load_reference(reference_geojson)
    
    def load_reference(self, geojson: Dict):
        """Carica dati di riferimento da GeoJSON"""
        if geojson.get('type') == 'FeatureCollection':
            self.reference_features = geojson.get('features', [])
        elif geojson.get('type') == 'Feature':
            self.reference_features = [geojson]
    
    def _polygon_centroid(self, coords: List) -> Tuple[float, float]:
        """Calcola il centroide di un poligono"""
        if not coords or not coords[0]:
            return (0, 0)
        
        ring = coords[0] if isinstance(coords[0][0], list) else coords
        n = len(ring)
        if n < 3:
            return (ring[0][0], ring[0][1]) if ring else (0, 0)
        
        cx = sum(p[0] for p in ring) / n
        cy = sum(p[1] for p in ring) / n
        return (cx, cy)
    
    def _polygon_bbox(self, coords: List) -> Tuple[float, float, float, float]:
        """Calcola bounding box [minx, miny, maxx, maxy]"""
        ring = coords[0] if isinstance(coords[0][0], list) else coords
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return (min(xs), min(ys), max(xs), max(ys))
    
    def _bbox_overlap(self, bb1: Tuple, bb2: Tuple) -> float:
        """Calcola sovrapposizione tra due bounding box"""
        xi = max(bb1[0], bb2[0])
        yi = max(bb1[1], bb2[1])
        xa = min(bb1[2], bb2[2])
        ya = min(bb1[3], bb2[3])
        
        if xi >= xa or yi >= ya:
            return 0.0
        
        inter_area = (xa - xi) * (ya - yi)
        area1 = (bb1[2] - bb1[0]) * (bb1[3] - bb1[1])
        area2 = (bb2[2] - bb2[0]) * (bb2[3] - bb2[1])
        
        return inter_area / min(area1, area2) if min(area1, area2) > 0 else 0
    
    def _distance(self, p1: Tuple, p2: Tuple) -> float:
        """Distanza euclidea tra due punti"""
        return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5
    
    def find_best_match(self, region_coords: List, threshold: float = 0.3) -> Optional[Dict]:
        """Trova la feature di riferimento che meglio corrisponde alla regione"""
        
        if not self.reference_features:
            return None
        
        region_centroid = self._polygon_centroid(region_coords)
        region_bbox = self._polygon_bbox(region_coords)
        
        best_match = None
        best_score = 0
        
        for feature in self.reference_features:
            geom = feature.get('geometry', {})
            geom_type = geom.get('type', '')
            
            if geom_type == 'Polygon':
                ref_coords = geom.get('coordinates', [[]])[0]
            elif geom_type == 'MultiPolygon':
                # Usa il poligono più grande
                polys = geom.get('coordinates', [])
                ref_coords = max(polys, key=lambda p: len(p[0]) if p else 0)[0] if polys else []
            else:
                continue
            
            if not ref_coords:
                continue
            
            ref_centroid = self._polygon_centroid([ref_coords])
            ref_bbox = self._polygon_bbox([ref_coords])
            
            # Score basato su:
            # 1. Vicinanza dei centroidi
            centroid_dist = self._distance(region_centroid, ref_centroid)
            max_dist = self._distance(
                (region_bbox[0], region_bbox[1]),
                (region_bbox[2], region_bbox[3])
            )
            centroid_score = max(0, 1 - centroid_dist / (max_dist + 0.001))
            
            # 2. Sovrapposizione bounding box
            overlap_score = self._bbox_overlap(region_bbox, ref_bbox)
            
            # 3. Similarità delle dimensioni
            region_area = (region_bbox[2] - region_bbox[0]) * (region_bbox[3] - region_bbox[1])
            ref_area = (ref_bbox[2] - ref_bbox[0]) * (ref_bbox[3] - ref_bbox[1])
            size_ratio = min(region_area, ref_area) / max(region_area, ref_area) if max(region_area, ref_area) > 0 else 0
            
            # Score combinato
            score = 0.4 * centroid_score + 0.4 * overlap_score + 0.2 * size_ratio
            
            if score > best_score and score >= threshold:
                best_score = score
                best_match = {
                    'feature': feature,
                    'score': score,
                    'ref_coords': ref_coords
                }
        
        return best_match
    
    def align_region(self, region_coords: List, snap_strength: float = 0.5) -> List:
        """
        Allinea una regione ai confini di riferimento.
        snap_strength: 0=nessun allineamento, 1=allineamento totale
        """
        
        match = self.find_best_match(region_coords)
        if not match:
            return region_coords
        
        ref_coords = match['ref_coords']
        score = match['score']
        
        # Interpolazione tra coordinate originali e riferimento
        # Più alto lo score, più ci fidiamo del riferimento
        effective_strength = snap_strength * score
        
        if effective_strength < 0.2:
            return region_coords
        
        # Se la differenza nel numero di punti è troppa, torna l'originale
        ring = region_coords[0] if isinstance(region_coords[0][0], list) else region_coords
        if abs(len(ring) - len(ref_coords)) > len(ring) * 2:
            return region_coords
        
        # Allineamento totale se score alto
        if score > 0.7 and snap_strength > 0.8:
            return [ref_coords + [ref_coords[0]]] if ref_coords[0] != ref_coords[-1] else [ref_coords]
        
        # Allineamento parziale: sposta ogni vertice verso il punto più vicino del riferimento
        aligned = []
        for point in ring:
            # Trova punto più vicino nel riferimento
            closest = min(ref_coords, key=lambda p: self._distance(point, p))
            
            # Interpola
            new_x = point[0] + (closest[0] - point[0]) * effective_strength
            new_y = point[1] + (closest[1] - point[1]) * effective_strength
            aligned.append([round(new_x, 6), round(new_y, 6)])
        
        # Chiudi il poligono
        if aligned and aligned[0] != aligned[-1]:
            aligned.append(aligned[0])
        
        return [aligned]
    
    def align_all(self, features: List[Dict], snap_strength: float = 0.5) -> List[Dict]:
        """Allinea tutte le feature ai confini di riferimento"""
        
        aligned_features = []
        
        for feature in features:
            geom = feature.get('geometry', {})
            if geom.get('type') != 'Polygon':
                aligned_features.append(feature)
                continue
            
            coords = geom.get('coordinates', [[]])
            aligned_coords = self.align_region(coords, snap_strength)
            
            aligned_feature = feature.copy()
            aligned_feature['geometry'] = {
                'type': 'Polygon',
                'coordinates': aligned_coords
            }
            aligned_features.append(aligned_feature)
        
        return aligned_features


# ==================== Helper Functions ====================

def image_to_base64(image: np.ndarray) -> str:
    _, buffer = cv2.imencode('.png', image)
    return base64.b64encode(buffer).decode('utf-8')


def region_to_dict(region: ExtractedRegion, idx: int) -> Dict:
    return {
        "id": idx,
        "name": region.name or f"Regione {idx + 1}",
        "area": region.area,
        "centroid": list(region.centroid),
        "bbox": list(region.bbox),
        "color": f"#{region.color[2]:02x}{region.color[1]:02x}{region.color[0]:02x}",
        "points": region.contour.reshape(-1, 2).tolist()
    }


# ==================== API Endpoints ====================

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve la pagina HTML principale"""
    html_path = Path(__file__).parent / "static" / "index.html"
    if html_path.exists():
        return HTMLResponse(content=html_path.read_text(encoding='utf-8'))
    return HTMLResponse(content="<h1>Frontend not found. Create static/index.html</h1>")


@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    """Carica un'immagine per l'elaborazione"""
    
    allowed = ["image/png", "image/jpeg", "image/jpg", "image/webp"]
    if file.content_type not in allowed:
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
    max_dim = 1200
    if max(width, height) > max_dim:
        scale = max_dim / max(width, height)
        thumb = cv2.resize(image, None, fx=scale, fy=scale)
    else:
        thumb = image
    
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


@app.post("/api/segment")
async def segment_image(req: SegmentRequest):
    """Esegue la segmentazione automatica"""
    
    if req.session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")
    
    session = sessions[req.session_id]
    segmenter = session["segmenter"]
    
    try:
        regions = segmenter.segment(n_colors=req.n_colors, min_area=req.min_area)
        session["regions"] = regions
        
        vis = segmenter.visualize(regions)
        
        return {
            "success": True,
            "num_regions": len(regions),
            "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
            "visualization": image_to_base64(vis)
        }
    except Exception as e:
        raise HTTPException(500, f"Errore segmentazione: {str(e)}")


@app.post("/api/segment-point")
async def segment_at_point(req: PointRequest):
    """Segmenta una regione cliccando un punto"""
    
    if req.session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")
    
    session = sessions[req.session_id]
    segmenter = session["segmenter"]
    regions = session["regions"]
    
    new_region = segmenter.segment_at_point(req.x, req.y)
    
    if new_region:
        regions.append(new_region)
        session["regions"] = regions
        
        vis = segmenter.visualize(regions)
        
        return {
            "success": True,
            "num_regions": len(regions),
            "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
            "visualization": image_to_base64(vis)
        }
    
    return {"success": False, "message": "Nessuna regione trovata in questo punto"}


@app.post("/api/delete-region/{region_id}")
async def delete_region(region_id: int, session_id: str):
    """Elimina una regione"""
    
    if session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")
    
    session = sessions[session_id]
    regions = session["regions"]
    
    if 0 <= region_id < len(regions):
        regions.pop(region_id)
        session["regions"] = regions
        
        vis = session["segmenter"].visualize(regions)
        
        return {
            "success": True,
            "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
            "visualization": image_to_base64(vis)
        }
    
    raise HTTPException(404, "Regione non trovata")


@app.post("/api/update-region")
async def update_region(req: UpdateRegionRequest):
    """Aggiorna i punti di una regione (editor poligoni)"""
    
    if req.session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")
    
    session = sessions[req.session_id]
    regions = session["regions"]
    
    if not (0 <= req.region_id < len(regions)):
        raise HTTPException(404, "Regione non trovata")
    
    # Aggiorna i punti del contorno
    new_contour = np.array(req.points, dtype=np.float32).reshape(-1, 1, 2)
    region = regions[req.region_id]
    region.contour = new_contour
    
    # Ricalcola centroid e area
    moments = cv2.moments(new_contour.astype(np.int32))
    if moments["m00"] != 0:
        region.centroid = (
            moments["m10"] / moments["m00"],
            moments["m01"] / moments["m00"]
        )
    region.area = cv2.contourArea(new_contour.astype(np.int32))
    
    # Ricalcola bounding box
    x, y, w, h = cv2.boundingRect(new_contour.astype(np.int32))
    region.bbox = (x, y, w, h)
    
    session["regions"] = regions
    
    vis = session["segmenter"].visualize(regions)
    
    return {
        "success": True,
        "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
        "visualization": image_to_base64(vis)
    }


@app.post("/api/export")
async def export_geojson(req: ExportRequest):
    """Esporta le regioni in formato GeoJSON"""
    
    if req.session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")
    
    session = sessions[req.session_id]
    regions = session["regions"]
    
    if not regions:
        raise HTTPException(400, "Nessuna regione da esportare")
    
    georef = Georeferencer(
        session["width"],
        session["height"],
        req.bounds.model_dump()
    )
    
    features = []
    for i, region in enumerate(regions):
        coords = georef.contour_to_coords(region.contour)
        
        name = region.name or f"Regione {i + 1}"
        if req.region_names and i in req.region_names:
            name = req.region_names[i]
        
        features.append({
            "type": "Feature",
            "properties": {
                "id": i,
                "name": name,
                "area_pixels": region.area,
                "color": f"#{region.color[2]:02x}{region.color[1]:02x}{region.color[0]:02x}"
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        })
    
    return {
        "type": "FeatureCollection",
        "properties": {
            "source": "Map to GeoJSON Converter",
            "bounds": req.bounds.model_dump()
        },
        "features": features
    }


@app.get("/api/presets")
async def get_presets():
    """Restituisce i preset geografici disponibili"""
    return {
        "italy": {"north": 47.1, "south": 35.5, "east": 18.5, "west": 6.6, "name": "Italia"},
        "europe": {"north": 71.5, "south": 34.5, "east": 40.0, "west": -25.0, "name": "Europa"},
        "world": {"north": 85.0, "south": -85.0, "east": 180.0, "west": -180.0, "name": "Mondo"},
        "usa": {"north": 49.5, "south": 24.5, "east": -66.5, "west": -125.0, "name": "USA"},
        "germany": {"north": 55.1, "south": 47.3, "east": 15.0, "west": 5.9, "name": "Germania"},
        "france": {"north": 51.1, "south": 41.3, "east": 9.6, "west": -5.2, "name": "Francia"},
        "spain": {"north": 43.8, "south": 36.0, "east": 4.3, "west": -9.3, "name": "Spagna"}
    }


@app.post("/api/align")
async def align_territories(req: AlignRequest):
    """
    Allinea le regioni estratte ai confini geografici di riferimento.
    Può usare GeoJSON fornito dall'utente o scaricare da Natural Earth.
    """
    
    if req.session_id not in sessions:
        raise HTTPException(404, "Sessione non trovata")
    
    session = sessions[req.session_id]
    regions = session["regions"]
    
    if not regions:
        raise HTTPException(400, "Nessuna regione da allineare")
    
    # Crea georeferencer per convertire pixel -> coordinate
    georef = Georeferencer(
        session["width"],
        session["height"],
        req.bounds.model_dump()
    )
    
    # Converti regioni in GeoJSON features
    features = []
    for i, region in enumerate(regions):
        coords = georef.contour_to_coords(region.contour)
        features.append({
            "type": "Feature",
            "properties": {"id": i, "name": region.name or f"Regione {i + 1}"},
            "geometry": {"type": "Polygon", "coordinates": [coords]}
        })
    
    # Se c'è un GeoJSON di riferimento, usa TerritoryAligner
    if req.reference_geojson:
        aligner = TerritoryAligner(req.reference_geojson)
        aligned_features = aligner.align_all(features, req.snap_strength)
        
        # Converti coordinate allineate in pixel e aggiorna le regioni
        for i, (feat, region) in enumerate(zip(aligned_features, regions)):
            aligned_coords = feat['geometry']['coordinates'][0]
            
            # Converti coord -> pixel
            new_points = []
            for lon, lat in aligned_coords[:-1]:  # Escludi ultimo punto (duplicato)
                px = (lon - georef.west) / georef.lon_per_pixel
                py = (georef.north - lat) / georef.lat_per_pixel
                new_points.append([px, py])
            
            if new_points:
                new_contour = np.array(new_points, dtype=np.float32).reshape(-1, 1, 2)
                region.contour = new_contour
                
                # Ricalcola proprietà
                moments = cv2.moments(new_contour.astype(np.int32))
                if moments["m00"] != 0:
                    region.centroid = (
                        moments["m10"] / moments["m00"],
                        moments["m01"] / moments["m00"]
                    )
                region.area = cv2.contourArea(new_contour.astype(np.int32))
                x, y, w, h = cv2.boundingRect(new_contour.astype(np.int32))
                region.bbox = (x, y, w, h)
        
        session["regions"] = regions
        vis = session["segmenter"].visualize(regions)
        
        return {
            "success": True,
            "message": f"Allineate {len(regions)} regioni al riferimento",
            "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
            "visualization": image_to_base64(vis),
            "aligned_geojson": {
                "type": "FeatureCollection",
                "features": aligned_features
            }
        }
    
    # Senza riferimento, restituisce le features convertite
    return {
        "success": True,
        "message": "Regioni convertite (nessun riferimento per allineamento)",
        "regions": [region_to_dict(r, i) for i, r in enumerate(regions)],
        "geojson": {
            "type": "FeatureCollection", 
            "features": features
        }
    }


@app.post("/api/upload-reference")
async def upload_reference_geojson(file: UploadFile = File(...)):
    """Carica un file GeoJSON di riferimento per l'allineamento"""
    
    if not file.filename.endswith(('.geojson', '.json')):
        raise HTTPException(400, "Il file deve essere GeoJSON (.geojson o .json)")
    
    try:
        content = await file.read()
        geojson = json.loads(content.decode('utf-8'))
        
        # Valida la struttura
        if geojson.get('type') not in ['FeatureCollection', 'Feature']:
            raise HTTPException(400, "GeoJSON non valido: deve essere Feature o FeatureCollection")
        
        features = geojson.get('features', [geojson]) if geojson.get('type') == 'FeatureCollection' else [geojson]
        
        return {
            "success": True,
            "filename": file.filename,
            "num_features": len(features),
            "geojson": geojson
        }
    except json.JSONDecodeError:
        raise HTTPException(400, "File JSON non valido")
    except Exception as e:
        raise HTTPException(500, f"Errore nel parsing del GeoJSON: {str(e)}")


@app.delete("/api/session/{session_id}")
async def delete_session(session_id: str):
    """Elimina una sessione e i file temporanei"""
    
    if session_id in sessions:
        try:
            os.remove(sessions[session_id]["file_path"])
        except:
            pass
        del sessions[session_id]
    
    return {"success": True}


# Serve static files
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


if __name__ == "__main__":
    import uvicorn
    print("\n🗺️  Map to GeoJSON Web App")
    print("   Apri http://localhost:8000 nel browser\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
