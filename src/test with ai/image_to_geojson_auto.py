"""
Map to GeoJSON - Segmentazione per COLORE
Usa K-Means clustering per raggruppare pixel simili
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict


class KMeansExtractor:
    def __init__(self, image_path: str):
        self.image_path = Path(image_path)
        self.image = cv2.imread(str(self.image_path))
        if self.image is None:
            raise ValueError(f"Impossibile caricare: {image_path}")
        
        self.height, self.width = self.image.shape[:2]
        self.regions = []
        
        print(f"✅ Immagine: {self.width}x{self.height}px")
    
    def segment_by_color(self, n_colors: int = 25, min_area: int = 2000):
        """Segmenta l'immagine in regioni di colore usando K-Means"""
        print(f"\n🎨 Segmentazione in {n_colors} colori...")
        
        # 1. Reshape immagine per K-Means
        pixels = self.image.reshape((-1, 3))
        pixels = np.float32(pixels)
        
        # 2. K-Means clustering
        print("   Clustering colori (può richiedere 10-20 sec)...")
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(
            pixels, 
            n_colors, 
            None, 
            criteria, 
            10, 
            cv2.KMEANS_PP_CENTERS
        )
        
        # 3. Crea immagine segmentata
        centers = np.uint8(centers)
        segmented = centers[labels.flatten()]
        segmented = segmented.reshape(self.image.shape)
        
        print("   ✅ Segmentazione completata")
        
        # 4. Per ogni colore, trova regioni connesse
        print("\n🔍 Rilevamento regioni per colore...")
        
        candidates = []
        
        for color_idx in range(n_colors):
            # Crea maschera per questo colore
            mask = (labels.flatten() == color_idx).reshape((self.height, self.width))
            mask = mask.astype(np.uint8) * 255
            
            # Trova contorni
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                if area < min_area:
                    continue
                
                # Colore medio reale (non cluster)
                mask_single = np.zeros((self.height, self.width), dtype=np.uint8)
                cv2.drawContours(mask_single, [contour], 0, 255, -1)
                mean_color_bgr = cv2.mean(self.image, mask=mask_single)[:3]
                b, g, r = mean_color_bgr
                
                # FILTRI
                # Escludi acqua azzurra
                if b > 200 and g > 150 and r < 180:
                    continue
                
                # Escludi bianco/grigio
                if min(r, g, b) > 215:
                    continue
                
                # Escludi nero
                if max(r, g, b) < 50:
                    continue
                
                # Semplifica contorno
                epsilon = 0.001 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                points = [(int(p[0][0]), int(p[0][1])) for p in approx]
                
                # Centroide
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = points[0]
                
                candidates.append({
                    'approx': points,
                    'area': area,
                    'centroid': (cx, cy),
                    'color': (int(r), int(g), int(b)),
                    'contour': contour
                })
                
                print(f"   Regione: {area:.0f}px² - RGB({int(r)},{int(g)},{int(b)})")
        
        # 5. Ordina per area
        candidates.sort(key=lambda x: x['area'], reverse=True)
        
        # 6. Rimuovi sovrapposizioni
        final_regions = []
        
        for candidate in candidates[:30]:  # Max 30 regioni
            # Controlla sovrapposizione
            is_duplicate = False
            cx1, cy1 = candidate['centroid']
            
            for existing in final_regions:
                # Se centroide dentro altra regione
                result = cv2.pointPolygonTest(existing['contour'], (float(cx1), float(cy1)), False)
                if result >= 0:
                    is_duplicate = True
                    break
                
                # Se aree si sovrappongono > 80%
                mask1 = np.zeros((self.height, self.width), dtype=np.uint8)
                mask2 = np.zeros((self.height, self.width), dtype=np.uint8)
                cv2.drawContours(mask1, [candidate['contour']], 0, 255, -1)
                cv2.drawContours(mask2, [existing['contour']], 0, 255, -1)
                
                overlap = np.logical_and(mask1, mask2).sum()
                if overlap > 0.8 * min(candidate['area'], existing['area']):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                r, g, b = candidate['color']
                final_regions.append({
                    'id': f'region_{len(final_regions)}',
                    'pixels': candidate['approx'],
                    'area': candidate['area'],
                    'centroid': candidate['centroid'],
                    'color': f'rgb({r},{g},{b})',
                    'contour': candidate['contour']
                })
        
        self.regions = final_regions
        print(f"\n✅ {len(final_regions)} regioni finali")
        
        # Salva immagine segmentata per debug
        debug_path = self.image_path.with_name(self.image_path.stem + '_segmented.png')
        cv2.imwrite(str(debug_path), segmented)
        print(f"   Debug: {debug_path}")
        
        return final_regions
    
    def calibrate_italy(self):
        """Calibrazione Italia"""
        self.calibration = {
            'lat_range': (36.0, 47.5),
            'lon_range': (6.5, 18.5)
        }
        print("\n🇮🇹 Calibrazione Italia: Lat 36.0-47.5°, Lon 6.5-18.5°")
    
    def calibrate_manual(self):
        """Calibrazione manuale"""
        print("\n🎯 CALIBRAZIONE MANUALE")
        try:
            lat_min = float(input("Lat min [36.0]: ") or "36.0")
            lat_max = float(input("Lat max [47.5]: ") or "47.5")
            lon_min = float(input("Lon min [6.5]: ") or "6.5")
            lon_max = float(input("Lon max [18.5]: ") or "18.5")
            
            self.calibration = {
                'lat_range': (lat_min, lat_max),
                'lon_range': (lon_min, lon_max)
            }
            print("✅ Calibrato")
            return True
        except:
            return False
    
    def pixel_to_latlon(self, x: int, y: int) -> Tuple[float, float]:
        """Pixel → Lat/Lon"""
        if not hasattr(self, 'calibration'):
            return (x, y)
        
        lat_min, lat_max = self.calibration['lat_range']
        lon_min, lon_max = self.calibration['lon_range']
        
        lon = lon_min + (x / self.width) * (lon_max - lon_min)
        lat = lat_max - (y / self.height) * (lat_max - lat_min)
        
        return (lon, lat)
    
    def to_geojson(self, output_path: str = None) -> Dict:
        """Esporta GeoJSON"""
        print("\n📝 Creazione GeoJSON...")
        
        use_geo = hasattr(self, 'calibration')
        features = []
        
        for region in self.regions:
            if use_geo:
                coordinates = [list(self.pixel_to_latlon(x, y)) for x, y in region['pixels']]
            else:
                coordinates = [[x, y] for x, y in region['pixels']]
            
            if coordinates and coordinates[0] != coordinates[-1]:
                coordinates.append(coordinates[0])
            
            feature = {
                "type": "Feature",
                "properties": {
                    "id": region['id'],
                    "color": region['color'],
                    "area_pixels": region['area']
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coordinates]
                }
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        if output_path is None:
            output_path = self.image_path.with_suffix('.geojson')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        
        print(f"✅ GeoJSON: {output_path} ({len(features)} regioni)")
        
        if use_geo:
            lons = [c[0] for f in features for c in f['geometry']['coordinates'][0]]
            lats = [c[1] for f in features for c in f['geometry']['coordinates'][0]]
            print(f"   Lat: {min(lats):.2f}° → {max(lats):.2f}°")
            print(f"   Lon: {min(lons):.2f}° → {max(lons):.2f}°")
        
        return geojson
    
    def visualize(self, save: bool = True):
        """Visualizza regioni"""
        print("\n🎨 Visualizzazione...")
        
        vis = self.image.copy()
        np.random.seed(42)
        
        for region in self.regions:
            color = tuple(np.random.randint(50, 255, 3).tolist())
            points = np.array(region['pixels'], dtype=np.int32)
            
            cv2.polylines(vis, [points], True, color, 3)
            
            cx, cy = region['centroid']
            cv2.circle(vis, (cx, cy), 8, color, -1)
            cv2.circle(vis, (cx, cy), 10, (0, 0, 0), 2)
            
            cv2.putText(vis, region['id'], (cx + 15, cy),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 4)
            cv2.putText(vis, region['id'], (cx + 15, cy),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        if save:
            output = self.image_path.with_name(self.image_path.stem + '_regions.png')
            cv2.imwrite(str(output), vis)
            print(f"✅ Immagine: {output}")
        
        return vis


def main():
    print("\n🗺️  MAP TO GEOJSON - K-Means Clustering")
    print("="*60)
    print("Segmentazione intelligente per colore\n")
    
    image_path = input("📁 Immagine: ").strip('"')
    
    try:
        extractor = KMeansExtractor(image_path)
        
        # Segmenta per colore
        extractor.segment_by_color(
            n_colors=25,        # Numero cluster colori
            min_area=2000       # Area minima regione
        )
        
        if not extractor.regions:
            print("\n❌ Nessuna regione trovata!")
            print("   Prova ad aumentare n_colors o abbassare min_area")
            return
        
        # Calibrazione
        print("\n" + "="*60)
        mode = input("🎯 [1] Italia, [2] Manuale, [3] Skip: ").strip()
        
        if mode == '1':
            extractor.calibrate_italy()
        elif mode == '2':
            extractor.calibrate_manual()
        
        # Esporta
        extractor.to_geojson()
        extractor.visualize()
        
        print("\n" + "="*60)
        print("✅ COMPLETATO!")
        print("="*60)
        print("\n🌐 Testa su: http://geojson.io")
        
    except Exception as e:
        print(f"\n❌ Errore: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()