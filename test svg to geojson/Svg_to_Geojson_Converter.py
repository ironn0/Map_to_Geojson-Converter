import xml.etree.ElementTree as ET
import json
import re
import os

def parse_svg_path(path_data):
    """Parser SVG path"""
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
        
        if cmd_type == 'M':
            for i in range(0, len(params), 2):
                if i + 1 < len(params):
                    current_x, current_y = params[i], params[i+1]
                    if i == 0:
                        start_x, start_y = current_x, current_y
                    coordinates.append([current_x, current_y])
        
        elif cmd_type == 'm':
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
        
        elif cmd_type == 'L':
            for i in range(0, len(params), 2):
                if i + 1 < len(params):
                    current_x, current_y = params[i], params[i+1]
                    coordinates.append([current_x, current_y])
        
        elif cmd_type == 'l':
            for i in range(0, len(params), 2):
                if i + 1 < len(params):
                    current_x += params[i]
                    current_y += params[i+1]
                    coordinates.append([current_x, current_y])
        
        elif cmd_type in ['Z', 'z']:
            if start_x is not None and start_y is not None:
                coordinates.append([start_x, start_y])
    
    return coordinates

def svg_to_latlon(x, y):
    """Converti coordinate SVG in lat/lon"""
    # Per una mappa del mondo standard:
    # SVG width ~2000px = 360° longitudine
    # SVG height ~857px = 180° latitudine
    
    lon = (x / 2000) * 360 - 180
    lat = 90 - (y / 1000) * 180
    
    # Limita i valori
    lon = max(-180, min(180, lon))
    lat = max(-90, min(90, lat))
    
    return [lon, lat]

def convert_svg_to_geojson(svg_file, output_file):
    """Converte SVG in GeoJSON"""
    
    tree = ET.parse(svg_file)
    root = tree.getroot()
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    
    features = []
    
    print("📍 Conversione in corso...")
    
    country_paths = {}
    for path in root.findall('.//svg:path', ns):
        country_id = path.get('id')
        country_name = path.get('name')
        path_data = path.get('d')
        
        if not country_id or not path_data:
            continue
        
        if country_id not in country_paths:
            country_paths[country_id] = {'name': country_name, 'paths': []}
        
        country_paths[country_id]['paths'].append(path_data)
    
    for country_id, data in country_paths.items():
        all_polygons = []
        
        for path_data in data['paths']:
            svg_coords = parse_svg_path(path_data)
            
            if len(svg_coords) < 3:
                continue
            
            geo_coords = [svg_to_latlon(x, y) for x, y in svg_coords]
            
            if geo_coords and geo_coords[0] != geo_coords[-1]:
                geo_coords.append(geo_coords[0])
            
            if len(geo_coords) >= 4:
                all_polygons.append(geo_coords)
        
        if not all_polygons:
            continue
        
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
                "id": country_id,
                "name": data['name']
            },
            "geometry": geometry
        }
        
        features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Convertiti {len(features)} paesi")
    print(f"📁 File salvato: {output_file}")
    print(f"🌐 Testa su: http://geojson.io\n")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    svg_path = os.path.join(script_dir, "world (1).svg")
    output_path = os.path.join(script_dir, "world_map.geojson")
    
    print(f"📂 Cerco SVG in: {svg_path}")
    
    if os.path.exists(svg_path):
        print("✅ File trovato!\n")
        convert_svg_to_geojson(svg_path, output_path)
    else:
        print(f"❌ File non trovato")