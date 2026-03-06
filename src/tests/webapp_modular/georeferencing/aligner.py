"""
🎯 Territory Aligner Module
Allinea le regioni estratte ai confini geografici di riferimento

Author: Map to GeoJSON Converter Project
"""

from typing import Dict, List, Optional, Tuple


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
