"""
Map Georeferencer - Convertitore da immagini di mappe a GeoJSON

Approccio migliorato:
1. Mappa mondiale GRANDE per selezione precisa dell'area
2. Checkbox per selezionare/deselezionare regioni estratte
3. Calibrazione manuale opzionale per maggiore precisione
4. Point-in-Polygon per identificazione regioni

Autore: Map to GeoJSON Converter Project
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import cv2
import geopandas as gpd
from shapely.geometry import Point, Polygon, mapping
import json
from dataclasses import dataclass
from typing import List, Optional, Tuple
import os


# Database dei paesi con bounding box predefiniti
COUNTRY_BOUNDS = {
    "Italia": {"bounds": (6.5, 36.0, 18.5, 47.5), "gadm_code": "ITA"},
    "Francia": {"bounds": (-5.5, 41.0, 10.0, 51.5), "gadm_code": "FRA"},
    "Germania": {"bounds": (5.5, 47.0, 15.5, 55.5), "gadm_code": "DEU"},
    "Spagna": {"bounds": (-9.5, 35.5, 4.5, 44.0), "gadm_code": "ESP"},
    "Regno Unito": {"bounds": (-8.5, 49.5, 2.0, 61.0), "gadm_code": "GBR"},
    "Polonia": {"bounds": (14.0, 49.0, 24.5, 55.0), "gadm_code": "POL"},
    "Svizzera": {"bounds": (5.5, 45.5, 10.5, 48.0), "gadm_code": "CHE"},
    "Austria": {"bounds": (9.5, 46.0, 17.5, 49.0), "gadm_code": "AUT"},
    "Portogallo": {"bounds": (-9.5, 36.5, -6.0, 42.5), "gadm_code": "PRT"},
    "Grecia": {"bounds": (19.0, 34.5, 30.0, 42.0), "gadm_code": "GRC"},
}


@dataclass
class Region:
    """Rappresenta una regione estratta dall'immagine"""
    contour: np.ndarray
    color: Tuple[int, int, int]
    centroid_pixel: Tuple[float, float]
    centroid_geo: Optional[Tuple[float, float]] = None
    name: Optional[str] = None
    gadm_geometry: Optional[object] = None
    area_pixels: float = 0
    enabled: bool = True  # Per checkbox selezione


