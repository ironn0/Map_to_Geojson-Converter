"""
🔍 MapSegmenter Module
Classe principale per la segmentazione delle immagini di mappe

Author: Map to GeoJSON Converter Project
"""

from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from config import ROBUST_SEGMENTATION_DEFAULTS
from models import ExtractedRegion


class MapSegmenter:
    """Motore di segmentazione avanzato con edge detection e watershed"""
    
    def __init__(self, image: np.ndarray):
        self.image = image
        self.height, self.width = image.shape[:2]
        self.regions: List[ExtractedRegion] = []
        self.edges = None
        self.last_profile = "legacy"
        self._preprocess()
    
    def _preprocess(self):
        """Pre-elaborazione legacy per compatibilita retroattiva."""
        # Converti in grayscale
        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        
        # Applica bilateral filter per preservare i bordi riducendo il rumore
        filtered = cv2.bilateralFilter(gray, 9, 75, 75)
        
        # Edge detection con Canny
        self.edges = cv2.Canny(filtered, 50, 150)
        
        # Dilata leggermente i bordi per chiuderli meglio
        kernel = np.ones((2, 2), np.uint8)
        self.edges = cv2.dilate(self.edges, kernel, iterations=1)

    def _compute_text_suppression_mask(self, gray: np.ndarray) -> np.ndarray:
        """
        Euristica leggera per ridurre etichette testuali:
        usa black-hat + componenti piccole ad alto contrasto.
        """
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 13))
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
        _, binary = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        mask = np.zeros_like(gray, dtype=np.uint8)
        for idx in range(1, num_labels):
            x, y, w, h, area = stats[idx]
            if area < 8:
                continue
            # Candidate testo: componenti allungate e piccole.
            elongation = max(w, h) / max(min(w, h), 1)
            if area <= 600 and elongation >= 2.5:
                mask[labels == idx] = 255
        return cv2.dilate(mask, np.ones((2, 2), np.uint8), iterations=1)

    def _prepare_robust_inputs(self, robust_settings: Dict) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Pipeline robusta per mappe rumorose/storiche/scansionate."""
        denoise_strength = float(robust_settings["denoise_strength"])
        clahe_clip = float(robust_settings["clahe_clip_limit"])
        block_size = int(robust_settings["adaptive_block_size"])
        adaptive_c = float(robust_settings["adaptive_c"])
        morphology_kernel = max(1, int(robust_settings["morphology_kernel"]))
        text_suppression = bool(robust_settings["text_suppression"])

        if block_size % 2 == 0:
            block_size += 1

        gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, None, denoise_strength, 7, 21)

        clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(8, 8))
        normalized = clahe.apply(denoised)

        adaptive = cv2.adaptiveThreshold(
            normalized,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            block_size,
            adaptive_c,
        )
        adaptive = cv2.medianBlur(adaptive, 3)

        edges = cv2.Canny(normalized, 40, 140)
        edges = cv2.bitwise_or(edges, cv2.bitwise_not(adaptive))
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (morphology_kernel, morphology_kernel))
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        edges = cv2.dilate(edges, np.ones((2, 2), np.uint8), iterations=1)

        text_mask = np.zeros_like(gray, dtype=np.uint8)
        if text_suppression:
            text_mask = self._compute_text_suppression_mask(normalized)

        enhanced = cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR)
        return enhanced, edges, text_mask

    def segment(
        self,
        n_colors: int = 40,
        min_area: int = 500,
        robust_mode: bool = False,
        robust_settings: Optional[Dict] = None,
    ) -> List[ExtractedRegion]:
        """Segmenta usando K-Means + edge masking con profilo legacy/robust."""
        profile_cfg = dict(ROBUST_SEGMENTATION_DEFAULTS)
        if robust_mode:
            if robust_settings:
                profile_cfg.update(robust_settings)
            source_image, edges, text_mask = self._prepare_robust_inputs(profile_cfg)
            self.last_profile = "robust"
        else:
            source_image = self.image
            edges = self.edges
            text_mask = np.zeros((self.height, self.width), dtype=np.uint8)
            self.last_profile = "legacy"

        # Converti in LAB per miglior clustering dei colori
        lab = cv2.cvtColor(source_image, cv2.COLOR_BGR2LAB)
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
            mask = cv2.subtract(mask, edges)
            if robust_mode:
                mask = cv2.subtract(mask, text_mask)
                artifact_min_component_area = int(profile_cfg.get("artifact_min_component_area", 0))
                if artifact_min_component_area > 0:
                    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
                    cleaned = np.zeros_like(mask, dtype=np.uint8)
                    for idx in range(1, num_labels):
                        area = stats[idx, cv2.CC_STAT_AREA]
                        if area >= artifact_min_component_area:
                            cleaned[labels == idx] = 255
                    mask = cleaned
            
            # Trova contorni
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                region = self._process_contour(contour, min_area, profile_cfg)
                if region:
                    regions.append(region)
        
        # Rimuovi regioni duplicate o sovrapposte
        regions = self._remove_overlapping(regions)
        
        # Ordina per area
        regions.sort(key=lambda r: r.area, reverse=True)
        self.regions = regions
        return regions
    
    def _process_contour(
        self,
        contour: np.ndarray,
        min_area: int,
        profile_cfg: Optional[Dict] = None,
    ) -> Optional[ExtractedRegion]:
        """Processa un singolo contorno e crea una regione"""
        contour_cfg = profile_cfg or ROBUST_SEGMENTATION_DEFAULTS
        area = cv2.contourArea(contour)
        if area < min_area:
            return None
        
        # Verifica convessità e compattezza
        hull = cv2.convexHull(contour)
        hull_area = cv2.contourArea(hull)
        if hull_area > 0:
            solidity = area / hull_area
            solidity_min = float(contour_cfg.get("contour_solidity_min", 0.3))
            if solidity < solidity_min:  # Troppo frammentato
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
        epsilon_scale = float(contour_cfg.get("contour_smoothing_epsilon_scale", 0.002))
        epsilon = epsilon_scale * perimeter
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        min_points = int(contour_cfg.get("contour_min_points", 4))
        if len(approx) < min_points:
            approx = contour
        if len(approx) < min_points:
            return None
        
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
            color=tuple(int(c) for c in target_color)
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
            contour = np.asarray(region.contour)
            if contour.size == 0:
                continue

            if contour.ndim == 2 and contour.shape[1] == 2:
                contour = contour.reshape(-1, 1, 2)
            elif contour.ndim != 3 or contour.shape[-2:] != (1, 2):
                continue

            if not np.isfinite(contour).all() or contour.shape[0] < 3:
                continue

            contour_i32 = np.round(contour).astype(np.int32)

            cv2.drawContours(overlay, [contour_i32], -1, color, -1)
            cv2.drawContours(overlay, [contour_i32], -1, (255, 255, 255), 2)
            
            cx, cy = int(region.centroid[0]), int(region.centroid[1])
            cv2.circle(overlay, (cx, cy), 6, (0, 0, 0), -1)
            cv2.circle(overlay, (cx, cy), 4, (255, 255, 0), -1)
            
            label = region.name or f"R{i+1}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(overlay, (cx - tw//2 - 3, cy - 28), (cx + tw//2 + 3, cy - 12), (0, 0, 0), -1)
            cv2.putText(overlay, label, (cx - tw//2, cy - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return cv2.addWeighted(self.image, 0.4, overlay, 0.6, 0)
