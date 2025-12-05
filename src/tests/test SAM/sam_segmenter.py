"""
SAM (Segment Anything Model) - Map Region Extractor

Uses Meta's SAM model to automatically extract region boundaries from map images.
Much more accurate than K-Means for complex maps.

Requirements:
    pip install transformers torch pillow numpy opencv-python

Author: Map to GeoJSON Converter Project
"""

import numpy as np
from PIL import Image
import cv2
from pathlib import Path
import json
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import sys

# Check if transformers is available
try:
    from transformers import SamModel, SamProcessor, pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("ÔÜá´©Å transformers not installed. Run: pip install transformers torch")


@dataclass
class ExtractedRegion:
    """Represents an extracted region from the map"""
    mask: np.ndarray
    contour: np.ndarray
    centroid: Tuple[float, float]
    area: float
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    color: Optional[Tuple[int, int, int]] = None
    name: Optional[str] = None
    score: float = 0.0


class SAMSegmenter:
    """
    Segment Anything Model wrapper for map region extraction.
    
    Uses facebook/sam-vit-base for a good balance of speed and accuracy.
    For higher accuracy, use facebook/sam-vit-huge (but slower).
    """
    
    def __init__(self, model_name: str = "facebook/sam-vit-base", device: str = None):
        """
        Initialize the SAM model.
        
        Args:
            model_name: HuggingFace model name (sam-vit-base, sam-vit-large, sam-vit-huge)
            device: 'cuda', 'cpu', or None for auto-detect
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers and torch are required. Install with: pip install transformers torch")
        
        self.model_name = model_name
        
        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
        
        print(f"­ƒöº Loading SAM model: {model_name}")
        print(f"   Device: {self.device}")
        
        # Load model and processor
        self.model = SamModel.from_pretrained(model_name)
        self.processor = SamProcessor.from_pretrained(model_name)
        
        if self.device == "cuda":
            self.model = self.model.to("cuda")
        
        print("Ô£à SAM model loaded successfully!")
    
    def segment_automatic(self, image_path: str, points_per_side: int = 32, 
                         min_area: int = 500) -> List[ExtractedRegion]:
        """
        Automatically segment all regions in the image.
        
        Args:
            image_path: Path to the map image
            points_per_side: Grid density for automatic segmentation (higher = more regions)
            min_area: Minimum region area in pixels to keep
            
        Returns:
            List of ExtractedRegion objects
        """
        print(f"­ƒôÀ Loading image: {image_path}")
        image = Image.open(image_path).convert("RGB")
        image_np = np.array(image)
        
        print(f"­ƒöì Running automatic segmentation (points_per_side={points_per_side})...")
        
        # Use pipeline for automatic mask generation
        generator = pipeline(
            "mask-generation", 
            model=self.model_name, 
            device=0 if self.device == "cuda" else -1,
            points_per_batch=64
        )
        
        outputs = generator(image_path, points_per_batch=64)
        
        print(f"   Found {len(outputs['masks'])} raw masks")
        
        # Process masks into regions
        regions = []
        for i, mask in enumerate(outputs['masks']):
            mask_np = np.array(mask).astype(np.uint8)
            
            # Find contours
            contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                continue
            
            # Get largest contour
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            
            if area < min_area:
                continue
            
            # Calculate centroid
            M = cv2.moments(largest)
            if M["m00"] > 0:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
            else:
                continue
            
            # Get bounding box
            x, y, w, h = cv2.boundingRect(largest)
            
            # Get dominant color in region
            masked_pixels = image_np[mask_np > 0]
            if len(masked_pixels) > 0:
                color = tuple(int(c) for c in np.mean(masked_pixels, axis=0))
            else:
                color = (128, 128, 128)
            
            # Get score if available - convert to float
            score_val = outputs.get('scores', [0.0] * len(outputs['masks']))[i] if 'scores' in outputs else 0.0
            score = float(score_val) if hasattr(score_val, 'item') else float(score_val) if score_val else 0.0
            
            region = ExtractedRegion(
                mask=mask_np,
                contour=largest,
                centroid=(float(cx), float(cy)),
                area=float(area),
                bbox=(x, y, w, h),
                color=color,
                score=score
            )
            regions.append(region)
        
        # Sort by area (largest first)
        regions.sort(key=lambda r: r.area, reverse=True)
        
        print(f"Ô£à Extracted {len(regions)} valid regions")
        return regions
    
    def segment_with_points(self, image_path: str, 
                           points: List[Tuple[int, int]]) -> List[ExtractedRegion]:
        """
        Segment specific regions by clicking points.
        
        Args:
            image_path: Path to the map image
            points: List of (x, y) coordinates where user clicked
            
        Returns:
            List of ExtractedRegion objects
        """
        print(f"­ƒôÀ Loading image: {image_path}")
        image = Image.open(image_path).convert("RGB")
        image_np = np.array(image)
        
        # Format points for SAM
        input_points = [[[p[0], p[1]] for p in points]]
        
        print(f"­ƒÄ» Segmenting {len(points)} clicked points...")
        
        # Process with SAM
        inputs = self.processor(image, input_points=input_points, return_tensors="pt")
        
        if self.device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        # Post-process masks
        masks = self.processor.image_processor.post_process_masks(
            outputs.pred_masks.cpu(),
            inputs["original_sizes"].cpu(),
            inputs["reshaped_input_sizes"].cpu()
        )
        
        scores = outputs.iou_scores.cpu().numpy()
        
        regions = []
        for i, (mask_tensor, score) in enumerate(zip(masks[0], scores[0])):
            # Take best mask for each point
            best_idx = np.argmax(score)
            mask_np = mask_tensor[best_idx].numpy().astype(np.uint8)
            
            # Find contours
            contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                continue
            
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            
            M = cv2.moments(largest)
            if M["m00"] > 0:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
            else:
                continue
            
            x, y, w, h = cv2.boundingRect(largest)
            
            masked_pixels = image_np[mask_np > 0]
            color = tuple(np.mean(masked_pixels, axis=0).astype(int)) if len(masked_pixels) > 0 else (128, 128, 128)
            
            region = ExtractedRegion(
                mask=mask_np,
                contour=largest,
                centroid=(cx, cy),
                area=area,
                bbox=(x, y, w, h),
                color=color,
                score=float(score[best_idx])
            )
            regions.append(region)
        
        print(f"Ô£à Extracted {len(regions)} regions from points")
        return regions
    
    def visualize_regions(self, image_path: str, regions: List[ExtractedRegion], 
                         output_path: str = None) -> np.ndarray:
        """
        Visualize extracted regions on the original image.
        
        Args:
            image_path: Path to original image
            regions: List of ExtractedRegion objects
            output_path: Optional path to save visualization
            
        Returns:
            Visualization as numpy array
        """
        image = np.array(Image.open(image_path).convert("RGB"))
        overlay = image.copy()
        
        # Draw each region
        for i, region in enumerate(regions):
            # Random color for visualization
            color = (
                np.random.randint(50, 255),
                np.random.randint(50, 255),
                np.random.randint(50, 255)
            )
            
            # Draw contour
            cv2.drawContours(overlay, [region.contour], -1, color, 2)
            
            # Draw centroid
            cx, cy = int(region.centroid[0]), int(region.centroid[1])
            cv2.circle(overlay, (cx, cy), 5, (255, 255, 0), -1)
            
            # Draw label
            label = region.name or f"R{i+1}"
            cv2.putText(overlay, label, (cx - 20, cy - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        # Blend with original
        result = cv2.addWeighted(image, 0.6, overlay, 0.4, 0)
        
        if output_path:
            cv2.imwrite(output_path, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
            print(f"­ƒÆ¥ Saved visualization to: {output_path}")
        
        return result
    
    def export_geojson(self, regions: List[ExtractedRegion], 
                      output_path: str,
                      geo_bounds: dict = None,
                      image_size: Tuple[int, int] = None,
                      region_names: dict = None,
                      real_geometries: dict = None) -> dict:
        """
        Export regions to GeoJSON format.
        
        Args:
            regions: List of ExtractedRegion objects
            output_path: Path to save GeoJSON file
            geo_bounds: Dict with 'north', 'south', 'east', 'west' for coordinate transformation
            image_size: (width, height) of original image
            region_names: Dict mapping region index to name
            real_geometries: Dict mapping region index to real shapely geometry from database
            
        Returns:
            GeoJSON dictionary
        """
        features = []
        skipped = 0
        
        for i, region in enumerate(regions):
            # Get region name
            name = region_names.get(i, None) if region_names else None
            if not name or name == "Unknown":
                skipped += 1
                continue  # Skip unidentified regions
            
            # Use real geometry from database if available
            if real_geometries and i in real_geometries and real_geometries[i] is not None:
                geom = real_geometries[i]
                # Convert shapely geometry to GeoJSON format
                if hasattr(geom, '__geo_interface__'):
                    geometry = geom.__geo_interface__
                else:
                    skipped += 1
                    continue
            else:
                # Fallback to extracted contour (not recommended)
                coords = region.contour.squeeze().tolist()
                
                if geo_bounds and image_size:
                    min_lon = geo_bounds.get('west', 0)
                    max_lon = geo_bounds.get('east', 1)
                    min_lat = geo_bounds.get('south', 0)
                    max_lat = geo_bounds.get('north', 1)
                    img_w, img_h = image_size
                    
                    geo_coords = []
                    for x, y in coords:
                        lon = min_lon + (x / img_w) * (max_lon - min_lon)
                        lat = max_lat - (y / img_h) * (max_lat - min_lat)
                        geo_coords.append([lon, lat])
                    
                    geo_coords.append(geo_coords[0])
                    coords = geo_coords
                
                geometry = {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
            
            feature = {
                "type": "Feature",
                "properties": {
                    "id": i + 1,
                    "name": name,
                    "area_pixels": float(region.area),
                    "color": f"#{region.color[0]:02x}{region.color[1]:02x}{region.color[2]:02x}",
                    "score": float(region.score) if hasattr(region.score, 'item') else float(region.score)
                },
                "geometry": geometry
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2)
        
        print(f"Exported {len(features)} regions to: {output_path} (skipped {skipped} unidentified)")
        return geojson


def main():
    """Demo of SAM segmentation"""
    print("=" * 60)
    print("­ƒù║´©Å  SAM Map Segmenter - Demo")
    print("=" * 60)
    
    if not TRANSFORMERS_AVAILABLE:
        print("\nÔØî Please install required packages:")
        print("   pip install transformers torch pillow numpy opencv-python")
        return
    
    # Check for test image
    test_images = [
        Path(__file__).parent / "test_map.png",
        Path(__file__).parent.parent / "test comparison" / "image.png",
    ]
    
    image_path = None
    for path in test_images:
        if path.exists():
            image_path = str(path)
            break
    
    if not image_path:
        print("\nÔÜá´©Å No test image found. Please provide an image path:")
        image_path = input("Image path: ").strip()
        if not Path(image_path).exists():
            print("ÔØî File not found!")
            return
    
    print(f"\n­ƒôÀ Using image: {image_path}")
    
    # Initialize SAM
    try:
        segmenter = SAMSegmenter(model_name="facebook/sam-vit-base")
    except Exception as e:
        print(f"ÔØî Error loading SAM: {e}")
        print("\nTrying to download model... This may take a few minutes.")
        segmenter = SAMSegmenter(model_name="facebook/sam-vit-base")
    
    # Run automatic segmentation
    print("\n" + "=" * 60)
    regions = segmenter.segment_automatic(image_path, points_per_side=32, min_area=1000)
    
    # Show results
    print(f"\n­ƒôè Results:")
    print(f"   Total regions: {len(regions)}")
    for i, r in enumerate(regions[:10]):  # Show first 10
        print(f"   [{i+1}] Area: {r.area:.0f}px, Color: {r.color}, Score: {r.score:.2f}")
    
    if len(regions) > 10:
        print(f"   ... and {len(regions) - 10} more")
    
    # Save visualization
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    vis_path = str(output_dir / "sam_segmented.png")
    segmenter.visualize_regions(image_path, regions, vis_path)
    
    # Export GeoJSON (pixel coordinates)
    geojson_path = str(output_dir / "sam_regions.geojson")
    img = Image.open(image_path)
    segmenter.export_geojson(regions, geojson_path, image_size=img.size)
    
    print("\nÔ£à Done!")
    print(f"   Visualization: {vis_path}")
    print(f"   GeoJSON: {geojson_path}")


class RegionMatcher:
    """
    Matches extracted regions with a worldwide geographic database.
    Uses Natural Earth or GADM shapefiles for region identification.
    """
    
    def __init__(self, shapefile_path: str = None, name_field: str = None):
        """
        Initialize the region matcher with a shapefile.
        
        Args:
            shapefile_path: Path to shapefile. If None, tries to find Natural Earth data.
            name_field: Field name to use for region names (e.g., 'name', 'NAME_1')
        """
        try:
            import geopandas as gpd
            self.gpd = gpd
        except ImportError:
            raise ImportError("geopandas is required. Install with: pip install geopandas")
        
        from shapely.geometry import Point, Polygon, box
        from shapely.ops import unary_union
        self.Point = Point
        self.Polygon = Polygon
        self.box = box
        self.unary_union = unary_union
        
        # Store preferred name field
        self.name_field = name_field
        
        # Find shapefile
        if shapefile_path is None:
            # Try to find Natural Earth data
            possible_paths = [
                Path(__file__).parent.parent / "test comparison" / "geodata" / "ne_10m_admin_1_states_provinces" / "ne_10m_admin_1_states_provinces.shp",
                Path(__file__).parent / "geodata" / "ne_10m_admin_1_states_provinces" / "ne_10m_admin_1_states_provinces.shp",
            ]
            
            for path in possible_paths:
                if path.exists():
                    shapefile_path = str(path)
                    break
            
            if shapefile_path is None:
                raise FileNotFoundError("Natural Earth shapefile not found. Please provide shapefile_path.")
        
        print(f"Loading shapefile: {shapefile_path}")
        self.gdf = self.gpd.read_file(shapefile_path)
        self.original_gdf = self.gdf.copy()  # Keep original for filtering
        print(f"   Loaded {len(self.gdf)} regions from database")
        
        # Print available columns for debugging
        print(f"   Available columns: {list(self.gdf.columns)[:10]}...")
    
    def filter_by_bounds(self, geo_bounds: dict):
        """
        Filter database to only include regions within the given bounds.
        This speeds up matching significantly.
        """
        min_lon = geo_bounds.get('west', -180)
        max_lon = geo_bounds.get('east', 180)
        min_lat = geo_bounds.get('south', -90)
        max_lat = geo_bounds.get('north', 90)
        
        # Create bounding box
        bbox = self.box(min_lon, min_lat, max_lon, max_lat)
        
        # Filter regions that intersect with bbox
        self.gdf = self.original_gdf[self.original_gdf.geometry.intersects(bbox)].copy()
        print(f"   Filtered to {len(self.gdf)} regions within bounds")
        return len(self.gdf)
    
    def filter_by_country(self, country_name: str):
        """
        Filter database to only include regions from a specific country.
        Works with Natural Earth data.
        """
        # Try different country column names
        country_cols = ['admin', 'ADMIN', 'sovereignt', 'name_sort', 'geonunit']
        
        filtered = None
        for col in country_cols:
            if col in self.original_gdf.columns:
                mask = self.original_gdf[col].str.lower().str.contains(country_name.lower(), na=False)
                if mask.any():
                    filtered = self.original_gdf[mask].copy()
                    print(f"   Filtered by {col}='{country_name}': {len(filtered)} regions")
                    break
        
        if filtered is not None and len(filtered) > 0:
            self.gdf = filtered
        else:
            print(f"   Could not filter by country '{country_name}', using all regions")
        
        return len(self.gdf)
    
    def reset_filter(self):
        """Reset to original unfiltered database."""
        self.gdf = self.original_gdf.copy()
        print(f"   Reset to {len(self.gdf)} regions")
    
    def _contour_to_geo_polygon(self, contour: np.ndarray, geo_bounds: dict, 
                                 image_size: Tuple[int, int]):
        """Convert a pixel contour to a geographic polygon."""
        min_lon = geo_bounds.get('west', 0)
        max_lon = geo_bounds.get('east', 1)
        min_lat = geo_bounds.get('south', 0)
        max_lat = geo_bounds.get('north', 1)
        img_w, img_h = image_size
        
        coords = contour.squeeze().tolist()
        geo_coords = []
        for x, y in coords:
            lon = min_lon + (x / img_w) * (max_lon - min_lon)
            lat = max_lat - (y / img_h) * (max_lat - min_lat)
            geo_coords.append((lon, lat))
        
        # Close the polygon if needed
        if geo_coords[0] != geo_coords[-1]:
            geo_coords.append(geo_coords[0])
        
        try:
            return self.Polygon(geo_coords)
        except:
            return None
    
    def identify_regions(self, regions: List[ExtractedRegion], 
                        geo_bounds: dict,
                        image_size: Tuple[int, int],
                        method: str = "overlap") -> Tuple[dict, dict]:
        """
        Identify regions by matching with the geographic database.
        
        Args:
            regions: List of ExtractedRegion objects from SAM
            geo_bounds: Dict with 'north', 'south', 'east', 'west' of the map image
            image_size: (width, height) of the image in pixels
            method: "centroid" (point in polygon) or "overlap" (best area match)
            
        Returns:
            Tuple of:
            - Dict mapping region index to identified name
            - Dict mapping region index to real shapely geometry
        """
        min_lon = geo_bounds.get('west', 0)
        max_lon = geo_bounds.get('east', 1)
        min_lat = geo_bounds.get('south', 0)
        max_lat = geo_bounds.get('north', 1)
        img_w, img_h = image_size
        
        print(f"Identifying regions using {method} method...")
        print(f"   Geo bounds: N={max_lat} S={min_lat} E={max_lon} W={min_lon}")
        print(f"   Image size: {image_size}")
        
        # Convert ALL extracted regions to geographic polygons first
        extracted_polys = []
        for i, region in enumerate(regions):
            poly = self._contour_to_geo_polygon(region.contour, geo_bounds, image_size)
            if poly is not None and poly.is_valid:
                extracted_polys.append((i, poly, region))
            else:
                extracted_polys.append((i, None, region))
        
        # Create a union of all extracted polygons for coverage check
        valid_polys = [p for _, p, _ in extracted_polys if p is not None]
        if valid_polys:
            try:
                all_extracted = self.unary_union(valid_polys)
                print(f"   Extracted area bounds: W={all_extracted.bounds[0]:.2f} S={all_extracted.bounds[1]:.2f} E={all_extracted.bounds[2]:.2f} N={all_extracted.bounds[3]:.2f}")
                print(f"   Extracted area total: {all_extracted.area:.4f} sq degrees")
            except Exception as e:
                print(f"   Warning: Could not create union: {e}")
                all_extracted = None
        else:
            all_extracted = None
            print("   Warning: No valid extracted polygons!")
        
        names = {}
        geometries = {}
        
        if method == "overlap":
            # Check which DB regions are covered by extracted regions
            matched_db_regions = []
            not_found = []
            
            print(f"\n   Checking {len(self.gdf)} database regions...")
            
            for idx, row in self.gdf.iterrows():
                if row.geometry is None or not row.geometry.is_valid:
                    continue
                
                db_geom = row.geometry
                
                # Get region name for debugging
                db_name = None
                if self.name_field and self.name_field in row.index:
                    db_name = row[self.name_field]
                if not db_name:
                    for col in ['name', 'NAME', 'NAME_1', 'name_en']:
                        if col in row.index and row[col]:
                            db_name = row[col]
                            break
                db_name = str(db_name) if db_name else f"Region_{idx}"
                
                if all_extracted is None:
                    not_found.append(db_name)
                    continue
                    
                try:
                    # Check intersection
                    if not db_geom.intersects(all_extracted):
                        not_found.append(f"{db_name} (no intersect)")
                        continue
                    
                    intersection = db_geom.intersection(all_extracted)
                    if intersection.is_empty:
                        not_found.append(f"{db_name} (empty)")
                        continue
                    
                    # Calculate coverage
                    coverage = intersection.area / db_geom.area if db_geom.area > 0 else 0
                    
                    if coverage > 0.01:  # Very low threshold - 1%
                        matched_db_regions.append({
                            'idx': idx,
                            'name': db_name,
                            'geometry': db_geom,
                            'coverage': coverage
                        })
                        print(f"   + {db_name}: {coverage*100:.1f}% covered")
                    else:
                        not_found.append(f"{db_name} ({coverage*100:.1f}%)")
                        
                except Exception as e:
                    not_found.append(f"{db_name} (error: {str(e)[:30]})")
                    continue
            
            if not_found:
                print(f"\n   NOT FOUND ({len(not_found)}): {', '.join(not_found[:10])}")
                if len(not_found) > 10:
                    print(f"   ... and {len(not_found) - 10} more")
            
            # Now assign matches to extracted regions
            for i, poly, region in extracted_polys:
                if poly is None:
                    names[i] = "Unknown"
                    geometries[i] = None
                    continue
                
                best_match = None
                best_overlap = 0
                
                for db_region in matched_db_regions:
                    try:
                        intersection = poly.intersection(db_region['geometry'])
                        overlap = intersection.area / poly.area if poly.area > 0 else 0
                        
                        if overlap > best_overlap:
                            best_overlap = overlap
                            best_match = db_region
                    except:
                        continue
                
                if best_match and best_overlap > 0.05:  # 5% minimum
                    names[i] = best_match['name']
                    geometries[i] = best_match['geometry']
                else:
                    names[i] = "Unknown"
                    geometries[i] = None
            
            # Also return all matched DB regions that weren't assigned
            # This helps when one extraction covers multiple real regions
            print(f"\n   Total DB regions found in image: {len(matched_db_regions)}")
            
            # Store all matched DB regions for later use
            self._last_matched_db_regions = matched_db_regions
            
        else:  # centroid method
            for i, poly, region in extracted_polys:
                if poly is None:
                    cx, cy = region.centroid
                else:
                    # Use centroid of the geo polygon
                    cx, cy = region.centroid
                    
                lon = min_lon + (cx / img_w) * (max_lon - min_lon)
                lat = max_lat - (cy / img_h) * (max_lat - min_lat)
                point = self.Point(lon, lat)
                
                found = False
                for idx, row in self.gdf.iterrows():
                    if row.geometry and row.geometry.contains(point):
                        name = None
                        if self.name_field and self.name_field in row.index:
                            name = row[self.name_field]
                        if not name:
                            for col in ['name', 'NAME', 'NAME_1', 'name_en', 'admin', 'ADMIN']:
                                if col in row.index and row[col]:
                                    name = row[col]
                                    break
                        
                        if name:
                            names[i] = str(name)
                            geometries[i] = row.geometry
                            found = True
                            break
                
                if not found:
                    names[i] = "Unknown"
                    geometries[i] = None
        
        matched = sum(1 for name in names.values() if name != "Unknown")
        print(f"Matched {matched}/{len(regions)} extracted regions")
        return names, geometries
    
    def get_all_matched_regions(self) -> list:
        """
        Get all database regions that were found in the last identify_regions call.
        This is useful when one extracted region covers multiple real regions.
        
        Returns:
            List of dicts with 'name' and 'geometry' for each matched DB region
        """
        return getattr(self, '_last_matched_db_regions', [])
    
    def export_matched_regions_geojson(self, output_path: str) -> dict:
        """
        Export ALL matched database regions to GeoJSON.
        Use this instead of the normal export to get all real regions found in the image.
        
        Args:
            output_path: Path to save GeoJSON
            
        Returns:
            GeoJSON dictionary
        """
        matched = self.get_all_matched_regions()
        
        if not matched:
            print("No matched regions to export. Run identify_regions first.")
            return {"type": "FeatureCollection", "features": []}
        
        features = []
        for i, region in enumerate(matched):
            geom = region['geometry']
            if hasattr(geom, '__geo_interface__'):
                geometry = geom.__geo_interface__
            else:
                continue
            
            feature = {
                "type": "Feature",
                "properties": {
                    "id": i + 1,
                    "name": region['name'],
                    "coverage": round(region['coverage'] * 100, 1)
                },
                "geometry": geometry
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2)
        
        print(f"Exported {len(features)} real regions to: {output_path}")
        return geojson
    
    def export_all_database_regions(self, output_path: str, geo_bounds: dict = None) -> dict:
        """
        Export ALL regions from the database (optionally filtered by bounds).
        This bypasses SAM completely and just exports real geographic data.
        
        Args:
            output_path: Path to save GeoJSON
            geo_bounds: Optional dict with 'north', 'south', 'east', 'west' to filter
            
        Returns:
            GeoJSON dictionary
        """
        features = []
        
        for idx, row in self.gdf.iterrows():
            if row.geometry is None or not row.geometry.is_valid:
                continue
            
            geom = row.geometry
            
            # Filter by bounds if provided
            if geo_bounds:
                centroid = geom.centroid
                if not (geo_bounds['west'] <= centroid.x <= geo_bounds['east'] and
                        geo_bounds['south'] <= centroid.y <= geo_bounds['north']):
                    continue
            
            # Get name
            name = None
            if self.name_field and self.name_field in row.index:
                name = row[self.name_field]
            if not name:
                for col in ['name', 'NAME', 'NAME_1', 'name_en']:
                    if col in row.index and row[col]:
                        name = row[col]
                        break
            name = str(name) if name else f"Region_{idx}"
            
            if hasattr(geom, '__geo_interface__'):
                geometry = geom.__geo_interface__
            else:
                continue
            
            feature = {
                "type": "Feature",
                "properties": {
                    "id": len(features) + 1,
                    "name": name
                },
                "geometry": geometry
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(geojson, f, indent=2)
        
        print(f"Exported ALL {len(features)} database regions to: {output_path}")
        return geojson
    
    def get_gadm_geometry(self, region_name: str):
        """
        Get the real GADM/NE geometry for a region by name.
        
        Args:
            region_name: Name of the region to find
            
        Returns:
            Shapely geometry or None
        """
        for idx, row in self.gdf.iterrows():
            for col in ['name', 'NAME', 'NAME_1', 'name_en', 'admin', 'ADMIN']:
                if col in row.index and row[col] and str(row[col]).lower() == region_name.lower():
                    return row.geometry
        return None


# Preset country bounds for common use cases
COUNTRY_BOUNDS = {
    "Italia": (6.5, 36.0, 18.5, 47.5),
    "France": (-5.5, 41.0, 10.0, 51.5),
    "Germany": (5.5, 47.0, 15.5, 55.5),
    "Spain": (-9.5, 35.5, 4.5, 44.0),
    "United Kingdom": (-8.5, 49.5, 2.0, 61.0),
    "Poland": (14.0, 49.0, 24.5, 55.0),
    "USA": (-125.0, 24.0, -66.0, 50.0),
    "Brazil": (-74.0, -34.0, -34.0, 5.5),
    "China": (73.0, 18.0, 135.0, 54.0),
    "India": (68.0, 6.0, 97.5, 37.0),
    "Australia": (113.0, -44.0, 154.0, -10.0),
    "Japan": (129.0, 31.0, 146.0, 46.0),
}


if __name__ == "__main__":
    main()