class WorldMapSelector(tk.Toplevel):
    """Finestra popup con mappa mondiale grande per selezione area"""
    
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("🌍 Seleziona Area sulla Mappa Mondiale")
        self.geometry("900x600")
        self.callback = callback
        
        # Stato selezione
        self.selection_start = None
        self.selection_rect = None
        self.current_rect_id = None
        
        self._setup_ui()
        self._draw_world_map()
        
        # Rendi modale
        self.transient(parent)
        self.grab_set()
    
    def _setup_ui(self):
        """Crea interfaccia"""
        # Istruzioni
        instructions = ttk.Label(self, 
            text="🖱️ Clicca e trascina per selezionare l'area geografica della tua mappa\n"
                 "Oppure clicca su un paese predefinito sotto",
            font=('Arial', 11))
        instructions.pack(pady=10)
        
        # Canvas per mappa
        self.canvas = tk.Canvas(self, width=850, height=450, bg='#1a3a5c', 
                               highlightthickness=2, highlightbackground='#333')
        self.canvas.pack(pady=5)
        
        # Bind eventi mouse
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        
        # Frame pulsanti paesi
        countries_frame = ttk.LabelFrame(self, text="⚡ Selezione Rapida")
        countries_frame.pack(fill=tk.X, padx=10, pady=5)
        
        row1 = ttk.Frame(countries_frame)
        row1.pack(fill=tk.X, pady=2)
        
        for country in ["Italia", "Francia", "Germania", "Spagna", "Regno Unito"]:
            btn = ttk.Button(row1, text=country, 
                           command=lambda c=country: self._select_country(c))
            btn.pack(side=tk.LEFT, padx=5, pady=2)
        
        row2 = ttk.Frame(countries_frame)
        row2.pack(fill=tk.X, pady=2)
        
        for country in ["Polonia", "Svizzera", "Austria", "Portogallo", "Grecia"]:
            btn = ttk.Button(row2, text=country, 
                           command=lambda c=country: self._select_country(c))
            btn.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Info selezione
        self.info_var = tk.StringVar(value="Nessuna selezione")
        ttk.Label(self, textvariable=self.info_var, font=('Arial', 10, 'bold')).pack(pady=5)
        
        # Pulsanti conferma/annulla
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="✓ Conferma", command=self._confirm).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="✗ Annulla", command=self.destroy).pack(side=tk.LEFT, padx=10)
    
    def _draw_world_map(self):
        """Disegna mappa mondiale dettagliata"""
        canvas = self.canvas
        w, h = 850, 450
        
        # Parametri proiezione (Mercator semplificata)
        # Lon: -180 a 180 -> 0 a w
        # Lat: 85 a -85 -> 0 a h
        self.lon_to_x = lambda lon: (lon + 180) / 360 * w
        self.lat_to_y = lambda lat: (85 - lat) / 170 * h
        self.x_to_lon = lambda x: (x / w) * 360 - 180
        self.y_to_lat = lambda y: 85 - (y / h) * 170
        
        # Griglia
        for lon in range(-180, 181, 30):
            x = self.lon_to_x(lon)
            canvas.create_line(x, 0, x, h, fill='#2a4a6c', width=1)
            canvas.create_text(x, h-10, text=f"{lon}°", fill='#5a8abc', font=('Arial', 7))
        
        for lat in range(-60, 91, 30):
            y = self.lat_to_y(lat)
            canvas.create_line(0, y, w, y, fill='#2a4a6c', width=1)
            canvas.create_text(15, y, text=f"{lat}°", fill='#5a8abc', font=('Arial', 7))
        
        # Continenti (più dettagliati)
        continents = {
            'europe': [
                (-10, 36), (0, 36), (3, 38), (5, 43), (-2, 44), (-5, 43), 
                (-9, 39), (-9, 43), (-3, 48), (2, 51), (5, 51), (8, 54),
                (12, 54), (15, 55), (24, 55), (28, 54), (32, 46), (28, 41),
                (26, 40), (23, 35), (18, 40), (14, 41), (12, 44), (7, 44),
                (6, 46), (10, 46), (13, 47), (16, 48), (15, 51), (19, 51),
                (22, 54), (18, 56), (14, 55), (10, 54), (5, 49), (2, 49),
                (-5, 48), (-8, 44), (-10, 36)
            ],
            'africa': [
                (-17, 15), (-12, 15), (-5, 10), (0, 5), (10, 5), (15, 0),
                (20, -5), (30, -5), (40, -10), (45, -15), (40, -25),
                (35, -33), (25, -35), (18, -35), (15, -30), (12, -18),
                (15, -10), (10, 0), (5, 5), (-5, 5), (-10, 10), (-17, 15)
            ],
            'asia': [
                (30, 35), (35, 30), (45, 25), (55, 25), (65, 20), (75, 15),
                (80, 10), (90, 15), (95, 20), (105, 20), (110, 22), (120, 25),
                (125, 35), (130, 40), (135, 45), (140, 45), (145, 50),
                (150, 55), (160, 60), (170, 65), (180, 68), (180, 75),
                (170, 70), (160, 70), (140, 72), (120, 75), (100, 78),
                (80, 78), (70, 75), (60, 70), (50, 60), (40, 55), (30, 50),
                (25, 45), (27, 40), (30, 35)
            ],
            'north_america': [
                (-170, 65), (-160, 70), (-140, 70), (-120, 75), (-100, 78),
                (-80, 75), (-70, 70), (-60, 65), (-55, 55), (-65, 45),
                (-70, 42), (-75, 35), (-80, 25), (-85, 20), (-90, 18),
                (-100, 20), (-105, 22), (-115, 28), (-120, 35), (-125, 42),
                (-130, 50), (-140, 55), (-150, 60), (-160, 60), (-170, 65)
            ],
            'south_america': [
                (-80, 10), (-75, 5), (-70, 0), (-75, -5), (-70, -15),
                (-65, -25), (-70, -40), (-75, -50), (-70, -55), (-65, -55),
                (-60, -50), (-55, -40), (-50, -25), (-45, -20), (-40, -10),
                (-35, -5), (-50, 0), (-60, 5), (-75, 10), (-80, 10)
            ],
            'australia': [
                (115, -20), (125, -15), (135, -12), (145, -15), (150, -22),
                (150, -30), (145, -38), (140, -38), (135, -35), (130, -32),
                (125, -30), (118, -22), (115, -20)
            ]
        }
        
        for name, coords in continents.items():
            points = [(self.lon_to_x(lon), self.lat_to_y(lat)) for lon, lat in coords]
            canvas.create_polygon(points, fill='#3d7a4a', outline='#2d5a3a', width=1, 
                                 tags=name)
        
        # Etichette paesi principali
        labels = [
            ("Italia", 12, 43), ("Francia", 2, 47), ("Germania", 10, 51),
            ("Spagna", -3, 40), ("UK", -2, 54), ("Polonia", 19, 52),
            ("Grecia", 22, 39), ("Turchia", 35, 39), ("Russia", 90, 60),
            ("Cina", 105, 35), ("India", 80, 22), ("Giappone", 138, 36),
            ("Australia", 135, -25), ("USA", -100, 40), ("Canada", -100, 55),
            ("Brasile", -50, -10), ("Argentina", -65, -35), ("Sudafrica", 25, -30),
            ("Egitto", 30, 27), ("Nigeria", 8, 10)
        ]
        
        for name, lon, lat in labels:
            x, y = self.lon_to_x(lon), self.lat_to_y(lat)
            canvas.create_text(x, y, text=name, fill='white', font=('Arial', 8))
    
    def _on_press(self, event):
        """Inizio selezione"""
        self.selection_start = (event.x, event.y)
        if self.current_rect_id:
            self.canvas.delete(self.current_rect_id)
    
    def _on_drag(self, event):
        """Trascinamento selezione"""
        if self.selection_start:
            if self.current_rect_id:
                self.canvas.delete(self.current_rect_id)
            
            x1, y1 = self.selection_start
            x2, y2 = event.x, event.y
            
            self.current_rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2, outline='#ff0000', width=2, fill='#ff000033'
            )
            
            # Mostra coordinate
            lon1, lat1 = self.x_to_lon(x1), self.y_to_lat(y1)
            lon2, lat2 = self.x_to_lon(x2), self.y_to_lat(y2)
            
            self.selection_rect = (min(lon1, lon2), min(lat1, lat2), 
                                  max(lon1, lon2), max(lat1, lat2))
            
            self.info_var.set(f"Bounds: {self.selection_rect[0]:.1f}°, {self.selection_rect[1]:.1f}° → "
                             f"{self.selection_rect[2]:.1f}°, {self.selection_rect[3]:.1f}°")
    
    def _on_release(self, event):
        """Fine selezione"""
        pass
    
    def _select_country(self, country: str):
        """Seleziona un paese predefinito"""
        if country in COUNTRY_BOUNDS:
            bounds = COUNTRY_BOUNDS[country]["bounds"]
            self.selection_rect = bounds
            
            # Disegna rettangolo
            if self.current_rect_id:
                self.canvas.delete(self.current_rect_id)
            
            x1 = self.lon_to_x(bounds[0])
            y1 = self.lat_to_y(bounds[3])  # max lat = top
            x2 = self.lon_to_x(bounds[2])
            y2 = self.lat_to_y(bounds[1])  # min lat = bottom
            
            self.current_rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2, outline='#00ff00', width=3, fill='#00ff0033'
            )
            
            self.info_var.set(f"✓ {country}: {bounds[0]:.1f}°, {bounds[1]:.1f}° → "
                             f"{bounds[2]:.1f}°, {bounds[3]:.1f}°")
    
    def _confirm(self):
        """Conferma selezione"""
        if self.selection_rect:
            self.callback(self.selection_rect)
            self.destroy()
        else:
            messagebox.showwarning("Attenzione", "Seleziona prima un'area!")


