"""
Shape Matcher - Confronta forme estratte con database geografico mondiale
Riconosce automaticamente regioni/paesi confrontando geometrie
"""

import cv2
import numpy as np
import json
import urllib.request
import zipfile
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from shapely.geometry import Polygon, MultiPolygon, shape, mapping
from shapely.ops import unary_union
from scipy.spatial import distance
import geopandas as gpd


class ShapeMatcher:
    def __init__(self, database_path: str = None, use_gadm_italy: bool = True):
        """Inizializza il matcher con database mondiale (o GADM Italy per regioni)"""
        self.use_gadm_italy = use_gadm_italy
        self.database_path = database_path or self._get_database_path()
        self.world_shapes = None
        self.italy_regions = None
        self.load_database()
        
        # Carica GADM Italy se richiesto
        if use_gadm_italy:
            self._load_gadm_italy()
    
    def _get_database_path(self) -> Path:
        """Ottiene path database (scarica se necessario)"""
        base_dir = Path(__file__).parent
        db_dir = base_dir / "geodata"
        db_dir.mkdir(exist_ok=True)
        
        shapefile = db_dir / "ne_10m_admin_1_states_provinces" / "ne_10m_admin_1_states_provinces.shp"
        
        if not shapefile.exists():
            print("\n📥 Download database mondiale (Natural Earth)...")
            print("   Questo può richiedere alcuni minuti...")
            self._download_naturalearth(db_dir)
        
        return shapefile
    
    def _download_naturalearth(self, target_dir: Path):
        """Scarica Natural Earth database (stati/province/regioni mondiali)"""
        # Natural Earth - Admin 1 (stati/province/regioni) - URL corretto
        # Nota: per l'Italia include sia regioni che province, prioritizziamo regioni
        url = "https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip"
        
        zip_path = target_dir / "ne_admin.zip"
        
        try:
            print(f"   Download da: {url}")
            
            # Aggiungi User-Agent per evitare 406 error
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            with urllib.request.urlopen(req) as response, open(zip_path, 'wb') as out_file:
                total_size = int(response.headers.get('Content-Length', 0))
                downloaded = 0
                chunk_size = 8192
                
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\r   Progresso: {progress:.1f}%", end='', flush=True)
                
                print()  # Newline dopo progresso
            
            print("   Estrazione...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir / "ne_10m_admin_1_states_provinces")
            
            zip_path.unlink()  # Rimuovi zip
            print("   ✅ Database scaricato")
            
        except Exception as e:
            print(f"   ❌ Errore download: {e}")
            print("\n   💡 ALTERNATIVA MANUALE:")
            print("   1. Vai su: https://www.naturalearthdata.com/downloads/10m-cultural-vectors/")
            print("   2. Scarica: 'Admin 1 – States, Provinces'")
            print("   3. Estrai in: " + str(target_dir))
            raise
    
    def load_database(self):
        """Carica shapefile mondiale"""
        print(f"\n🗺️  Caricamento database mondiale...")
        
        try:
            self.world_shapes = gpd.read_file(str(self.database_path))
            print(f"   ✅ {len(self.world_shapes)} regioni/stati caricati")
            print(f"   📍 Copertura: {', '.join(self.world_shapes['admin'].unique()[:5])}...")
            
        except Exception as e:
            print(f"   ❌ Errore caricamento: {e}")
            raise
    
    def _load_gadm_italy(self):
        """Carica database GADM Italy (regioni ufficiali)"""
        base_dir = Path(__file__).parent
        gadm_shapefile = base_dir / "geodata" / "gadm_italy" / "gadm41_ITA_1.shp"
        
        if not gadm_shapefile.exists():
            print("\n💡 Database regioni italiane non trovato")
            print("   Esegui: python download_gadm.py")
            print("   Oppure usa Natural Earth (meno preciso)")
            return
        
        try:
            self.italy_regions = gpd.read_file(str(gadm_shapefile))
            print(f"\n🇮🇹 Database GADM Italy caricato")
            print(f"   ✅ {len(self.italy_regions)} regioni italiane ufficiali")
        except Exception as e:
            print(f"   ⚠️ Errore caricamento GADM Italy: {e}")
            self.italy_regions = None
    
    def extract_features_from_image(self, image_path: str, n_colors: int = 60, min_area: int = 300) -> List[Dict]:
        """Estrae contorni da immagine (riutilizza logica K-Means)"""
        print(f"\n🎨 Estrazione forme da immagine...")
        
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Impossibile caricare: {image_path}")
        
        height, width = image.shape[:2]
        print(f"   Dimensioni: {width}x{height}px")
        
        # K-Means clustering
        pixels = image.reshape((-1, 3)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(pixels, n_colors, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
        
        # Trova contorni per ogni colore
        candidates = []
        
        for color_idx in range(n_colors):
            mask = (labels.flatten() == color_idx).reshape((height, width)).astype(np.uint8) * 255
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area < min_area:
                    continue
                
                # Semplifica contorno
                epsilon = 0.001 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                points = [(int(p[0][0]), int(p[0][1])) for p in approx]
                
                # Normalizza coordinate (0-1)
                normalized_points = [(x/width, y/height) for x, y in points]
                
                # Crea poligono Shapely
                if len(normalized_points) >= 3:
                    try:
                        poly = Polygon(normalized_points)
                        if poly.is_valid and poly.area > 0:
                            candidates.append({
                                'geometry': poly,
                                'area': area,
                                'points': points,
                                'normalized': normalized_points
                            })
                    except:
                        continue
        
        print(f"   ✅ {len(candidates)} forme estratte")
        return candidates
    
    def normalize_shape(self, poly: Polygon) -> np.ndarray:
        """Normalizza forma per confronto (invariante a scala/rotazione/traslazione)"""
        coords = np.array(poly.exterior.coords[:-1])  # Rimuovi ultimo punto duplicato
        
        # Centra sul centroide
        centroid = np.mean(coords, axis=0)
        coords_centered = coords - centroid
        
        # Normalizza scala
        max_dist = np.max(np.linalg.norm(coords_centered, axis=1))
        if max_dist > 0:
            coords_normalized = coords_centered / max_dist
        else:
            coords_normalized = coords_centered
        
        # Allinea orientamento (usa punto più a nord come riferimento)
        north_idx = np.argmax(coords_normalized[:, 1])
        coords_aligned = np.roll(coords_normalized, -north_idx, axis=0)
        
        return coords_aligned
    
    def shape_similarity(self, poly1: Polygon, poly2: Polygon) -> float:
        """Calcola similarità tra due forme (0=diverso, 1=identico)"""
        try:
            # Metodo 1: Hausdorff distance normalizzata
            coords1 = self.normalize_shape(poly1)
            coords2 = self.normalize_shape(poly2)
            
            # Interpola per avere stesso numero di punti
            n_points = 50
            coords1_interp = self._interpolate_shape(coords1, n_points)
            coords2_interp = self._interpolate_shape(coords2, n_points)
            
            # Distanza Hausdorff
            hausdorff = max(
                distance.directed_hausdorff(coords1_interp, coords2_interp)[0],
                distance.directed_hausdorff(coords2_interp, coords1_interp)[0]
            )
            
            # Converti in score (0-1)
            similarity_hausdorff = np.exp(-hausdorff * 5)
            
            # Metodo 2: IoU (Intersection over Union)
            intersection = poly1.intersection(poly2).area
            union = poly1.union(poly2).area
            iou = intersection / union if union > 0 else 0
            
            # Combina metodi (pesato)
            combined_score = 0.6 * similarity_hausdorff + 0.4 * iou
            
            return combined_score
            
        except:
            return 0.0
    
    def _interpolate_shape(self, coords: np.ndarray, n_points: int) -> np.ndarray:
        """Interpola punti lungo perimetro"""
        from scipy.interpolate import interp1d
        
        t = np.linspace(0, 1, len(coords))
        t_new = np.linspace(0, 1, n_points)
        
        fx = interp1d(t, coords[:, 0], kind='linear')
        fy = interp1d(t, coords[:, 1], kind='linear')
        
        return np.column_stack([fx(t_new), fy(t_new)])
    
    def find_best_match(self, extracted_shape: Dict, top_k: int = 5, region_filter: str = None, prefer_large: bool = True) -> List[Dict]:
        """Trova migliori match nel database mondiale"""
        extracted_poly = extracted_shape['geometry']
        
        matches = []
        
        # Usa GADM Italy se disponibile e filtro Italy
        if region_filter and region_filter.lower() == 'italy' and self.italy_regions is not None:
            search_set = self.italy_regions.copy()
            name_field = 'NAME_1'  # Nome regione in GADM
            admin_field = 'COUNTRY'
            print(f"     [GADM] Confronto con {len(search_set)} regioni italiane...", end='', flush=True)
        
        # Altrimenti usa Natural Earth
        elif region_filter:
            search_set = self.world_shapes[self.world_shapes['admin'].str.contains(region_filter, case=False, na=False)].copy()
            name_field = 'name'
            admin_field = 'admin'
            
            # Per l'Italia senza GADM, prendi solo entità grandi
            if prefer_large and region_filter.lower() == 'italy':
                import warnings
                warnings.filterwarnings('ignore', category=UserWarning)
                search_set['area_deg2'] = search_set.geometry.area
                threshold = search_set['area_deg2'].quantile(0.70)
                search_set = search_set[search_set['area_deg2'] >= threshold]
            
            print(f"     [Natural Earth] Confronto con {len(search_set)} entità...", end='', flush=True)
        else:
            search_set = self.world_shapes.copy()
            name_field = 'name'
            admin_field = 'admin'
            print(f"     Confronto con {len(search_set)} entità...", end='', flush=True)
        
        for idx, row in search_set.iterrows():
            db_geom = row.geometry
            
            # Converti MultiPolygon in Polygon principale
            if isinstance(db_geom, MultiPolygon):
                db_geom = max(db_geom.geoms, key=lambda p: p.area)
            
            if not isinstance(db_geom, Polygon):
                continue
            
            # Calcola similarità
            score = self.shape_similarity(extracted_poly, db_geom)
            
            if score > 0.12:  # Soglia bassissima per mappe stilizzate
                matches.append({
                    'name': row.get(name_field, 'Unknown'),
                    'admin': row.get(admin_field, 'Unknown') if admin_field in row else 'Italy',
                    'region': row.get('region', '') if 'region' in row else 'Europe',
                    'score': score,
                    'geometry': db_geom,
                    'properties': row.to_dict()
                })
        
        print(f" trovati {len(matches)} candidati")
        
        # Ordina per score
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        return matches[:top_k]
    
    def match_all(self, image_path: str, confidence_threshold: float = 0.3, region_filter: str = None) -> Dict:
        """Processo completo: estrai → match → GeoJSON
        
        Args:
            image_path: Path immagine
            confidence_threshold: Soglia minima confidenza (0.0-1.0)
            region_filter: Filtra per paese (es. "Italy", "France")
        """
        print("\n" + "="*60)
        print("🔍 SHAPE MATCHING - Riconoscimento Automatico")
        print("="*60)
        
        if region_filter:
            print(f"🎯 Filtro geografico: {region_filter}")
        
        # 1. Estrai forme da immagine
        extracted_shapes = self.extract_features_from_image(image_path, n_colors=80, min_area=200)
        
        if not extracted_shapes:
            print("\n❌ Nessuna forma estratta dall'immagine")
            return None
        
        # Ordina per area (più grandi prima)
        extracted_shapes.sort(key=lambda x: x['area'], reverse=True)
        
        # 2. Match con database
        print(f"\n🎯 Matching con database mondiale...")
        
        results = []
        
        for i, shape in enumerate(extracted_shapes[:25]):  # Limita a 25 forme più grandi
            print(f"\n   Forma {i+1}/{min(25, len(extracted_shapes))} (area: {shape['area']:.0f}px²)...")
            
            # Prioritizza entità grandi se filtro Italy (regioni non province)
            prefer_large = (region_filter and region_filter.lower() == 'italy')
            matches = self.find_best_match(shape, top_k=5, region_filter=region_filter, prefer_large=prefer_large)
            
            if matches:
                best_match = matches[0]
                
                print(f"     Top 3 match:")
                for j, m in enumerate(matches[:3], 1):
                    print(f"       {j}. {m['name']} ({m['admin']}) - {m['score']:.3f}")
                
                if best_match['score'] >= confidence_threshold:
                    print(f"     ✓ ACCETTATO: {best_match['name']} ({best_match['score']:.2%})")
                    
                    results.append({
                        'extracted_geometry': shape['geometry'],
                        'matched_name': best_match['name'],
                        'matched_admin': best_match['admin'],
                        'matched_region': best_match['region'],
                        'confidence': best_match['score'],
                        'db_geometry': best_match['geometry'],
                        'properties': best_match['properties']
                    })
                else:
                    print(f"     ⚠️ Score troppo basso ({best_match['score']:.2%} < {confidence_threshold:.0%})")
            else:
                print(f"     ⚠️ Nessun candidato trovato")
        
        # 3. Crea GeoJSON
        print(f"\n📝 Generazione GeoJSON...")
        
        features = []
        
        for result in results:
            feature = {
                "type": "Feature",
                "properties": {
                    "name": result['matched_name'],
                    "admin": result['matched_admin'],
                    "region": result['matched_region'],
                    "confidence": round(result['confidence'], 3),
                    "source": "shape_matching"
                },
                "geometry": mapping(result['db_geometry'])  # Usa geometria DB (precisa)
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Salva
        output_path = Path(image_path).with_suffix('.matched.geojson')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ {len(results)} regioni riconosciute")
        print(f"📁 GeoJSON: {output_path}")
        
        return {
            'geojson': geojson,
            'output_path': str(output_path),
            'matched_count': len(results),
            'total_extracted': len(extracted_shapes)
        }


def main():
    print("\n🌍 SHAPE MATCHER - Riconoscimento Geografico Automatico")
    print("="*70)
    print("Confronta forme estratte da immagini con database mondiale")
    print("Database: Natural Earth (stati/province mondiali)\n")
    
    image_path = input("📁 Immagine mappa: ").strip('"')
    
    # Opzionale: filtro geografico
    print("\n💡 Opzionale: filtra per paese (es. 'Italy', 'France', 'Germany')")
    region_filter = input("   Filtro [lascia vuoto per ricerca mondiale]: ").strip()
    if not region_filter:
        region_filter = None
    
    # Soglia confidenza
    print("\n💡 Soglia confidenza per mappe stilizzate (0.0-1.0)")
    print("   Suggerito: 0.15-0.20 per mappe illustrate/colorate")
    threshold_input = input("   Soglia [0.18]: ").strip()
    threshold = float(threshold_input) if threshold_input else 0.18
    
    try:
        matcher = ShapeMatcher()
        result = matcher.match_all(image_path, confidence_threshold=threshold, region_filter=region_filter)
        
        if result:
            print("\n" + "="*70)
            print("✅ COMPLETATO!")
            print("="*70)
            print(f"   {result['matched_count']}/{result['total_extracted']} forme riconosciute")
            
            if result['matched_count'] == 0:
                print("\n💡 SUGGERIMENTI:")
                print("   - Abbassa la soglia (es. 0.2)")
                print("   - Usa filtro geografico (es. 'Italy')")
                print("   - Verifica che l'immagine sia chiara")
            
            print(f"\n🌐 Visualizza su: http://geojson.io")
            print(f"   File: {result['output_path']}")
        
    except Exception as e:
        print(f"\n❌ Errore: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
