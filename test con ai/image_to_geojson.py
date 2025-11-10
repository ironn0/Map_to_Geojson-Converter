"""
AI Map Extractor - Converte immagini di mappe in GeoJSON
Versione 1.0 - Usa Computer Vision (OpenCV) senza modelli pesanti
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import List, Tuple, Dict
import argparse

class MapExtractor:
    def __init__(self, image_path: str):
        """Inizializza l'estrattore con un'immagine"""
        self.image_path = Path(image_path)
        self.image = cv2.imread(str(self.image_path))
        if self.image is None:
            raise ValueError(f"Impossibile caricare immagine: {image_path}")
        
        self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        self.height, self.width = self.image.shape[:2]
        self.regions = []
        
        print(f"✅ Immagine caricata: {self.width}x{self.height}px")
    
    def preprocess(self):
        """Preprocessa l'immagine per migliorare il rilevamento"""
        print("🔄 Preprocessing immagine...")
        
        # Riduzione rumore
        self.gray = cv2.GaussianBlur(self.gray, (5, 5), 0)
        
        # Aumento contrasto
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        self.gray = clahe.apply(self.gray)
        
        # Binarizzazione adattiva
        self.binary = cv2.adaptiveThreshold(
            self.gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        print("✅ Preprocessing completato")
    
    def detect_regions(self, min_area: int = 1000, max_area: int = None):
        """Rileva regioni/confini usando contour detection"""
        print("🔍 Rilevamento regioni...")
        
        if max_area is None:
            max_area = self.width * self.height * 0.8
        
        # Trova contorni
        contours, hierarchy = cv2.findContours(
            self.binary, 
            cv2.RETR_TREE, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        print(f"   Trovati {len(contours)} contorni")
        
        # Filtra contorni validi
        valid_regions = []
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            
            if min_area <= area <= max_area:
                # Semplifica il contorno
                epsilon = 0.005 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # Converti in lista di punti
                points = [(int(p[0][0]), int(p[0][1])) for p in approx]
                
                # Calcola centroide
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                else:
                    cx, cy = points[0]
                
                valid_regions.append({
                    'id': f'region_{i}',
                    'pixels': points,
                    'area': area,
                    'centroid': (cx, cy),
                    'bounds': cv2.boundingRect(contour)
                })
        
        self.regions = valid_regions
        print(f"✅ Rilevate {len(valid_regions)} regioni valide")
        
        return valid_regions
    
    def calibrate_manual(self):
        """Calibrazione manuale con input utente"""
        print("\n🎯 CALIBRAZIONE GEOGRAFICA")
        print("="*60)
        print("Devi fornire le coordinate geografiche dell'area della mappa:\n")
        
        try:
            lat_min = float(input("Latitudine minima (sud):  "))
            lat_max = float(input("Latitudine massima (nord): "))
            lon_min = float(input("Longitudine minima (ovest): "))
            lon_max = float(input("Longitudine massima (est):  "))
            
            self.calibration = {
                'lat_range': (lat_min, lat_max),
                'lon_range': (lon_min, lon_max)
            }
            
            print(f"\n✅ Calibrazione salvata:")
            print(f"   Lat: {lat_min}° → {lat_max}°")
            print(f"   Lon: {lon_min}° → {lon_max}°")
            
            return True
            
        except ValueError:
            print("❌ Errore: inserisci numeri validi")
            return False
    
    def pixel_to_latlon(self, x: int, y: int) -> Tuple[float, float]:
        """Converte coordinate pixel in lat/lon"""
        if not hasattr(self, 'calibration'):
            raise ValueError("Calibrazione non effettuata!")
        
        lat_min, lat_max = self.calibration['lat_range']
        lon_min, lon_max = self.calibration['lon_range']
        
        # Normalizza coordinate pixel
        x_norm = x / self.width
        y_norm = y / self.height
        
        # Converti in coordinate geografiche (Y invertita)
        lon = lon_min + x_norm * (lon_max - lon_min)
        lat = lat_max - y_norm * (lat_max - lat_min)
        
        return (lon, lat)
    
    def to_geojson(self, output_path: str = None) -> Dict:
        """Esporta regioni in formato GeoJSON"""
        print("\n📝 Creazione GeoJSON...")
        
        if not hasattr(self, 'calibration'):
            print("⚠️  Nessuna calibrazione, uso coordinate pixel")
            use_geo = False
        else:
            use_geo = True
        
        features = []
        
        for region in self.regions:
            # Converti coordinate
            if use_geo:
                coordinates = [
                    list(self.pixel_to_latlon(x, y)) 
                    for x, y in region['pixels']
                ]
            else:
                coordinates = [[x, y] for x, y in region['pixels']]
            
            # Chiudi il poligono
            if coordinates and coordinates[0] != coordinates[-1]:
                coordinates.append(coordinates[0])
            
            # Crea feature GeoJSON
            feature = {
                "type": "Feature",
                "properties": {
                    "id": region['id'],
                    "area_pixels": region['area'],
                    "centroid_x": region['centroid'][0],
                    "centroid_y": region['centroid'][1]
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coordinates]
                }
            }
            
            features.append(feature)
        
        # Crea FeatureCollection
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Salva file
        if output_path is None:
            output_path = self.image_path.with_suffix('.geojson')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        
        print(f"✅ GeoJSON salvato: {output_path}")
        print(f"   {len(features)} regioni esportate")
        
        return geojson
    
    def visualize(self, show: bool = True, save: bool = True):
        """Visualizza le regioni rilevate"""
        print("\n🎨 Creazione visualizzazione...")
        
        # Copia immagine originale
        vis = self.image.copy()
        
        # Disegna ogni regione con colore casuale
        for i, region in enumerate(self.regions):
            color = tuple(np.random.randint(0, 255, 3).tolist())
            
            # Disegna contorno
            points = np.array(region['pixels'], dtype=np.int32)
            cv2.polylines(vis, [points], True, color, 2)
            
            # Disegna centroide
            cx, cy = region['centroid']
            cv2.circle(vis, (cx, cy), 5, color, -1)
            
            # Etichetta
            cv2.putText(vis, region['id'], (cx+10, cy), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        if save:
            output_path = self.image_path.with_name(
                self.image_path.stem + '_detected.png'
            )
            cv2.imwrite(str(output_path), vis)
            print(f"✅ Visualizzazione salvata: {output_path}")
        
        if show:
            cv2.imshow('Regioni Rilevate', vis)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        
        return vis


def main():
    parser = argparse.ArgumentParser(
        description='Estrae confini da immagini di mappe e crea GeoJSON'
    )
    parser.add_argument('image', help='Path immagine mappa (PNG, JPG)')
    parser.add_argument('-o', '--output', help='Path output GeoJSON')
    parser.add_argument('--min-area', type=int, default=1000, 
                       help='Area minima regione (pixel²)')
    parser.add_argument('--no-calibration', action='store_true',
                       help='Salta calibrazione geografica')
    parser.add_argument('--no-viz', action='store_true',
                       help='Non mostrare visualizzazione')
    
    args = parser.parse_args()
    
    print("\n🗺️  AI MAP EXTRACTOR")
    print("="*60)
    
    try:
        # Carica ed elabora immagine
        extractor = MapExtractor(args.image)
        extractor.preprocess()
        extractor.detect_regions(min_area=args.min_area)
        
        # Calibrazione geografica
        if not args.no_calibration:
            if not extractor.calibrate_manual():
                print("\n⚠️  Continuo senza calibrazione geografica")
        
        # Esporta GeoJSON
        extractor.to_geojson(args.output)
        
        # Visualizza
        if not args.no_viz:
            extractor.visualize(show=False, save=True)
        
        print("\n✅ Processo completato!")
        print("🌐 Testa il GeoJSON su: http://geojson.io")
        
    except Exception as e:
        print(f"\n❌ Errore: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Se eseguito senza argomenti, modalità interattiva
    import sys
    if len(sys.argv) == 1:
        print("\n🗺️  AI MAP EXTRACTOR - Modalità Interattiva")
        print("="*60)
        
        image_path = input("\n📁 Path immagine mappa: ").strip('"')
        
        try:
            extractor = MapExtractor(image_path)
            extractor.preprocess()
            extractor.detect_regions()
            
            # Chiedi calibrazione
            resp = input("\n🎯 Vuoi calibrare geograficamente? (s/n): ")
            if resp.lower() == 's':
                extractor.calibrate_manual()
            
            extractor.to_geojson()
            extractor.visualize(show=False, save=True)
            
            print("\n✅ Completato!")
            
        except Exception as e:
            print(f"❌ Errore: {e}")
    else:
        main()