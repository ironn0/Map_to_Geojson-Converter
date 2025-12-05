"""
Interactive Map Viewer for Region Selection

Uses Folium (Leaflet wrapper) to display extracted regions
and allows users to select which ones to export.

Author: Map to GeoJSON Converter Project
"""

import folium
from folium.plugins import Draw, Search
import json
import webbrowser
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Optional, Callable
import threading
import http.server
import socketserver
from urllib.parse import parse_qs, urlparse

# Check if geopandas is available
try:
    import geopandas as gpd
    from shapely.geometry import shape, mapping
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False


class InteractiveMapViewer:
    """
    Creates an interactive Leaflet map to visualize and select regions.
    
    Features:
    - Display all identified regions on a map
    - Click to select/deselect regions
    - Different colors for selected vs unselected
    - Export only selected regions
    """
    
    def __init__(self):
        self.regions: List[Dict] = []  # List of region data
        self.selected_indices: set = set()  # Indices of selected regions
        self.map_path: Optional[str] = None
        self.callback: Optional[Callable] = None
        self._server = None
        self._server_thread = None
        
    def add_regions_from_matcher(self, region_matcher, include_unmatched: bool = False):
        """
        Load regions from a RegionMatcher instance.
        
        Args:
            region_matcher: RegionMatcher instance with loaded database
            include_unmatched: If True, include all database regions, not just matched
        """
        if region_matcher is None:
            return
        
        self.regions = []
        
        if include_unmatched and hasattr(region_matcher, 'gdf') and region_matcher.gdf is not None:
            # Load all regions from database
            gdf = region_matcher.gdf
            for idx, row in gdf.iterrows():
                name = row.get('NAME_1') or row.get('name') or row.get('NAME') or f"Region {idx}"
                geom = row.geometry
                
                # Get centroid for popup positioning
                centroid = geom.centroid
                
                self.regions.append({
                    'index': len(self.regions),
                    'name': name,
                    'geometry': mapping(geom),
                    'centroid': (centroid.y, centroid.x),
                    'matched': False,
                    'properties': {
                        'name': name,
                        'source': 'database'
                    }
                })
        else:
            # Load only matched regions
            matched = region_matcher.get_all_matched_regions()
            for region in matched:
                geom = region.get('geometry')
                if geom is None:
                    continue
                    
                name = region.get('name', 'Unknown')
                
                # Handle both shapely objects and GeoJSON dicts
                if hasattr(geom, '__geo_interface__'):
                    geom_dict = mapping(geom)
                    centroid = geom.centroid
                    centroid_coords = (centroid.y, centroid.x)
                elif isinstance(geom, dict):
                    geom_dict = geom
                    # Try to compute centroid
                    try:
                        shp = shape(geom)
                        centroid = shp.centroid
                        centroid_coords = (centroid.y, centroid.x)
                    except:
                        centroid_coords = (0, 0)
                else:
                    continue
                
                self.regions.append({
                    'index': len(self.regions),
                    'name': name,
                    'geometry': geom_dict,
                    'centroid': centroid_coords,
                    'matched': True,
                    'properties': region.get('properties', {'name': name})
                })
        
        # Select all by default
        self.selected_indices = set(range(len(self.regions)))
    
    def add_regions_from_geojson(self, geojson_path: str):
        """Load regions from a GeoJSON file."""
        with open(geojson_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.regions = []
        features = data.get('features', [])
        
        for idx, feature in enumerate(features):
            geom = feature.get('geometry')
            props = feature.get('properties', {})
            name = props.get('name') or props.get('NAME_1') or props.get('NAME') or f"Region {idx}"
            
            # Compute centroid
            try:
                shp = shape(geom)
                centroid = shp.centroid
                centroid_coords = (centroid.y, centroid.x)
            except:
                centroid_coords = (0, 0)
            
            self.regions.append({
                'index': idx,
                'name': name,
                'geometry': geom,
                'centroid': centroid_coords,
                'matched': True,
                'properties': props
            })
        
        # Select all by default
        self.selected_indices = set(range(len(self.regions)))
    
    def create_map(self, center: tuple = None, zoom: int = 6) -> folium.Map:
        """
        Create the Folium map with all regions.
        
        Args:
            center: (lat, lon) tuple for map center. Auto-calculated if None.
            zoom: Initial zoom level
            
        Returns:
            folium.Map object
        """
        # Auto-calculate center from regions
        if center is None and self.regions:
            lats = [r['centroid'][0] for r in self.regions if r['centroid'] != (0, 0)]
            lons = [r['centroid'][1] for r in self.regions if r['centroid'] != (0, 0)]
            if lats and lons:
                center = (sum(lats) / len(lats), sum(lons) / len(lons))
            else:
                center = (42.0, 12.0)  # Default: Italy
        elif center is None:
            center = (42.0, 12.0)
        
        # Create base map
        m = folium.Map(
            location=center,
            zoom_start=zoom,
            tiles='cartodbpositron'  # Clean, light map style
        )
        
        # Add layer control
        folium.TileLayer('OpenStreetMap', name='OpenStreetMap').add_to(m)
        folium.TileLayer('cartodbdark_matter', name='Dark Mode').add_to(m)
        
        # Create a single GeoJSON FeatureCollection with all regions
        features = []
        for region in self.regions:
            idx = region['index']
            is_selected = idx in self.selected_indices
            
            features.append({
                'type': 'Feature',
                'geometry': region['geometry'],
                'properties': {
                    **region['properties'],
                    'region_index': idx,
                    'region_name': region['name'],
                    'selected': is_selected
                }
            })
        
        geojson_data = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        # Add the GeoJSON layer with dynamic styling via JavaScript
        # We'll add it raw and control it via JS
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Add custom JavaScript for interactive click selection
        self._add_interactive_selection_js(m, geojson_data)
        
        return m
    
    def _add_interactive_selection_js(self, m: folium.Map, geojson_data: dict):
        """Add JavaScript for truly interactive region selection with click-to-toggle."""
        
        # Create a custom HTML with selection controls and interactive map logic
        selection_html = """
        <style>
            .info-panel {
                position: fixed;
                top: 10px;
                right: 10px;
                z-index: 1000;
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                font-family: Arial, sans-serif;
                max-width: 320px;
                max-height: 90vh;
                overflow-y: auto;
            }
            .region-list {
                max-height: 300px;
                overflow-y: auto;
                margin: 10px 0;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            .region-item {
                padding: 8px 12px;
                border-bottom: 1px solid #eee;
                cursor: pointer;
                display: flex;
                align-items: center;
                transition: background 0.2s;
            }
            .region-item:hover {
                background: #f5f5f5;
            }
            .region-item.selected {
                background: #d5f5e3;
            }
            .region-item .checkbox {
                width: 20px;
                height: 20px;
                margin-right: 10px;
                border: 2px solid #ccc;
                border-radius: 4px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
            }
            .region-item.selected .checkbox {
                background: #2ecc71;
                border-color: #27ae60;
                color: white;
            }
            .btn {
                padding: 8px 12px;
                margin: 2px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 13px;
            }
            .btn-primary { background: #3498db; color: white; }
            .btn-danger { background: #e74c3c; color: white; }
            .btn-success { background: #27ae60; color: white; font-weight: bold; }
            .btn:hover { opacity: 0.9; }
        </style>
        
        <div class="info-panel" id="selection-panel">
            <h3 style="margin: 0 0 10px 0; color: #333;">­ƒù║´©Å Region Selection</h3>
            <p style="margin: 5px 0; font-size: 12px; color: #666;">
                <b>Click on regions</b> on the map to select/deselect them.<br>
                Or use the list below.
            </p>
            <div style="margin: 10px 0; padding: 10px; background: #e8f5e9; border-radius: 4px;">
                <span id="selected-count" style="font-weight: bold; color: #2ecc71; font-size: 18px;">0</span>
                <span style="color: #666;"> / </span>
                <span id="total-count" style="color: #666;">0</span>
                <span style="color: #666;"> regions selected</span>
            </div>
            
            <div style="margin: 10px 0;">
                <button class="btn btn-primary" onclick="selectAll()">Ô£à Select All</button>
                <button class="btn btn-danger" onclick="selectNone()">ÔØî Clear All</button>
            </div>
            
            <div class="region-list" id="region-list">
                <!-- Region items will be added here by JS -->
            </div>
            
            <div style="margin-top: 10px;">
                <button class="btn btn-success" onclick="exportSelected()" style="width: 100%; padding: 12px;">
                    ­ƒÆ¥ Export Selected Regions
                </button>
            </div>
            
            <div id="export-info" style="
                margin-top: 10px;
                padding: 10px;
                background: #d5f5e3;
                border-radius: 4px;
                font-size: 12px;
                display: none;
            "></div>
        </div>
        
        <script>
        // Wait for map to be ready
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(initializeSelection, 500);
        });
        
        var selectedRegions = new Set(""" + json.dumps(list(self.selected_indices)) + """);
        var regionData = """ + json.dumps(self.regions) + """;
        var geojsonData = """ + json.dumps(geojson_data) + """;
        var geojsonLayer = null;
        var map = null;
        
        function initializeSelection() {
            // Find the Leaflet map instance
            for (var key in window) {
                if (window[key] instanceof L.Map) {
                    map = window[key];
                    break;
                }
            }
            
            if (!map) {
                console.error('Could not find Leaflet map');
                return;
            }
            
            // Add the GeoJSON layer with interactive styling
            geojsonLayer = L.geoJSON(geojsonData, {
                style: function(feature) {
                    var idx = feature.properties.region_index;
                    var isSelected = selectedRegions.has(idx);
                    return {
                        fillColor: isSelected ? '#2ecc71' : '#95a5a6',
                        color: isSelected ? '#27ae60' : '#7f8c8d',
                        weight: isSelected ? 3 : 1,
                        fillOpacity: isSelected ? 0.5 : 0.2,
                        opacity: 1
                    };
                },
                onEachFeature: function(feature, layer) {
                    var idx = feature.properties.region_index;
                    var name = feature.properties.region_name || feature.properties.name || 'Unknown';
                    
                    // Tooltip
                    layer.bindTooltip(function() {
                        var isSelected = selectedRegions.has(idx);
                        return '<b>' + name + '</b><br>' +
                               (isSelected ? 'Ô£à Selected' : 'ÔØî Not selected') +
                               '<br><i>Click to toggle</i>';
                    }, {sticky: true});
                    
                    // Click handler
                    layer.on('click', function(e) {
                        L.DomEvent.stopPropagation(e);
                        toggleRegion(idx);
                    });
                    
                    // Hover effect
                    layer.on('mouseover', function(e) {
                        layer.setStyle({
                            weight: 4,
                            fillOpacity: 0.7
                        });
                    });
                    
                    layer.on('mouseout', function(e) {
                        var isSelected = selectedRegions.has(idx);
                        layer.setStyle({
                            weight: isSelected ? 3 : 1,
                            fillOpacity: isSelected ? 0.5 : 0.2
                        });
                    });
                }
            }).addTo(map);
            
            // Build the region list
            buildRegionList();
            updateCount();
        }
        
        function buildRegionList() {
            var listEl = document.getElementById('region-list');
            listEl.innerHTML = '';
            
            regionData.forEach(function(region, idx) {
                var isSelected = selectedRegions.has(idx);
                var item = document.createElement('div');
                item.className = 'region-item' + (isSelected ? ' selected' : '');
                item.setAttribute('data-index', idx);
                item.innerHTML = '<div class="checkbox">' + (isSelected ? 'Ô£ô' : '') + '</div>' +
                                 '<span>' + region.name + '</span>';
                item.onclick = function() {
                    toggleRegion(idx);
                };
                listEl.appendChild(item);
            });
        }
        
        function updateCount() {
            document.getElementById('selected-count').textContent = selectedRegions.size;
            document.getElementById('total-count').textContent = regionData.length;
        }
        
        function updateRegionListItem(idx) {
            var item = document.querySelector('.region-item[data-index="' + idx + '"]');
            if (item) {
                var isSelected = selectedRegions.has(idx);
                item.className = 'region-item' + (isSelected ? ' selected' : '');
                item.querySelector('.checkbox').innerHTML = isSelected ? 'Ô£ô' : '';
            }
        }
        
        function toggleRegion(idx) {
            if (selectedRegions.has(idx)) {
                selectedRegions.delete(idx);
            } else {
                selectedRegions.add(idx);
            }
            
            // Update map style
            if (geojsonLayer) {
                geojsonLayer.eachLayer(function(layer) {
                    if (layer.feature && layer.feature.properties.region_index === idx) {
                        var isSelected = selectedRegions.has(idx);
                        layer.setStyle({
                            fillColor: isSelected ? '#2ecc71' : '#95a5a6',
                            color: isSelected ? '#27ae60' : '#7f8c8d',
                            weight: isSelected ? 3 : 1,
                            fillOpacity: isSelected ? 0.5 : 0.2
                        });
                    }
                });
            }
            
            updateRegionListItem(idx);
            updateCount();
        }
        
        function selectAll() {
            selectedRegions = new Set(Array.from({length: regionData.length}, function(_, i) { return i; }));
            updateAllStyles();
            buildRegionList();
            updateCount();
        }
        
        function selectNone() {
            selectedRegions.clear();
            updateAllStyles();
            buildRegionList();
            updateCount();
        }
        
        function updateAllStyles() {
            if (geojsonLayer) {
                geojsonLayer.eachLayer(function(layer) {
                    if (layer.feature) {
                        var idx = layer.feature.properties.region_index;
                        var isSelected = selectedRegions.has(idx);
                        layer.setStyle({
                            fillColor: isSelected ? '#2ecc71' : '#95a5a6',
                            color: isSelected ? '#27ae60' : '#7f8c8d',
                            weight: isSelected ? 3 : 1,
                            fillOpacity: isSelected ? 0.5 : 0.2
                        });
                    }
                });
            }
        }
        
        function exportSelected() {
            var selected = Array.from(selectedRegions);
            
            if (selected.length === 0) {
                alert('Please select at least one region!');
                return;
            }
            
            var features = selected.map(function(idx) {
                var r = regionData[idx];
                return {
                    type: 'Feature',
                    geometry: r.geometry,
                    properties: r.properties
                };
            });
            
            var geojson = {
                type: 'FeatureCollection',
                features: features
            };
            
            // Create download
            var dataStr = JSON.stringify(geojson, null, 2);
            var dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
            
            var exportName = 'selected_regions.geojson';
            
            var linkElement = document.createElement('a');
            linkElement.setAttribute('href', dataUri);
            linkElement.setAttribute('download', exportName);
            linkElement.click();
            
            // Show info
            var info = document.getElementById('export-info');
            info.style.display = 'block';
            var regionNames = selected.map(function(i) { return regionData[i].name; });
            info.innerHTML = 'Ô£à <b>Exported ' + features.length + ' regions!</b><br><br>' +
                'Regions: ' + regionNames.slice(0, 5).join(', ') +
                (regionNames.length > 5 ? '... and ' + (regionNames.length - 5) + ' more' : '');
        }
        </script>
        """
        
        # Add to map
        m.get_root().html.add_child(folium.Element(selection_html))
    
    def save_map(self, filepath: str = None) -> str:
        """
        Save the map to an HTML file.
        
        Args:
            filepath: Path to save. If None, creates temp file.
            
        Returns:
            Path to the saved HTML file
        """
        if filepath is None:
            # Create temp file
            fd, filepath = tempfile.mkstemp(suffix='.html', prefix='region_map_')
            os.close(fd)
        
        m = self.create_map()
        m.save(filepath)
        self.map_path = filepath
        
        return filepath
    
    def open_in_browser(self, filepath: str = None):
        """
        Save map and open in default browser.
        
        Args:
            filepath: Path to save. If None, creates temp file.
        """
        path = self.save_map(filepath)
        webbrowser.open(f'file://{path}')
        return path
    
    def get_selected_regions(self) -> List[Dict]:
        """Get list of currently selected regions."""
        return [r for r in self.regions if r['index'] in self.selected_indices]
    
    def export_selected_geojson(self, filepath: str) -> dict:
        """
        Export only selected regions to GeoJSON.
        
        Args:
            filepath: Output file path
            
        Returns:
            GeoJSON dict
        """
        selected = self.get_selected_regions()
        
        features = []
        for region in selected:
            features.append({
                'type': 'Feature',
                'geometry': region['geometry'],
                'properties': region['properties']
            })
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2, ensure_ascii=False)
        
        return geojson
    
    def select_all(self):
        """Select all regions."""
        self.selected_indices = set(range(len(self.regions)))
    
    def select_none(self):
        """Deselect all regions."""
        self.selected_indices.clear()
    
    def toggle_selection(self, index: int):
        """Toggle selection of a region by index."""
        if index in self.selected_indices:
            self.selected_indices.discard(index)
        else:
            self.selected_indices.add(index)