class MapGeoreferencer:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Map Georeferencer - Convertitore Mappe → GeoJSON")
        self.root.geometry("1400x900")
        
        # Stato
        self.image: Optional[Image.Image] = None
        self.image_array: Optional[np.ndarray] = None
        self.tk_image: Optional[ImageTk.PhotoImage] = None
        self.regions: List[Region] = []
        self.gadm_gdf: Optional[gpd.GeoDataFrame] = None
        
        # Calibrazione
        self.geo_bounds: Optional[Tuple[float, float, float, float]] = None
        self.calibration_points: List[Tuple[Tuple[int, int], Tuple[float, float]]] = []
        self.calibration_mode = False
        
        # Visualizzazione
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        self._setup_ui()
        self._load_gadm_database()
    
    def _setup_ui(self):
        """Crea interfaccia"""
        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="📂 Carica Immagine", command=self._load_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🌍 Seleziona Area", command=self._open_world_map).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        ttk.Label(toolbar, text="N. Cluster:").pack(side=tk.LEFT, padx=2)
        self.n_regions_var = tk.IntVar(value=25)
        ttk.Spinbox(toolbar, from_=2, to=100, textvariable=self.n_regions_var, width=5).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(toolbar, text="🔍 Estrai Regioni", command=self._extract_regions).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🎯 Identifica", command=self._identify_regions).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="💾 Esporta GeoJSON", command=self._export_geojson).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        ttk.Button(toolbar, text="✓ Seleziona Tutto", command=self._select_all_regions).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✗ Deseleziona Tutto", command=self._deselect_all_regions).pack(side=tk.LEFT, padx=2)
        
        # Main area
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas sinistro
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=3)
        
        canvas_frame = ttk.Frame(left_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bg='#2b2b2b', highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        v_scroll = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll = ttk.Scrollbar(left_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        
        # Pannello destro
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=1)
        
        # Info area
        info_frame = ttk.LabelFrame(right_frame, text="📍 Area Geografica")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.bounds_label = ttk.Label(info_frame, text="Nessuna area selezionata\nClicca '🌍 Seleziona Area'")
        self.bounds_label.pack(pady=10)
        
        # Lista regioni con checkbox
        regions_frame = ttk.LabelFrame(right_frame, text="📋 Regioni Estratte (clicca per selezionare/deselezionare)")
        regions_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollable frame per checkbox
        canvas_scroll = tk.Canvas(regions_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(regions_frame, orient=tk.VERTICAL, command=canvas_scroll.yview)
        self.regions_container = ttk.Frame(canvas_scroll)
        
        self.regions_container.bind(
            "<Configure>",
            lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all"))
        )
        
        canvas_scroll.create_window((0, 0), window=self.regions_container, anchor="nw")
        canvas_scroll.configure(yscrollcommand=scrollbar.set)
        
        canvas_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.region_checkboxes = []
        
        # Status bar
        self.status_var = tk.StringVar(value="Pronto. Carica un'immagine e seleziona l'area geografica.")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN).pack(side=tk.BOTTOM, fill=tk.X)
    
    def _open_world_map(self):
        """Apre finestra selezione mappa mondiale"""
        WorldMapSelector(self.root, self._on_area_selected)
    
    def _on_area_selected(self, bounds: Tuple[float, float, float, float]):
        """Callback quando viene selezionata un'area"""
        self.geo_bounds = bounds
        self.bounds_label.config(
            text=f"Lon: {bounds[0]:.2f}° → {bounds[2]:.2f}°\n"
                 f"Lat: {bounds[1]:.2f}° → {bounds[3]:.2f}°"
        )
        self.status_var.set(f"✓ Area selezionata: {bounds}")
    
    def _load_gadm_database(self):
        """Carica database GADM"""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        gadm_path = os.path.join(script_dir, "geodata", "gadm_italy", "gadm41_ITA_1.shp")
        
        if os.path.exists(gadm_path):
            try:
                self.gadm_gdf = gpd.read_file(gadm_path)
                self.status_var.set(f"✓ Database GADM: {len(self.gadm_gdf)} regioni italiane")
            except Exception as e:
                self.gadm_gdf = None
        else:
            self.gadm_gdf = None
    
    def _load_image(self):
        """Carica immagine"""
        filetypes = [("Immagini", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff"), ("Tutti", "*.*")]
        filepath = filedialog.askopenfilename(title="Seleziona immagine mappa", filetypes=filetypes)
        
        if filepath:
            try:
                self.image = Image.open(filepath)
                self.image_array = np.array(self.image)
                self._display_image()
                self.status_var.set(f"✓ Immagine: {self.image.width}x{self.image.height} px")
                self.regions = []
                self._update_regions_list()
            except Exception as e:
                messagebox.showerror("Errore", f"Errore caricamento:\n{e}")
    
    def _display_image(self):
        """Mostra immagine"""
        if self.image is None:
            return
        
        canvas_w = self.canvas.winfo_width() or 800
        canvas_h = self.canvas.winfo_height() or 600
        
        img_w, img_h = self.image.size
        scale_w = canvas_w / img_w
        scale_h = canvas_h / img_h
        self.scale = min(scale_w, scale_h, 1.0)
        
        new_w = int(img_w * self.scale)
        new_h = int(img_h * self.scale)
        
        resized = self.image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        
        self.offset_x = (canvas_w - new_w) // 2
        self.offset_y = (canvas_h - new_h) // 2
        
        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, 
                                image=self.tk_image, tags="image")
    
    def _on_scroll(self, event):
        """Zoom"""
        if event.delta > 0:
            self.scale *= 1.1
        else:
            self.scale /= 1.1
        self.scale = max(0.1, min(5.0, self.scale))
        self._display_image()
        self._draw_regions_overlay()
    
    def _extract_regions(self):
        """Estrai regioni con K-Means"""
        if self.image_array is None:
            messagebox.showwarning("Attenzione", "Carica prima un'immagine!")
            return
        
        self.status_var.set("⏳ Estrazione in corso...")
        self.root.update()
        
        try:
            n_clusters = self.n_regions_var.get()
            
            # Prepara immagine
            if len(self.image_array.shape) == 2:
                img_rgb = cv2.cvtColor(self.image_array, cv2.COLOR_GRAY2RGB)
            elif self.image_array.shape[2] == 4:
                img_rgb = cv2.cvtColor(self.image_array, cv2.COLOR_RGBA2RGB)
            else:
                img_rgb = self.image_array.copy()
            
            # K-Means
            pixels = img_rgb.reshape(-1, 3).astype(np.float32)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
            _, labels, centers = cv2.kmeans(pixels, n_clusters, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
            
            centers = centers.astype(np.uint8)
            labels = labels.flatten()
            segmented = centers[labels].reshape(img_rgb.shape)
            
            # Estrai contorni
            self.regions = []
            
            for i, center in enumerate(centers):
                mask = np.all(segmented == center, axis=2).astype(np.uint8) * 255
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if contours:
                    largest = max(contours, key=cv2.contourArea)
                    area = cv2.contourArea(largest)
                    
                    if area > 100:
                        M = cv2.moments(largest)
                        if M["m00"] > 0:
                            cx = M["m10"] / M["m00"]
                            cy = M["m01"] / M["m00"]
                            
                            self.regions.append(Region(
                                contour=largest,
                                color=tuple(int(c) for c in center),
                                centroid_pixel=(cx, cy),
                                area_pixels=area,
                                enabled=True
                            ))
            
            self.regions.sort(key=lambda r: r.area_pixels, reverse=True)
            self._update_regions_list()
            self._draw_regions_overlay()
            
            self.status_var.set(f"✓ Estratte {len(self.regions)} regioni")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore estrazione:\n{e}")
    
    def _update_regions_list(self):
        """Aggiorna lista checkbox regioni"""
        # Pulisci
        for widget in self.regions_container.winfo_children():
            widget.destroy()
        self.region_checkboxes = []
        
        for i, region in enumerate(self.regions):
            frame = ttk.Frame(self.regions_container)
            frame.pack(fill=tk.X, pady=1)
            
            # Checkbox
            var = tk.BooleanVar(value=region.enabled)
            cb = ttk.Checkbutton(frame, variable=var,
                                command=lambda idx=i, v=var: self._toggle_region(idx, v))
            cb.pack(side=tk.LEFT)
            
            # Colore
            color_hex = f"#{region.color[0]:02x}{region.color[1]:02x}{region.color[2]:02x}"
            color_label = tk.Label(frame, text="■", fg=color_hex, font=('Arial', 14))
            color_label.pack(side=tk.LEFT, padx=2)
            
            # Nome
            name = region.name or f"Regione {i+1}"
            status = "✓" if region.name else "?"
            ttk.Label(frame, text=f"{name} {status}").pack(side=tk.LEFT, padx=5)
            
            self.region_checkboxes.append((var, region))
    
    def _toggle_region(self, idx: int, var: tk.BooleanVar):
        """Toggle selezione regione"""
        if idx < len(self.regions):
            self.regions[idx].enabled = var.get()
            self._draw_regions_overlay()
    
    def _select_all_regions(self):
        """Seleziona tutte le regioni"""
        for i, region in enumerate(self.regions):
            region.enabled = True
        for var, _ in self.region_checkboxes:
            var.set(True)
        self._draw_regions_overlay()
    
    def _deselect_all_regions(self):
        """Deseleziona tutte le regioni"""
        for i, region in enumerate(self.regions):
            region.enabled = False
        for var, _ in self.region_checkboxes:
            var.set(False)
        self._draw_regions_overlay()
    
    def _draw_regions_overlay(self):
        """Disegna overlay regioni"""
        if self.image is None or not self.regions:
            return
        
        overlay = self.image.copy()
        draw = ImageDraw.Draw(overlay, 'RGBA')
        
        for region in self.regions:
            points = [(int(p[0][0] * self.scale + self.offset_x), 
                      int(p[0][1] * self.scale + self.offset_y)) 
                     for p in region.contour]
            
            if len(points) > 2:
                if region.enabled:
                    # Verde se abilitata
                    draw.polygon(points, outline=(0, 255, 0, 200), fill=None)
                    
                    # Centroide
                    cx, cy = region.centroid_pixel
                    cx_s = int(cx * self.scale + self.offset_x)
                    cy_s = int(cy * self.scale + self.offset_y)
                    r = 5
                    draw.ellipse([cx_s-r, cy_s-r, cx_s+r, cy_s+r], fill=(255, 255, 0, 200))
                else:
                    # Rosso tratteggiato se disabilitata
                    draw.polygon(points, outline=(255, 0, 0, 100), fill=None)
        
        self.tk_image = ImageTk.PhotoImage(overlay)
        self.canvas.delete("all")
        self.canvas.create_image(self.offset_x, self.offset_y, anchor=tk.NW, 
                                image=self.tk_image, tags="image")
    
    def _identify_regions(self):
        """Identifica regioni con Point-in-Polygon"""
        enabled_regions = [r for r in self.regions if r.enabled]
        
        if not enabled_regions:
            messagebox.showwarning("Attenzione", "Nessuna regione selezionata!")
            return
        
        if self.gadm_gdf is None:
            messagebox.showwarning("Attenzione", "Database GADM non disponibile!")
            return
        
        if self.geo_bounds is None:
            messagebox.showwarning("Attenzione", "Seleziona prima l'area geografica!")
            return
        
        self.status_var.set("⏳ Identificazione in corso...")
        self.root.update()
        
        try:
            min_lon, min_lat, max_lon, max_lat = self.geo_bounds
            img_w, img_h = self.image.size
            
            matched = 0
            
            for region in enabled_regions:
                cx, cy = region.centroid_pixel
                
                # Pixel -> Coordinate geografiche
                lon = min_lon + (cx / img_w) * (max_lon - min_lon)
                lat = max_lat - (cy / img_h) * (max_lat - min_lat)
                
                region.centroid_geo = (lon, lat)
                
                # Cerca regione GADM
                point = Point(lon, lat)
                
                for idx, row in self.gadm_gdf.iterrows():
                    if row.geometry and row.geometry.contains(point):
                        region.name = row.get('NAME_1', f"Region {idx}")
                        region.gadm_geometry = row.geometry
                        matched += 1
                        break
            
            self._update_regions_list()
            self._draw_regions_overlay()
            
            self.status_var.set(f"✓ Identificate {matched}/{len(enabled_regions)} regioni")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore identificazione:\n{e}")
    
    def _export_geojson(self):
        """Esporta GeoJSON"""
        identified = [r for r in self.regions if r.enabled and r.gadm_geometry]
        
        if not identified:
            messagebox.showwarning("Attenzione", "Nessuna regione identificata da esportare!")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Salva GeoJSON",
            defaultextension=".geojson",
            filetypes=[("GeoJSON", "*.geojson"), ("JSON", "*.json")]
        )
        
        if filepath:
            try:
                features = []
                
                for region in identified:
                    features.append({
                        "type": "Feature",
                        "properties": {
                            "name": region.name,
                            "color": f"#{region.color[0]:02x}{region.color[1]:02x}{region.color[2]:02x}",
                        },
                        "geometry": mapping(region.gadm_geometry)
                    })
                
                geojson = {"type": "FeatureCollection", "features": features}
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(geojson, f, indent=2, ensure_ascii=False)
                
                self.status_var.set(f"✓ Esportato: {filepath}")
                messagebox.showinfo("Successo", f"Esportate {len(features)} regioni!")
                
            except Exception as e:
                messagebox.showerror("Errore", f"Errore esportazione:\n{e}")


def main():
    root = tk.Tk()
    app = MapGeoreferencer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
