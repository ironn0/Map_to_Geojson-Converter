import xml.etree.ElementTree as ET
import json
import re
import os

def parse_svg_path(path_data):
    """Parser SVG path semplificato"""
    if not path_data:
        return []
    
    coordinates = []
    path_data = re.sub(r'[\n\r\t]', ' ', path_data)
    path_data = re.sub(r'\s+', ' ', path_data)
    
    commands = re.findall(r'[MmLlHhVvCcSsQqTtAaZz][^MmLlHhVvCcSsQqTtAaZz]*', path_data)
    
    current_x, current_y = 0, 0
    start_x, start_y = 0, 0
    
    for cmd in commands:
        cmd_type = cmd[0]
        params = re.findall(r'-?\d*\.?\d+(?:[eE][-+]?\d+)?', cmd[1:])
        params = [float(p) for p in params if p]
        
        if not params and cmd_type not in ['zZ']:
            continue
        
        if cmd_type == 'M':  # Move absolute
            for i in range(0, len(params), 2):
                if i + 1 < len(params):
                    current_x, current_y = params[i], params[i+1]
                    if i == 0:
                        start_x, start_y = current_x, current_y
                    coordinates.append([current_x, current_y])
        
        elif cmd_type == 'm':  # Move relative
            for i in range(0, len(params), 2):
                if i + 1 < len(params):
                    if i == 0 and not coordinates:
                        current_x, current_y = params[i], params[i+1]
                    else:
                        current_x += params[i]
                        current_y += params[i+1]
                    if i == 0:
                        start_x, start_y = current_x, current_y
                    coordinates.append([current_x, current_y])
        
        elif cmd_type == 'L':  # Line absolute
            for i in range(0, len(params), 2):
                if i + 1 < len(params):
                    current_x, current_y = params[i], params[i+1]
                    coordinates.append([current_x, current_y])
        
        elif cmd_type == 'l':  # Line relative
            for i in range(0, len(params), 2):
                if i + 1 < len(params):
                    current_x += params[i]
                    current_y += params[i+1]
                    coordinates.append([current_x, current_y])
        
        elif cmd_type == 'H':  # Horizontal absolute
            for p in params:
                current_x = p
                coordinates.append([current_x, current_y])
        
        elif cmd_type == 'h':  # Horizontal relative
            for p in params:
                current_x += p
                coordinates.append([current_x, current_y])
        
        elif cmd_type == 'V':  # Vertical absolute
            for p in params:
                current_y = p
                coordinates.append([current_x, current_y])
        
        elif cmd_type == 'v':  # Vertical relative
            for p in params:
                current_y += p
                coordinates.append([current_x, current_y])
        
        elif cmd_type in ['Z', 'z']:  # Close path
            if start_x is not None and start_y is not None:
                coordinates.append([start_x, start_y])
    
    return coordinates

def analyze_svg(svg_file):
    """Analizza l'SVG e mostra info"""
    tree = ET.parse(svg_file)
    root = tree.getroot()
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    
    # Trova viewBox
    viewbox = root.get('viewBox')
    if viewbox:
        vb = viewbox.split()
        print(f"📐 ViewBox: {vb}")
        svg_width = float(vb[2]) if len(vb) > 2 else 1000
        svg_height = float(vb[3]) if len(vb) > 3 else 1000
    else:
        svg_width = float(root.get('width', '1000').replace('px', ''))
        svg_height = float(root.get('height', '1000').replace('px', ''))
    
    print(f"📏 Dimensioni SVG: {svg_width} x {svg_height}")
    
    # Conta elementi
    paths = root.findall('.//svg:path', ns)
    print(f"🗺️  Path trovati: {len(paths)}")
    
    # Trova bounds reali
    all_x, all_y = [], []
    for path in paths[:10]:  # Analizza primi 10
        path_data = path.get('d')
        if path_data:
            coords = parse_svg_path(path_data)
            for x, y in coords:
                all_x.append(x)
                all_y.append(y)
    
    if all_x and all_y:
        print(f"📊 Range X: {min(all_x):.1f} → {max(all_x):.1f}")
        print(f"📊 Range Y: {min(all_y):.1f} → {max(all_y):.1f}")
        return (min(all_x), max(all_x), min(all_y), max(all_y), svg_width, svg_height)
    
    return (0, svg_width, 0, svg_height, svg_width, svg_height)