class MapSelectionDialog:
    """
    A dialog that shows the map in an embedded browser or external browser
    and handles the selection callback.
    """
    
    def __init__(self, parent_window=None):
        self.parent = parent_window
        self.viewer = InteractiveMapViewer()
        self.result_path: Optional[str] = None
        
    def show(self, region_matcher=None, geojson_path: str = None, 
             include_all_db: bool = False, bounds: dict = None) -> Optional[str]:
        """
        Show the map selection dialog.
        
        Args:
            region_matcher: RegionMatcher instance
            geojson_path: Path to existing GeoJSON file
            include_all_db: Include all database regions (not just matched)
            bounds: Geographic bounds dict with north, south, east, west
            
        Returns:
            Path to exported GeoJSON if user exports, None otherwise
        """
        # Load regions
        if geojson_path:
            self.viewer.add_regions_from_geojson(geojson_path)
        elif region_matcher:
            self.viewer.add_regions_from_matcher(region_matcher, include_all_db)
        
        if not self.viewer.regions:
            return None
        
        # Calculate center from bounds if provided
        center = None
        if bounds:
            center = (
                (bounds.get('north', 47) + bounds.get('south', 36)) / 2,
                (bounds.get('east', 18) + bounds.get('west', 7)) / 2
            )
        
        # Create and open map
        map_obj = self.viewer.create_map(center=center)
        
        # Save to temp file
        temp_dir = tempfile.gettempdir()
        map_path = os.path.join(temp_dir, 'map_selection.html')
        map_obj.save(map_path)
        
        # Open in browser
        webbrowser.open(f'file://{map_path}')
        
        return map_path


