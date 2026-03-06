"""
🔍 MapSegmenter Module
Classe principale per la segmentazione delle immagini di mappe

Author: Map to GeoJSON Converter Project
"""

import numpy as np
import cv2
from typing import List, Optional, Tuple
from models import ExtractedRegion


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
                region = self._process_contour(contour, min_area)
                if region:
                    regions.append(region)
        
        # Rimuovi regioni duplicate o sovrapposte
        regions = self._remove_overlapping(regions)
        
        # Ordina per area
        regions.sort(key=lambda r: r.area, reverse=True)
        self.regions = regions
        return regions
    
    def _process_contour(self, contour: np.ndarray, min_area: int) -> Optional[ExtractedRegion]:
        """Processa un singolo contorno e crea una regione"""
        area = cv2.contourArea(contour)
        if area < min_area:
            return None
        
        # Verifica convessità e compattezza
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        if hull_area > 0:
            solidity = area / hull_area
            if solidity < 0.3:  # Troppo frammentato
                return None
        
        # Colore medio dalla regione originale
        mask_single = np.zeros((self.height, self.width), dtype=np.uint8)
        cv2.drawContours(mask_single, [contour], 0, 255, -1)
        mean_color = cv2.mean(self.image, mask=mask_single)[:3]
        b, g, r = mean_color
        
        # Filtra bianco/nero puro e grigio uniforme
        if min(r, g, b) > 235 or max(r, g, b) < 25:
            return None
        if abs(r - g) < 10 and abs(g - b) < 10 and abs(r - b) < 10:
            if r > 200 or r < 50:  # Grigio chiaro/scuro
                return None
        
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
            return None
        cx = M["m10"] / M["m00"]
        cy = M["m01"] / M["m00"]
        
        x, y, w, h = cv2.boundingRect(contour)
        
        return ExtractedRegion(
            contour=approx,
            centroid=(float(cx), float(cy)),
            area=float(area),
            bbox=(x, y, w, h),
            color=(int(b), int(g), int(r))
        )
    
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