def svg_to_latlon_italia(x, y, bounds):
    """Converti coordinate SVG in lat/lon per l'Italia"""
    min_x, max_x, min_y, max_y, svg_w, svg_h = bounds
    
    # Coordinate reali Italia
    # Lat: 36° (sud Sicilia) → 47° (nord)
    # Lon: 6° (ovest) → 19° (est)
    
    lat_min, lat_max = 36.0, 47.0
    lon_min, lon_max = 6.0, 19.0
    
    # Normalizza coordinate SVG
    x_norm = (x - min_x) / (max_x - min_x) if max_x > min_x else 0
    y_norm = (y - min_y) / (max_y - min_y) if max_y > min_y else 0
    
    # Converti in lat/lon (Y invertita!)
    lon = lon_min + x_norm * (lon_max - lon_min)
    lat = lat_max - y_norm * (lat_max - lat_min)  # Inverte Y
    
    # Limita
    lon = max(-180, min(180, lon))
    lat = max(-90, min(90, lat))
    
    return [lon, lat]

def convert_italia_to_geojson(svg_file, output_file):
    """Converte SVG Italia in GeoJSON"""
    
    print("\n🇮🇹 CONVERSIONE MAPPA ITALIA\n" + "="*50)
    
    # Analizza SVG
    bounds = analyze_svg(svg_file)
    
    tree = ET.parse(svg_file)
    root = tree.getroot()
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    
    features = []
    
    print("\n📍 Conversione in corso...")
    
    # Raggruppa per regione/provincia
    regions = {}
    for path in root.findall('.//svg:path', ns):
        region_id = path.get('id') or path.get('class') or f"region_{len(regions)}"
        region_name = path.get('name') or path.get('title') or region_id
        path_data = path.get('d')
        
        if not path_data:
            continue
        
        if region_id not in regions:
            regions[region_id] = {'name': region_name, 'paths': []}
        
        regions[region_id]['paths'].append(path_data)
    
    # Converti ogni regione
    for region_id, data in regions.items():
        all_polygons = []
        
        for path_data in data['paths']:
            svg_coords = parse_svg_path(path_data)
            
            if len(svg_coords) < 3:
                continue
            
            geo_coords = [svg_to_latlon_italia(x, y, bounds) for x, y in svg_coords]
            
            # Chiudi poligono
            if geo_coords and geo_coords[0] != geo_coords[-1]:
                geo_coords.append(geo_coords[0])
            
            if len(geo_coords) >= 4:
                all_polygons.append(geo_coords)
        
        if not all_polygons:
            continue
        
        # Geometria
        if len(all_polygons) == 1:
            geometry = {
                "type": "Polygon",
                "coordinates": all_polygons
            }
        else:
            geometry = {
                "type": "MultiPolygon",
                "coordinates": [[poly] for poly in all_polygons]
            }
        
        feature = {
            "type": "Feature",
            "properties": {
                "id": region_id,
                "name": data['name']
            },
            "geometry": geometry
        }
        
        features.append(feature)
        print(f"   ✓ {data['name']}")
    
    # Crea GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Convertite {len(features)} regioni/province")
    print(f"📁 File salvato: {output_file}")
    print(f"🌐 Testa su: http://geojson.io\n")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Cerca file SVG Italia
    possible_names = ["italia.svg", "italy.svg", "Italy.svg", "Italia.svg", "map-italy.svg"]
    
    svg_path = None
    for name in possible_names:
        test_path = os.path.join(script_dir, name)
        if os.path.exists(test_path):
            svg_path = test_path
            break
    
    if svg_path:
        output_path = os.path.join(script_dir, "italia_map.geojson")
        print(f"✅ Trovato: {os.path.basename(svg_path)}")
        convert_italia_to_geojson(svg_path, output_path)
    else:
        print("❌ File SVG Italia non trovato!")
        print(f"💡 Metti un file SVG dell'Italia nella cartella:")
        print(f"   {script_dir}")
        print(f"   Rinominalo come: italia.svg")