def create_selection_map(regions_data: List[Dict], output_path: str = None,
                         center: tuple = None, zoom: int = 6) -> str:
    """
    Convenience function to create a selection map from region data.
    
    Args:
        regions_data: List of dicts with 'name', 'geometry', 'properties'
        output_path: Where to save the HTML file
        center: (lat, lon) center point
        zoom: Initial zoom level
        
    Returns:
        Path to the saved HTML file
    """
    viewer = InteractiveMapViewer()
    
    for idx, region in enumerate(regions_data):
        geom = region.get('geometry')
        if isinstance(geom, dict):
            geom_dict = geom
        elif hasattr(geom, '__geo_interface__'):
            geom_dict = mapping(geom)
        else:
            continue
        
        # Calculate centroid
        try:
            shp = shape(geom_dict)
            centroid = shp.centroid
            centroid_coords = (centroid.y, centroid.x)
        except:
            centroid_coords = (0, 0)
        
        viewer.regions.append({
            'index': idx,
            'name': region.get('name', f'Region {idx}'),
            'geometry': geom_dict,
            'centroid': centroid_coords,
            'matched': True,
            'properties': region.get('properties', {'name': region.get('name', f'Region {idx}')})
        })
    
    viewer.select_all()
    
    return viewer.save_map(output_path)


# Test
if __name__ == "__main__":
    # Test with sample data
    print("Interactive Map Viewer")
    print("=" * 50)
    
    # Create sample regions (simple squares for testing)
    sample_regions = [
        {
            'name': 'Region A',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[[12, 42], [13, 42], [13, 43], [12, 43], [12, 42]]]
            },
            'properties': {'name': 'Region A', 'population': 1000000}
        },
        {
            'name': 'Region B', 
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[[13, 42], [14, 42], [14, 43], [13, 43], [13, 42]]]
            },
            'properties': {'name': 'Region B', 'population': 2000000}
        },
        {
            'name': 'Region C',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [[[12, 41], [14, 41], [14, 42], [12, 42], [12, 41]]]
            },
            'properties': {'name': 'Region C', 'population': 500000}
        }
    ]
    
    # Create map
    map_path = create_selection_map(sample_regions, center=(42, 13), zoom=8)
    print(f"Map saved to: {map_path}")
    
    # Open in browser
    webbrowser.open(f'file://{map_path}')
