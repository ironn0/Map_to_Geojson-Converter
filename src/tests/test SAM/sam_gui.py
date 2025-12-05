"""
SAM Map Segmenter - GUI Version

A graphical interface for using SAM to extract map regions.
Combines SAM's powerful segmentation with manual review.

Author: Map to GeoJSON Converter Project
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import cv2
from pathlib import Path
import json
from typing import List, Optional, Tuple
import threading

# Try to import SAM
try:
    from sam_segmenter import SAMSegmenter, ExtractedRegion, RegionMatcher, TRANSFORMERS_AVAILABLE
    GEOPANDAS_AVAILABLE = RegionMatcher is not None
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    GEOPANDAS_AVAILABLE = False
    SAMSegmenter = None
    ExtractedRegion = None
    RegionMatcher = None

# Try to import interactive map viewer
try:
    from interactive_map import InteractiveMapViewer, MapSelectionDialog
    FOLIUM_AVAILABLE = True
except ImportError:
    try:
        import folium
        from interactive_map import InteractiveMapViewer, MapSelectionDialog
        FOLIUM_AVAILABLE = True
    except ImportError:
        FOLIUM_AVAILABLE = False
        InteractiveMapViewer = None
        MapSelectionDialog = None


class SAMMapGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("­ƒñû SAM Map Segmenter")
        self.root.geometry("1400x900")
        
        # State
        self.image: Optional[Image.Image] = None
        self.image_path: Optional[str] = None
        self.tk_image: Optional[ImageTk.PhotoImage] = None
        self.regions: List = []
        self.segmenter = None  # SAMSegmenter instance
        self.clicked_points: List[Tuple[int, int]] = []
        self.region_matcher = None  # RegionMatcher instance
        self.identified_regions: dict = {}  # region_idx -> region_name
        self.real_geometries: dict = {}  # region_idx -> shapely geometry
        
        # Geo bounds (lat/lon bounding box)
        # Default: Italy
        self.geo_bounds = {
            'north': 47.1,  # max lat
            'south': 35.5,  # min lat  
            'east': 18.5,   # max lon
            'west': 6.6     # min lon
        }
        
        # Mode: 'auto' or 'points'
        self.mode = 'auto'
        
        self._setup_ui()
        self._check_dependencies()
    
    def _setup_ui(self):
        """Create the GUI"""
        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="­ƒôé Load Image", command=self._load_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="­ƒöº Load SAM", command=self._load_sam).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Mode selection
        ttk.Label(toolbar, text="Mode:").pack(side=tk.LEFT, padx=2)
        self.mode_var = tk.StringVar(value="auto")
        ttk.Radiobutton(toolbar, text="Auto", variable=self.mode_var, value="auto").pack(side=tk.LEFT)
        ttk.Radiobutton(toolbar, text="Click Points", variable=self.mode_var, value="points").pack(side=tk.LEFT)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        ttk.Button(toolbar, text="­ƒöì Segment", command=self._run_segmentation).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="­ƒùæ´©Å Clear Points", command=self._clear_points).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="­ƒîì Identify Regions", command=self._identify_regions).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="­ƒÆ¥ Export Found", command=self._export_all_matched).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="­ƒôÑ Export ALL DB", command=self._export_entire_database).pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Interactive map button
        self.map_btn = ttk.Button(toolbar, text="­ƒù║´©Å Interactive Map", command=self._show_interactive_map)
        self.map_btn.pack(side=tk.LEFT, padx=2)
        if not FOLIUM_AVAILABLE:
            self.map_btn.configure(state=tk.DISABLED)
        
        # Main area
        main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left: Image canvas
        left_frame = ttk.Frame(main_pane)
        main_pane.add(left_frame, weight=3)
        
        self.canvas = tk.Canvas(left_frame, bg='#2b2b2b', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        
        # Right: Controls and region list
        right_frame = ttk.Frame(main_pane)
        main_pane.add(right_frame, weight=1)
        
        # Model info
        model_frame = ttk.LabelFrame(right_frame, text="­ƒñû SAM Model")
        model_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.model_status = ttk.Label(model_frame, text="Not loaded")
        self.model_status.pack(pady=5)
        
        ttk.Label(model_frame, text="Model:").pack(anchor=tk.W, padx=5)
        self.model_var = tk.StringVar(value="facebook/sam-vit-base")
        model_combo = ttk.Combobox(model_frame, textvariable=self.model_var, values=[
            "facebook/sam-vit-base",
            "facebook/sam-vit-large", 
            "facebook/sam-vit-huge"
        ])
        model_combo.pack(fill=tk.X, padx=5, pady=2)
        
        # Segmentation settings
        settings_frame = ttk.LabelFrame(right_frame, text="ÔÜÖ´©Å Settings")
        settings_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Min Area (pixels):").pack(anchor=tk.W, padx=5)
        self.min_area_var = tk.IntVar(value=1000)
        ttk.Spinbox(settings_frame, from_=100, to=10000, textvariable=self.min_area_var).pack(fill=tk.X, padx=5, pady=2)
        
        ttk.Label(settings_frame, text="Points per Side (auto mode):").pack(anchor=tk.W, padx=5)
        self.points_var = tk.IntVar(value=32)
        ttk.Spinbox(settings_frame, from_=8, to=64, textvariable=self.points_var).pack(fill=tk.X, padx=5, pady=2)
        
        # Geographic Database settings
        geo_frame = ttk.LabelFrame(right_frame, text="­ƒîì Geographic Database")
        geo_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(geo_frame, text="Database:").pack(anchor=tk.W, padx=5)
        self.db_var = tk.StringVar(value="natural_earth")
        db_combo = ttk.Combobox(geo_frame, textvariable=self.db_var, values=[
            "natural_earth",
            "gadm_italy"
        ], state="readonly")
        db_combo.pack(fill=tk.X, padx=5, pady=2)
        
        # Country filter (for Natural Earth)
        ttk.Label(geo_frame, text="Filter by Country:").pack(anchor=tk.W, padx=5)
        self.country_var = tk.StringVar(value="Italy")
        country_combo = ttk.Combobox(geo_frame, textvariable=self.country_var, values=[
            "Italy", "France", "Germany", "Spain", "United Kingdom",
            "Poland", "Netherlands", "Belgium", "Austria", "Switzerland",
            "Portugal", "Greece", "Sweden", "Norway", "Finland",
            "United States", "Canada", "Mexico", "Brazil", "Argentina",
            "China", "Japan", "India", "Australia", ""
        ])
        country_combo.pack(fill=tk.X, padx=5, pady=2)
        
        self.db_status = ttk.Label(geo_frame, text="Not loaded")
        self.db_status.pack(pady=2)
        
        ttk.Button(geo_frame, text="­ƒôé Load Database", command=self._load_database).pack(pady=5)
        
        # Geo Bounds - PRESETS
        bounds_frame = ttk.LabelFrame(geo_frame, text="Map Bounds (lat/lon)")
        bounds_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Preset buttons
        preset_frame = ttk.Frame(bounds_frame)
        preset_frame.pack(fill=tk.X, padx=5, pady=2)
        ttk.Button(preset_frame, text="­ƒç«­ƒç╣ Italy", width=8, 
                   command=lambda: self._set_preset_bounds("Italy")).pack(side=tk.LEFT, padx=1)
        ttk.Button(preset_frame, text="­ƒç¬­ƒç║ Europe", width=8,
                   command=lambda: self._set_preset_bounds("Europe")).pack(side=tk.LEFT, padx=1)
        ttk.Button(preset_frame, text="­ƒîì World", width=8,
                   command=lambda: self._set_preset_bounds("World")).pack(side=tk.LEFT, padx=1)
        
        bounds_grid = ttk.Frame(bounds_frame)
        bounds_grid.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(bounds_grid, text="North:").grid(row=0, column=0, sticky=tk.W)
        self.north_var = tk.DoubleVar(value=47.1)
        ttk.Entry(bounds_grid, textvariable=self.north_var, width=10).grid(row=0, column=1)
        
        ttk.Label(bounds_grid, text="South:").grid(row=1, column=0, sticky=tk.W)
        self.south_var = tk.DoubleVar(value=35.5)
        ttk.Entry(bounds_grid, textvariable=self.south_var, width=10).grid(row=1, column=1)
        
        ttk.Label(bounds_grid, text="East:").grid(row=2, column=0, sticky=tk.W)
        self.east_var = tk.DoubleVar(value=18.5)
        ttk.Entry(bounds_grid, textvariable=self.east_var, width=10).grid(row=2, column=1)
        
        ttk.Label(bounds_grid, text="West:").grid(row=3, column=0, sticky=tk.W)
        self.west_var = tk.DoubleVar(value=6.6)
        ttk.Entry(bounds_grid, textvariable=self.west_var, width=10).grid(row=3, column=1)
        
        ttk.Button(bounds_frame, text="­ƒîÉ Set from Database", command=self._set_bounds_from_db).pack(pady=2)
        
        # Regions list
        regions_frame = ttk.LabelFrame(right_frame, text="­ƒôï Extracted Regions")
        regions_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ("id", "name", "area", "score")
        self.regions_tree = ttk.Treeview(regions_frame, columns=columns, show="headings", height=12)
        self.regions_tree.heading("id", text="ID")
        self.regions_tree.heading("name", text="Name")
        self.regions_tree.heading("area", text="Area")
        self.regions_tree.heading("score", text="Score")
        self.regions_tree.column("id", width=30)
        self.regions_tree.column("name", width=120)
        self.regions_tree.column("area", width=60)
        self.regions_tree.column("score", width=50)
        
        scrollbar = ttk.Scrollbar(regions_frame, orient=tk.VERTICAL, command=self.regions_tree.yview)
        self.regions_tree.configure(yscrollcommand=scrollbar.set)
        
        self.regions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Load an image and SAM model to begin.")
        ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN).pack(side=tk.BOTTOM, fill=tk.X)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.root, mode='indeterminate')
    
    def _check_dependencies(self):
        """Check if required packages are installed"""
        if not TRANSFORMERS_AVAILABLE:
            messagebox.showwarning(
                "Missing Dependencies",
                "transformers and torch are not installed.\n\n"
                "Install them with:\n"
                "pip install transformers torch pillow numpy opencv-python"
            )
            self.model_status.config(text="ÔØî Dependencies missing")
    
    def _load_image(self):
        """Load an image file"""
        filetypes = [("Images", "*.png *.jpg *.jpeg *.bmp *.tiff"), ("All", "*.*")]
        filepath = filedialog.askopenfilename(title="Select Map Image", filetypes=filetypes)
        
        if filepath:
            try:
                self.image = Image.open(filepath).convert("RGB")
                self.image_path = filepath
                self._display_image()
                self.status_var.set(f"Ô£à Loaded: {Path(filepath).name} ({self.image.width}x{self.image.height})")
                self.regions = []
                self.clicked_points = []
                self._update_regions_tree()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image:\n{e}")
    
    def _display_image(self, overlay_regions: bool = True):
        """Display the image on canvas"""
        if self.image is None:
            return
        
        # Calculate scale to fit canvas
        canvas_w = self.canvas.winfo_width() or 800
        canvas_h = self.canvas.winfo_height() or 600
        
        img_w, img_h = self.image.size
        scale = min(canvas_w / img_w, canvas_h / img_h, 1.0)
        
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)
        
        # Create display image
        display = self.image.copy()
        
        # Draw regions if available
        if overlay_regions and self.regions:
            draw = ImageDraw.Draw(display, 'RGBA')
            for i, region in enumerate(self.regions):
                # Draw contour
                points = [(int(p[0]), int(p[1])) for p in region.contour.squeeze()]
                if len(points) > 2:
                    color = (np.random.randint(50, 255), np.random.randint(50, 255), np.random.randint(50, 255))
                    draw.polygon(points, outline=color + (255,), fill=None)
                    
                    # Draw centroid
                    cx, cy = int(region.centroid[0]), int(region.centroid[1])
                    r = 5
                    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(255, 255, 0, 200))
        
        # Draw clicked points
        if self.clicked_points:
            draw = ImageDraw.Draw(display, 'RGBA')
            for i, (x, y) in enumerate(self.clicked_points):
                r = 8
                draw.ellipse([x-r, y-r, x+r, y+r], fill=(255, 0, 0, 200), outline=(255, 255, 255, 255))
                draw.text((x+10, y-10), str(i+1), fill=(255, 255, 255, 255))
        
        # Resize and display
        resized = display.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        
        self.canvas.delete("all")
        offset_x = (canvas_w - new_w) // 2
        offset_y = (canvas_h - new_h) // 2
        self.canvas.create_image(offset_x, offset_y, anchor=tk.NW, image=self.tk_image)
        
        # Store offset and scale for click detection
        self._display_offset = (offset_x, offset_y)
        self._display_scale = scale
    
    def _on_canvas_click(self, event):
        """Handle canvas click for point mode"""
        if self.mode_var.get() != "points" or self.image is None:
            return
        
        # Convert canvas coords to image coords
        offset_x, offset_y = getattr(self, '_display_offset', (0, 0))
        scale = getattr(self, '_display_scale', 1.0)
        
        img_x = int((event.x - offset_x) / scale)
        img_y = int((event.y - offset_y) / scale)
        
        # Check bounds
        if 0 <= img_x < self.image.width and 0 <= img_y < self.image.height:
            self.clicked_points.append((img_x, img_y))
            self._display_image()
            self.status_var.set(f"­ƒôì Point {len(self.clicked_points)} added at ({img_x}, {img_y})")
    
    def _clear_points(self):
        """Clear clicked points"""
        self.clicked_points = []
        self._display_image()
        self.status_var.set("­ƒùæ´©Å Points cleared")
    
    def _load_sam(self):
        """Load the SAM model"""
        if not TRANSFORMERS_AVAILABLE:
            messagebox.showerror("Error", "transformers and torch are required!")
            return
        
        model_name = self.model_var.get()
        self.status_var.set(f"ÔÅ│ Loading {model_name}... This may take a few minutes.")
        self.progress.pack(side=tk.BOTTOM, fill=tk.X)
        self.progress.start()
        self.root.update()
        
        def load_thread():
            try:
                self.segmenter = SAMSegmenter(model_name=model_name)
                self.root.after(0, lambda: self._on_sam_loaded(True))
            except Exception as e:
                self.root.after(0, lambda: self._on_sam_loaded(False, str(e)))
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def _on_sam_loaded(self, success: bool, error: str = None):
        """Callback when SAM loading is complete"""
        self.progress.stop()
        self.progress.pack_forget()
        
        if success:
            self.model_status.config(text=f"Ô£à {self.model_var.get()}")
            self.status_var.set("Ô£à SAM model loaded successfully!")
        else:
            self.model_status.config(text="ÔØî Load failed")
            self.status_var.set(f"ÔØî Failed to load SAM: {error}")
            messagebox.showerror("Error", f"Failed to load SAM:\n{error}")
    
    def _run_segmentation(self):
        """Run SAM segmentation"""
        if self.segmenter is None:
            messagebox.showwarning("Warning", "Please load SAM model first!")
            return
        
        if self.image is None:
            messagebox.showwarning("Warning", "Please load an image first!")
            return
        
        mode = self.mode_var.get()
        
        if mode == "points" and not self.clicked_points:
            messagebox.showwarning("Warning", "Click some points on the image first!")
            return
        
        self.status_var.set("ÔÅ│ Running segmentation...")
        self.progress.pack(side=tk.BOTTOM, fill=tk.X)
        self.progress.start()
        self.root.update()
        
        def segment_thread():
            try:
                if mode == "auto":
                    regions = self.segmenter.segment_automatic(
                        self.image_path,
                        points_per_side=self.points_var.get(),
                        min_area=self.min_area_var.get()
                    )
                else:
                    regions = self.segmenter.segment_with_points(
                        self.image_path,
                        self.clicked_points
                    )
                
                self.root.after(0, lambda: self._on_segmentation_done(regions))
            except Exception as e:
                self.root.after(0, lambda: self._on_segmentation_error(str(e)))
        
        threading.Thread(target=segment_thread, daemon=True).start()
    
    def _on_segmentation_done(self, regions):
        """Callback when segmentation is complete"""
        self.progress.stop()
        self.progress.pack_forget()
        
        self.regions = regions
        self._display_image()
        self._update_regions_tree()
        self.status_var.set(f"Ô£à Found {len(regions)} regions")
    
    def _on_segmentation_error(self, error: str):
        """Callback when segmentation fails"""
        self.progress.stop()
        self.progress.pack_forget()
        self.status_var.set(f"ÔØî Segmentation failed: {error}")
        messagebox.showerror("Error", f"Segmentation failed:\n{error}")
    
    def _update_regions_tree(self):
        """Update the regions treeview"""
        self.regions_tree.delete(*self.regions_tree.get_children())
        
        for i, region in enumerate(self.regions):
            name = self.identified_regions.get(i, "?")
            self.regions_tree.insert("", tk.END, values=(
                i + 1,
                name,
                f"{region.area:.0f}",
                f"{region.score:.2f}"
            ))
    
    def _load_database(self):
        """Load the geographic database"""
        if not GEOPANDAS_AVAILABLE:
            messagebox.showerror("Error", "geopandas is required for database matching!\n\nInstall with:\npip install geopandas shapely")
            return
        
        db_type = self.db_var.get()
        
        # Paths to shapefiles
        base_path = Path(__file__).parent
        
        if db_type == "natural_earth":
            shapefile = base_path / ".." / "test comparison" / "geodata" / "ne_10m_admin_1_states_provinces" / "ne_10m_admin_1_states_provinces.shp"
            name_field = "name"
        elif db_type == "gadm_italy":
            shapefile = base_path / ".." / "georeferencer" / "geodata" / "gadm_italy" / "gadm41_ITA_1.shp"
            name_field = "NAME_1"
        else:
            messagebox.showerror("Error", f"Unknown database: {db_type}")
            return
        
        shapefile = shapefile.resolve()
        
        if not shapefile.exists():
            messagebox.showerror("Error", f"Shapefile not found:\n{shapefile}\n\nPlease download the geodata first.")
            return
        
        country_filter = self.country_var.get().strip()
        
        self.status_var.set(f"Loading {db_type} database...")
        self.progress.pack(side=tk.BOTTOM, fill=tk.X)
        self.progress.start()
        self.root.update()
        
        def load_thread():
            try:
                self.region_matcher = RegionMatcher(str(shapefile), name_field=name_field)
                
                # Apply country filter for Natural Earth
                if db_type == "natural_earth" and country_filter:
                    self.region_matcher.filter_by_country(country_filter)
                
                self.root.after(0, lambda: self._on_database_loaded(True, len(self.region_matcher.gdf)))
            except Exception as e:
                self.root.after(0, lambda: self._on_database_loaded(False, error=str(e)))
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def _on_database_loaded(self, success: bool, count: int = 0, error: str = None):
        """Callback when database loading is complete"""
        self.progress.stop()
        self.progress.pack_forget()
        
        if success:
            self.db_status.config(text=f"Ô£à {count} regions")
            self.status_var.set(f"Database loaded: {count} regions")
        else:
            self.db_status.config(text="ÔØî Load failed")
            self.status_var.set(f"Failed to load database: {error}")
            messagebox.showerror("Error", f"Failed to load database:\n{error}")
    
    def _set_preset_bounds(self, preset: str):
        """Set bounds from preset"""
        presets = {
            "Italy": (6.6, 35.5, 18.5, 47.1),
            "Europe": (-10, 35, 40, 70),
            "World": (-180, -90, 180, 90),
            "France": (-5, 41, 10, 51),
            "Germany": (5.5, 47, 15.5, 55.5),
            "Spain": (-9.5, 35.5, 4.5, 44),
            "USA": (-125, 24, -66, 50),
        }
        
        if preset in presets:
            west, south, east, north = presets[preset]
            self.west_var.set(west)
            self.south_var.set(south)
            self.east_var.set(east)
            self.north_var.set(north)
            self.status_var.set(f"Bounds set to {preset}")
    
    def _set_bounds_from_db(self):
        """Set geo bounds from database extent"""
        if self.region_matcher is None:
            messagebox.showwarning("Warning", "Please load a database first!")
            return
        
        bounds = self.region_matcher.gdf.total_bounds  # [minx, miny, maxx, maxy]
        self.west_var.set(round(bounds[0], 2))
        self.south_var.set(round(bounds[1], 2))
        self.east_var.set(round(bounds[2], 2))
        self.north_var.set(round(bounds[3], 2))
        
        self.status_var.set(f"Ô£à Bounds set from database: N={bounds[3]:.2f} S={bounds[1]:.2f} E={bounds[2]:.2f} W={bounds[0]:.2f}")
    
    def _identify_regions(self):
        """Identify extracted regions using the database"""
        if not self.regions:
            messagebox.showwarning("Warning", "No regions to identify! Run segmentation first.")
            return
        
        if self.region_matcher is None:
            messagebox.showwarning("Warning", "Please load a geographic database first!")
            return
        
        if self.image is None:
            messagebox.showwarning("Warning", "No image loaded!")
            return
        
        # Get current bounds
        geo_bounds = {
            'north': self.north_var.get(),
            'south': self.south_var.get(),
            'east': self.east_var.get(),
            'west': self.west_var.get()
        }
        
        self.status_var.set("ÔÅ│ Identifying regions...")
        self.progress.pack(side=tk.BOTTOM, fill=tk.X)
        self.progress.start()
        self.root.update()
        
        def identify_thread():
            try:
                names, geometries = self.region_matcher.identify_regions(
                    self.regions,
                    geo_bounds,
                    self.image.size
                )
                self.root.after(0, lambda: self._on_identify_done(names, geometries))
            except Exception as e:
                self.root.after(0, lambda: self._on_identify_error(str(e)))
        
        threading.Thread(target=identify_thread, daemon=True).start()
    
    def _on_identify_done(self, names: dict, geometries: dict):
        """Callback when identification is complete"""
        self.progress.stop()
        self.progress.pack_forget()
        
        self.identified_regions = names
        self.real_geometries = geometries
        self._update_regions_tree()
        
        # Count identified
        identified = sum(1 for name in names.values() if name != "Unknown")
        self.status_var.set(f"Identified {identified}/{len(self.regions)} regions (only these will be exported with real boundaries)")
    
    def _on_identify_error(self, error: str):
        """Callback when identification fails"""
        self.progress.stop()
        self.progress.pack_forget()
        self.status_var.set(f"ÔØî Identification failed: {error}")
        messagebox.showerror("Error", f"Identification failed:\n{error}")
    
    def _export_geojson(self):
        """Export regions to GeoJSON"""
        if not self.regions:
            messagebox.showwarning("Warning", "No regions to export!")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Save GeoJSON",
            defaultextension=".geojson",
            filetypes=[("GeoJSON", "*.geojson"), ("JSON", "*.json")]
        )
        
        if filepath:
            try:
                # Get geo bounds if available
                geo_bounds = None
                if self.identified_regions:
                    geo_bounds = {
                        'north': self.north_var.get(),
                        'south': self.south_var.get(),
                        'east': self.east_var.get(),
                        'west': self.west_var.get()
                    }
                
                result = self.segmenter.export_geojson(
                    self.regions, 
                    filepath,
                    image_size=self.image.size,
                    region_names=self.identified_regions if self.identified_regions else None,
                    geo_bounds=geo_bounds,
                    real_geometries=self.real_geometries if self.real_geometries else None
                )
                exported_count = len(result.get('features', []))
                self.status_var.set(f"Exported to: {filepath}")
                messagebox.showinfo("Success", f"Exported {exported_count} identified regions with real boundaries!\n\nUnidentified regions were skipped.")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed:\n{e}")
    
    def _export_all_matched(self):
        """Export ALL database regions found in the image"""
        if self.region_matcher is None:
            messagebox.showwarning("Warning", "Please load a database and run identification first!")
            return
        
        matched = self.region_matcher.get_all_matched_regions()
        if not matched:
            messagebox.showwarning("Warning", "No regions identified yet! Run 'Identify Regions' first.")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Save All Found Regions",
            defaultextension=".geojson",
            filetypes=[("GeoJSON", "*.geojson"), ("JSON", "*.json")]
        )
        
        if filepath:
            try:
                result = self.region_matcher.export_matched_regions_geojson(filepath)
                exported_count = len(result.get('features', []))
                self.status_var.set(f"Exported {exported_count} regions to: {filepath}")
                
                # Show list of exported regions
                region_names = [r['name'] for r in matched]
                names_text = ", ".join(region_names[:10])
                if len(region_names) > 10:
                    names_text += f"... and {len(region_names) - 10} more"
                
                messagebox.showinfo("Success", 
                    f"Exported {exported_count} REAL regions from database!\n\n"
                    f"Regions: {names_text}\n\n"
                    f"These are the actual geographic boundaries from the database.")
            except Exception as e:
                messagebox.showerror("Error", f"Export failed:\n{e}")
    
    def _export_entire_database(self):
        """Export ALL regions from the loaded database (bypasses SAM completely)"""
        if self.region_matcher is None:
            messagebox.showwarning("Warning", "Please load a database first!")
            return
        
        # Ask user if they want to filter by bounds
        use_bounds = messagebox.askyesno(
            "Filter by Bounds?",
            f"Do you want to filter by the current map bounds?\n\n"
            f"North: {self.north_var.get()}\n"
            f"South: {self.south_var.get()}\n"
            f"East: {self.east_var.get()}\n"
            f"West: {self.west_var.get()}\n\n"
            f"Click YES to filter, NO to export entire database."
        )
        
        filepath = filedialog.asksaveasfilename(
            title="Export Database Regions",
            defaultextension=".geojson",
            filetypes=[("GeoJSON", "*.geojson"), ("JSON", "*.json")]
        )
        
        if filepath:
            try:
                geo_bounds = None
                if use_bounds:
                    geo_bounds = {
                        'north': self.north_var.get(),
                        'south': self.south_var.get(),
                        'east': self.east_var.get(),
                        'west': self.west_var.get()
                    }
                
                result = self.region_matcher.export_all_database_regions(filepath, geo_bounds)
                exported_count = len(result.get('features', []))
                
                self.status_var.set(f"Exported {exported_count} database regions to: {filepath}")
                messagebox.showinfo("Success", 
                    f"Exported {exported_count} regions directly from database!\n\n"
                    f"This includes ALL regions from the loaded database"
                    + (f" within the specified bounds." if use_bounds else "."))
            except Exception as e:
                messagebox.showerror("Error", f"Export failed:\n{e}")
    
    def _show_interactive_map(self):
        """Open interactive Leaflet map for region selection"""
        if not FOLIUM_AVAILABLE:
            messagebox.showerror("Error", 
                "Folium library not available!\n\n"
                "Install it with: pip install folium")
            return
        
        if self.region_matcher is None:
            messagebox.showwarning("Warning", 
                "Please load a database first!\n\n"
                "1. Load an image\n"
                "2. Load a geo database (Natural Earth or GADM)\n"
                "3. Then open the interactive map")
            return
        
        # Ask what to show on map
        choice = self._ask_map_content()
        if choice is None:
            return
        
        try:
            self.status_var.set("Creating interactive map...")
            self.root.update()
            
            # Create the viewer
            viewer = InteractiveMapViewer()
            
            if choice == "matched":
                # Show only matched/identified regions
                matched = self.region_matcher.get_all_matched_regions()
                if not matched:
                    messagebox.showwarning("Warning", 
                        "No regions identified yet!\n\n"
                        "Run 'Identify Regions' first, or choose to view all database regions.")
                    return
                viewer.add_regions_from_matcher(self.region_matcher, include_unmatched=False)
            
            elif choice == "all_db":
                # Show all database regions (filtered by bounds)
                viewer.add_regions_from_matcher(self.region_matcher, include_unmatched=True)
            
            elif choice == "all_db_filtered":
                # Filter by current bounds first
                geo_bounds = {
                    'north': self.north_var.get(),
                    'south': self.south_var.get(),
                    'east': self.east_var.get(),
                    'west': self.west_var.get()
                }
                self.region_matcher.filter_by_bounds(geo_bounds)
                viewer.add_regions_from_matcher(self.region_matcher, include_unmatched=True)
            
            if not viewer.regions:
                messagebox.showwarning("Warning", "No regions to display!")
                return
            
            # Get map center from bounds
            center = (
                (self.north_var.get() + self.south_var.get()) / 2,
                (self.east_var.get() + self.west_var.get()) / 2
            )
            
            # Create and save map
            map_path = viewer.save_map()
            
            # Open in browser
            import webbrowser
            webbrowser.open(f'file://{map_path}')
            
            self.status_var.set(f"Interactive map opened with {len(viewer.regions)} regions")
            
            messagebox.showinfo("Interactive Map", 
                f"­ƒù║´©Å Map opened in your browser!\n\n"
                f"Regions loaded: {len(viewer.regions)}\n\n"
                f"Features:\n"
                f"ÔÇó Click regions to select/deselect\n"
                f"ÔÇó Use 'Select All' / 'Clear All' buttons\n"
                f"ÔÇó Click 'Export Selected' to download GeoJSON\n\n"
                f"The map file is at:\n{map_path}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create map:\n{e}")
            import traceback
            traceback.print_exc()
    
    def _ask_map_content(self) -> Optional[str]:
        """Ask user what content to show on the map"""
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Map Content")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = [None]  # Use list to allow modification in nested function
        
        ttk.Label(dialog, text="­ƒù║´©Å What do you want to see on the map?", 
                  font=('Arial', 12, 'bold')).pack(pady=15)
        
        # Option 1: Matched regions only
        frame1 = ttk.Frame(dialog)
        frame1.pack(fill=tk.X, padx=20, pady=5)
        
        def select_matched():
            result[0] = "matched"
            dialog.destroy()
        
        ttk.Button(frame1, text="Ô£à Only Identified Regions", 
                   command=select_matched, width=30).pack(side=tk.LEFT)
        ttk.Label(frame1, text="(from SAM segmentation)", 
                  foreground='gray').pack(side=tk.LEFT, padx=10)
        
        # Option 2: All database regions
        frame2 = ttk.Frame(dialog)
        frame2.pack(fill=tk.X, padx=20, pady=5)
        
        def select_all_db():
            result[0] = "all_db"
            dialog.destroy()
        
        ttk.Button(frame2, text="­ƒôÜ All Database Regions", 
                   command=select_all_db, width=30).pack(side=tk.LEFT)
        ttk.Label(frame2, text="(entire loaded database)", 
                  foreground='gray').pack(side=tk.LEFT, padx=10)
        
        # Option 3: Database filtered by bounds
        frame3 = ttk.Frame(dialog)
        frame3.pack(fill=tk.X, padx=20, pady=5)
        
        def select_filtered():
            result[0] = "all_db_filtered"
            dialog.destroy()
        
        ttk.Button(frame3, text="­ƒÄ» Database (Filtered by Bounds)", 
                   command=select_filtered, width=30).pack(side=tk.LEFT)
        
        # Show current bounds
        bounds_text = f"N:{self.north_var.get():.1f} S:{self.south_var.get():.1f} E:{self.east_var.get():.1f} W:{self.west_var.get():.1f}"
        ttk.Label(frame3, text=bounds_text, foreground='blue').pack(side=tk.LEFT, padx=10)
        
        # Info text
        info_frame = ttk.Frame(dialog)
        info_frame.pack(fill=tk.X, padx=20, pady=20)
        
        info_text = """
­ƒÆí Tip: L'obiettivo ├¿ riconoscere i territori dalla foto!

ÔÇó Usa "Only Identified" per vedere cosa SAM ha trovato
ÔÇó Usa "Database (Filtered)" per vedere TUTTI i territori
  nell'area della tua mappa e selezionare quelli desiderati
ÔÇó Nella mappa interattiva potrai cliccare per selezionare
  e poi esportare solo i territori che ti servono
        """
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT, 
                  wraplength=350).pack()
        
        # Cancel button
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=10)
        
        # Wait for dialog
        dialog.wait_window()
        
        return result[0]


def main():
    root = tk.Tk()
    app = SAMMapGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
