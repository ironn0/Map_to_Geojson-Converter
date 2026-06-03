"""
🌍 Georeferencer Module
Converte coordinate pixel in coordinate geografiche

Author: Map to GeoJSON Converter Project
"""

from typing import Dict, Tuple, List
import numpy as np


class Georeferencer:
    """Converte coordinate pixel in coordinate geografiche"""
    
    def __init__(self, width: int, height: int, bounds: Dict):
        self.width = width
        self.height = height
        self.north = bounds.get('north', 90)
        self.south = bounds.get('south', -90)
        self.east = bounds.get('east', 180)
        self.west = bounds.get('west', -180)
        
        self.lon_per_pixel = (self.east - self.west) / self.width
        self.lat_per_pixel = (self.north - self.south) / self.height
    
    def pixel_to_coord(self, x: float, y: float) -> Tuple[float, float]:
        """Converte coordinate pixel in longitudine/latitudine"""
        lon = self.west + (x * self.lon_per_pixel)
        lat = self.north - (y * self.lat_per_pixel)
        return (round(lon, 6), round(lat, 6))
    
    def coord_to_pixel(self, lon: float, lat: float) -> Tuple[int, int]:
        """Converte coordinate geografiche in pixel"""
        x = int((lon - self.west) / self.lon_per_pixel)
        y = int((self.north - lat) / self.lat_per_pixel)
        return (x, y)
    
    def contour_to_coords(self, contour: np.ndarray) -> List[List[float]]:
        """Converte un contorno di pixel in coordinate geografiche"""
        points = contour.reshape(-1, 2) if len(contour.shape) == 3 else contour
        coords = [list(self.pixel_to_coord(float(x), float(y))) for x, y in points]
        # Chiudi il poligono
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        return coords
    
    def coords_to_pixels(self, coords: List[List[float]]) -> List[List[int]]:
        """Converte coordinate geografiche in pixel"""
        pixels = [list(self.coord_to_pixel(lon, lat)) for lon, lat in coords]
        return pixels
    
    def get_bounds_dict(self) -> Dict:
        """Restituisce i confini come dizionario"""
        return {
            'north': self.north,
            'south': self.south,
            'east': self.east,
            'west': self.west
        }
