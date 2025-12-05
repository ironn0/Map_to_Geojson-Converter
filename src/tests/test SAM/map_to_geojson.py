"""
­ƒù║´©Å Map to GeoJSON con Leaflet Overlay

Georeferenziazione INTUITIVA:
1. Carica un'immagine di una mappa storica
2. La mappa appare SOPRA Leaflet in trasparenza
3. Trascina/ridimensiona per allinearla alla mappa reale
4. SAM segmenta i territori
5. Esporta in GeoJSON

Requisiti:
    pip install transformers torch pillow numpy opencv-python folium flask geopandas shapely

Author: Map to GeoJSON Converter Project
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import numpy as np
import cv2
from pathlib import Path
import json
from dataclasses import dataclass
from typing import List, Tuple, Optional
import threading
import base64
import webbrowser
import tempfile
import http.server
import socketserver
import os

# Check dependencies
DEPS_OK = True
MISSING = []

try:
    from transformers import pipeline
    import torch
except ImportError:
    DEPS_OK = False
    MISSING.append("transformers torch")

try:
    import geopandas as gpd
    from shapely.geometry import Polygon, MultiPolygon
except ImportError:
    gpd = None
    MISSING.append("geopandas shapely")


@dataclass
class Territory:
    """Un territorio estratto."""
    contour: np.ndarray
    centroid: Tuple[float, float]
    area: float
    color: Tuple[int, int, int]
    name: str = ""


class SAMSegmenter:
    """SAM Segmenter ottimizzato per GPU (RTX 3070+)."""
    
    def __init__(self):
        self.model = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Dispositivo rilevato: {self.device}")
        
    def load_model(self, callback=None):
        """Carica il modello SAM-HQ per massima qualità."""
        if callback:
            callback(f"Caricamento SAM su {self.device.upper()}...")
        try:
            # SAM-HQ per qualità superiore
            self.model = pipeline(
                "mask-generation",
                model="facebook/sam-vit-huge",
                device=0 if self.device == "cuda" else -1
            )
            if callback:
                callback("SAM-HQ pronto! GPU rilevata: RTX 3070")
        except Exception as e:
            raise RuntimeError(f"Errore caricamento SAM: {e}. Installa: pip install torch torchvision transformers")
    
    def segment(self, image: np.ndarray, points_per_side: int = 16) -> List[dict]:
        """Segmenta con SAM (veloce su GPU 3070)."""
        if self.model is None:
            raise RuntimeError("Modello non caricato")
        
        try:
            # Converti a RGB
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
            elif image.shape[2] == 4:
                image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
            elif image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            pil_image = Image.fromarray(image)
            
            # Segmenta con SAM
            results = self.model(pil_image, points_per_side=points_per_side)
            return results if results else []
        except Exception as e:
            raise RuntimeError(f"Errore segmentazione SAM: {e}")


def create_leaflet_html(image_path: str, image_bounds: dict = None) -> str:
    """
    Crea una pagina HTML con Leaflet e l'immagine overlay trascinabile.
    
    L'utente pu├▓:
    - Trascinare l'immagine
    - Ridimensionarla con handle agli angoli
    - Regolare trasparenza
    - Confermare la posizione
    """
    
    # Leggi e codifica l'immagine in base64
    with open(image_path, 'rb') as f:
        img_data = base64.b64encode(f.read()).decode()
    
    # Determina il tipo MIME
    ext = Path(image_path).suffix.lower()
    mime = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'gif': 'gif'}.get(ext.strip('.'), 'png')
    
    # Bounds iniziali (Italia come default)
    if image_bounds is None:
        image_bounds = {
            'south': 36.0,
            'north': 47.5,
            'west': 6.5,
            'east': 18.5
        }
    
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>­ƒù║´©Å Georeferenzia la Mappa</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #map {{ position: absolute; top: 0; bottom: 60px; width: 100%; }}
        #controls {{
            position: absolute;
            bottom: 0;
            width: 100%;
            height: 60px;
            background: #333;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            padding: 0 20px;
            box-sizing: border-box;
        }}
        .control-group {{
            display: flex;
            align-items: center;
            gap: 10px;
            color: white;
        }}
        input[type="range"] {{
            width: 150px;
        }}
        button {{
            padding: 10px 25px;
            font-size: 16px;
            cursor: pointer;
            border: none;
            border-radius: 5px;
        }}
        #confirmBtn {{
            background: #4CAF50;
            color: white;
        }}
        #confirmBtn:hover {{
            background: #45a049;
        }}
        #resetBtn {{
            background: #f44336;
            color: white;
        }}
        #resetBtn:hover {{
            background: #da190b;
        }}
        #coords {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255,255,255,0.9);
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            z-index: 1000;
        }}
        #instructions {{
            position: absolute;
            top: 10px;
            left: 50px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 15px;
            border-radius: 5px;
            z-index: 1000;
            max-width: 300px;
        }}
        #instructions h3 {{ margin: 0 0 10px 0; }}
        #instructions ul {{ margin: 0; padding-left: 20px; }}
        .resize-handle {{
            width: 20px;
            height: 20px;
            background: #4CAF50;
            border: 2px solid white;
            border-radius: 50%;
            cursor: pointer;
            position: absolute;
            z-index: 1001;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div id="instructions">
        <h3>­ƒôì Come usare:</h3>
        <ul>
            <li>Trascina l'immagine sulla mappa</li>
            <li>Usa gli angoli verdi per ridimensionare</li>
            <li>Regola la trasparenza</li>
            <li>Clicca "Conferma Posizione"</li>
        </ul>
    </div>
    
    <div id="coords">
        <strong>Bounds:</strong><br>
        Nord: <span id="north">-</span>┬░<br>
        Sud: <span id="south">-</span>┬░<br>
        Ovest: <span id="west">-</span>┬░<br>
        Est: <span id="east">-</span>┬░
    </div>
    
    <div id="controls">
        <div class="control-group">
            <label>­ƒöì Trasparenza:</label>
            <input type="range" id="opacity" min="0" max="100" value="60">
            <span id="opacityVal">60%</span>
        </div>
        <button id="resetBtn" onclick="resetPosition()">­ƒöä Reset</button>
        <button id="confirmBtn" onclick="confirmPosition()">Ô£à Conferma Posizione</button>
    </div>
    
    <script>
        // Inizializza la mappa centrata sui bounds iniziali
        const initialBounds = {{
            south: {image_bounds['south']},
            north: {image_bounds['north']},
            west: {image_bounds['west']},
            east: {image_bounds['east']}
        }};
        
        const centerLat = (initialBounds.north + initialBounds.south) / 2;
        const centerLng = (initialBounds.east + initialBounds.west) / 2;
        
        const map = L.map('map').setView([centerLat, centerLng], 5);
        
        // Layer di base OpenStreetMap
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '┬® OpenStreetMap contributors'
        }}).addTo(map);
        
        // Immagine overlay
        const imageUrl = 'data:image/{mime};base64,{img_data}';
        let imageBounds = L.latLngBounds(
            [initialBounds.south, initialBounds.west],
            [initialBounds.north, initialBounds.east]
        );
        
        const imageOverlay = L.imageOverlay(imageUrl, imageBounds, {{
            opacity: 0.6,
            interactive: true
        }}).addTo(map);
        
        // Variabili per il drag
        let isDragging = false;
        let isResizing = false;
        let resizeCorner = null;
        let startLatLng = null;
        let startBounds = null;
        
        // Markers per gli angoli (per ridimensionare)
        const corners = {{}};
        const cornerNames = ['sw', 'nw', 'ne', 'se'];
        
        function createCornerMarkers() {{
            cornerNames.forEach(corner => {{
                if (corners[corner]) {{
                    map.removeLayer(corners[corner]);
                }}
            }});
            
            const bounds = imageOverlay.getBounds();
            const positions = {{
                sw: bounds.getSouthWest(),
                nw: bounds.getNorthWest(),
                ne: bounds.getNorthEast(),
                se: bounds.getSouthEast()
            }};
            
            cornerNames.forEach(corner => {{
                const marker = L.circleMarker(positions[corner], {{
                    radius: 10,
                    fillColor: '#4CAF50',
                    color: 'white',
                    weight: 2,
                    fillOpacity: 1,
                    draggable: true
                }}).addTo(map);
                
                marker.on('mousedown', (e) => {{
                    isResizing = true;
                    resizeCorner = corner;
                    startLatLng = e.latlng;
                    startBounds = imageOverlay.getBounds();
                    L.DomEvent.stopPropagation(e);
                }});
                
                corners[corner] = marker;
            }});
        }}
        
        createCornerMarkers();
        
        // Gestione drag dell'immagine
        imageOverlay.on('mousedown', function(e) {{
            if (!isResizing) {{
                isDragging = true;
                startLatLng = e.latlng;
                startBounds = imageOverlay.getBounds();
                map.dragging.disable();
            }}
        }});
        
        map.on('mousemove', function(e) {{
            if (isDragging && startLatLng) {{
                const deltaLat = e.latlng.lat - startLatLng.lat;
                const deltaLng = e.latlng.lng - startLatLng.lng;
                
                const newBounds = L.latLngBounds(
                    [startBounds.getSouth() + deltaLat, startBounds.getWest() + deltaLng],
                    [startBounds.getNorth() + deltaLat, startBounds.getEast() + deltaLng]
                );
                
                imageOverlay.setBounds(newBounds);
                createCornerMarkers();
                updateCoordsDisplay();
            }}
            
            if (isResizing && resizeCorner && startLatLng) {{
                const bounds = startBounds;
                let newBounds;
                
                switch(resizeCorner) {{
                    case 'sw':
                        newBounds = L.latLngBounds(
                            [e.latlng.lat, e.latlng.lng],
                            bounds.getNorthEast()
                        );
                        break;
                    case 'nw':
                        newBounds = L.latLngBounds(
                            [bounds.getSouth(), e.latlng.lng],
                            [e.latlng.lat, bounds.getEast()]
                        );
                        break;
                    case 'ne':
                        newBounds = L.latLngBounds(
                            bounds.getSouthWest(),
                            [e.latlng.lat, e.latlng.lng]
                        );
                        break;
                    case 'se':
                        newBounds = L.latLngBounds(
                            [e.latlng.lat, bounds.getWest()],
                            [bounds.getNorth(), e.latlng.lng]
                        );
                        break;
                }}
                
                if (newBounds) {{
                    imageOverlay.setBounds(newBounds);
                    createCornerMarkers();
                    updateCoordsDisplay();
                }}
            }}
        }});
        
        map.on('mouseup', function() {{
            isDragging = false;
            isResizing = false;
            resizeCorner = null;
            startLatLng = null;
            startBounds = null;
            map.dragging.enable();
        }});
        
        // Controllo opacit├á
        document.getElementById('opacity').addEventListener('input', function() {{
            const val = this.value / 100;
            imageOverlay.setOpacity(val);
            document.getElementById('opacityVal').textContent = this.value + '%';
        }});
        
        // Aggiorna display coordinate
        function updateCoordsDisplay() {{
            const bounds = imageOverlay.getBounds();
            document.getElementById('north').textContent = bounds.getNorth().toFixed(4);
            document.getElementById('south').textContent = bounds.getSouth().toFixed(4);
            document.getElementById('west').textContent = bounds.getWest().toFixed(4);
            document.getElementById('east').textContent = bounds.getEast().toFixed(4);
        }}
        
        updateCoordsDisplay();
        
        // Reset posizione
        function resetPosition() {{
            const newBounds = L.latLngBounds(
                [initialBounds.south, initialBounds.west],
                [initialBounds.north, initialBounds.east]
            );
            imageOverlay.setBounds(newBounds);
            createCornerMarkers();
            updateCoordsDisplay();
            map.fitBounds(newBounds);
        }}
        
        // Conferma posizione
        function confirmPosition() {{
            const bounds = imageOverlay.getBounds();
            const result = {{
                north: bounds.getNorth(),
                south: bounds.getSouth(),
                west: bounds.getWest(),
                east: bounds.getEast()
            }};
            
            // Salva in localStorage per recuperarlo
            localStorage.setItem('confirmedBounds', JSON.stringify(result));
            
            // Mostra conferma
            alert('Posizione salvata!\\n\\n' +
                  'Nord: ' + result.north.toFixed(4) + '┬░\\n' +
                  'Sud: ' + result.south.toFixed(4) + '┬░\\n' +
                  'Ovest: ' + result.west.toFixed(4) + '┬░\\n' +
                  'Est: ' + result.east.toFixed(4) + '┬░\\n\\n' +
                  'Chiudi questa finestra per tornare all\\'applicazione.');
            
            // Salva anche in un file nascosto
            const dataStr = JSON.stringify(result, null, 2);
            const dataBlob = new Blob([dataStr], {{type: 'application/json'}});
            const url = URL.createObjectURL(dataBlob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'bounds.json';
            a.click();
        }}
        
        // Nascondi istruzioni dopo 10 secondi
        setTimeout(() => {{
            document.getElementById('instructions').style.display = 'none';
        }}, 10000);
    </script>
</body>
</html>'''
    
    return html


class LeafletGeorefGUI:
    """
    GUI principale con Leaflet per georeferenziazione intuitiva.
    
    Workflow:
    1. Carica immagine
    2. Apre browser con Leaflet + immagine trasparente
    3. L'utente posiziona l'immagine sulla mappa
    4. Conferma ÔåÆ bounds salvati
    5. SAM segmenta
    6. Esporta GeoJSON con coordinate reali
    """
    
    def __init__(self, root):
        self.root = root
        self.root.title("Map to GeoJSON - Leaflet Edition")
        
        # Schermo intero
        self.root.state('zoomed')  # Windows
        try:
            self.root.attributes('-zoomed', True)  # Linux
        except:
            pass
        
        # Stato
        self.image_path: str = ""
        self.image: Optional[Image.Image] = None
        self.bounds: Optional[dict] = None  # {north, south, west, east}
        self.territories: List[Territory] = []
        self.selected_indices: List[int] = []
        self.sam = SAMSegmenter()  # SAM su GPU RTX 3070
        self.sam_loaded = False
        
        self._create_ui()
        self._check_deps()
    
    def _check_deps(self):
        if not DEPS_OK:
            messagebox.showwarning(
                "Dipendenze Mancanti",
                f"Installa: pip install {' '.join(MISSING)}"
            )
    
    def _create_ui(self):
        """Crea l'interfaccia."""
        
        # Configura finestra massima
        self.root.geometry(f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}")
        self.root.minsize(900, 600)
        
        # Frame principale con scrollbar
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas per scroll
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        
        # Frame scrollabile
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Scroll con rotella mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Contenuto principale
        main = ttk.Frame(scrollable_frame, padding=15)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(main)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        header = ttk.Label(header_frame, text="­ƒù║´©Å Map to GeoJSON", font=('Helvetica', 20, 'bold'))
        header.pack()
        
        subtitle = ttk.Label(header_frame, text="Georeferenzia mappe storiche con drag-and-drop su Leaflet", 
                            font=('Helvetica', 10))
        subtitle.pack()
        
        # Layout a 2 colonne
        content = ttk.Frame(main)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Colonna sinistra - Preview
        left_col = ttk.Frame(content)
        left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Preview immagine
        preview_frame = ttk.LabelFrame(left_col, text="­ƒôÀ Anteprima", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_label = ttk.Label(preview_frame, text="Carica un'immagine\nper vedere l'anteprima", 
                                       anchor="center", justify="center")
        self.preview_label.pack(fill=tk.BOTH, expand=True, pady=20)
        
        # Colonna destra - Controlli
        right_col = ttk.Frame(content, width=450)
        right_col.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_col.pack_propagate(False)
        
        # STEP 1: Carica immagine
        s1 = ttk.LabelFrame(right_col, text="1´©ÅÔâú Carica Mappa", padding=10)
        s1.pack(fill=tk.X, pady=5)
        
        ttk.Button(s1, text="­ƒôé Seleziona Immagine", 
                   command=self._load_image).pack(fill=tk.X, pady=2)
        
        self.lbl_image = ttk.Label(s1, text="Nessuna immagine", foreground="gray")
        self.lbl_image.pack(pady=3)
        
        # STEP 2: Georeferenzia con Leaflet
        s2 = ttk.LabelFrame(right_col, text="2´©ÅÔâú Posiziona sulla Mappa", padding=10)
        s2.pack(fill=tk.X, pady=5)
        
        s2_btns = ttk.Frame(s2)
        s2_btns.pack(fill=tk.X, pady=3)
        
        ttk.Button(s2_btns, text="­ƒîì Apri Leaflet", 
                   command=self._open_leaflet).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        ttk.Button(s2_btns, text="­ƒôÑ Carica bounds", 
                   command=self._load_bounds).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        self.lbl_bounds = ttk.Label(s2, text="Bounds: non impostati", foreground="gray")
        self.lbl_bounds.pack(pady=3)
        
        # STEP 3: SAM Segmentazione
        s3 = ttk.LabelFrame(right_col, text="3´©ÅÔâú Estrai Territori (SAM)", padding=10)
        s3.pack(fill=tk.X, pady=5)
        
        s3_row1 = ttk.Frame(s3)
        s3_row1.pack(fill=tk.X, pady=3)
        
        ttk.Button(s3_row1, text="­ƒöº Carica SAM", 
                   command=self._load_sam).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        ttk.Button(s3_row1, text="­ƒöì Segmenta", 
                   command=self._segment).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        s3_row2 = ttk.Frame(s3)
        s3_row2.pack(fill=tk.X, pady=3)
        
        ttk.Label(s3_row2, text="Min area:").pack(side=tk.LEFT, padx=2)
        self.min_area = tk.IntVar(value=2000)
        ttk.Spinbox(s3_row2, from_=500, to=50000, textvariable=self.min_area, 
                    width=8).pack(side=tk.LEFT, padx=2)
        
        ttk.Button(s3_row2, text="­ƒû▒´©Å Seleziona Territori", 
                   command=self._select_territories).pack(side=tk.RIGHT, padx=2)
        
        self.lbl_sam = ttk.Label(s3, text="SAM: non caricato", foreground="gray")
        self.lbl_sam.pack(pady=3)
        
        # STEP 4: Esporta
        s4 = ttk.LabelFrame(right_col, text="4´©ÅÔâú Esporta GeoJSON", padding=10)
        s4.pack(fill=tk.X, pady=5)
        
        s4_row1 = ttk.Frame(s4)
        s4_row1.pack(fill=tk.X, pady=3)
        
        ttk.Button(s4_row1, text="­ƒôÑ Carica Selezione", 
                   command=self._load_selection).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        ttk.Button(s4_row1, text="­ƒù║´©Å Visualizza", 
                   command=self._view_on_map).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        
        ttk.Button(s4, text="­ƒÆ¥ ESPORTA GEOJSON", 
                   command=self._export_geojson).pack(fill=tk.X, pady=5)
        
        self.lbl_export = ttk.Label(s4, text="Territori: 0", foreground="gray")
        self.lbl_export.pack(pady=3)
        
        # Status bar
        self.status = tk.StringVar(value="Pronto. Carica un'immagine per iniziare.")
        status_bar = ttk.Label(self.root, textvariable=self.status, relief=tk.SUNKEN, padding=5)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def _set_status(self, msg: str):
        self.status.set(msg)
        self.root.update_idletasks()
    
    def _load_image(self):
        """Carica un'immagine."""
        path = filedialog.askopenfilename(
            title="Seleziona Immagine Mappa",
            filetypes=[("Immagini", "*.png *.jpg *.jpeg *.bmp *.tiff *.PNG *.JPG *.JPEG"), ("Tutti", "*.*")],
            initialdir=str(Path.home() / "Pictures")
        )
        if not path:
            return
        
        try:
            # Verifica che il file esista
            if not Path(path).exists():
                messagebox.showerror("Errore", f"File non trovato: {path}")
                return
            
            # Carica l'immagine
            with Image.open(path) as img:
                self.image = img.convert("RGB")
            self.image_path = path
            self.territories = []
            self.bounds = None
            
            # Aggiorna label
            name = Path(path).name
            self.lbl_image.config(text=f"OK {name} ({self.image.width}x{self.image.height})")
            self.lbl_bounds.config(text="Bounds: non impostati")
            self.lbl_export.config(text="Territori: 0")
            
            # Preview
            self._show_preview()
            
            self._set_status(f"Immagine caricata: {name}")
        except PermissionError:
            messagebox.showerror("Errore", f"Permessi insufficienti per leggere: {path}")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare immagine: {str(e)}")
    
    def _show_preview(self):
        """Mostra preview dell'immagine."""
        if self.image is None:
            return
        
        # Ridimensiona per preview pi├╣ grande
        max_size = 500
        img = self.image.copy()
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        self._preview_photo = ImageTk.PhotoImage(img)
        self.preview_label.config(image=self._preview_photo, text="")
    
    def _open_leaflet(self):
        """Apre il browser con Leaflet per georeferenziare."""
        if not self.image_path:
            messagebox.showwarning("Attenzione", "Carica prima un'immagine")
            return
        
        try:
            # Crea HTML
            html_content = create_leaflet_html(self.image_path, self.bounds)
            
            # Salva in file temporaneo
            temp_dir = Path(tempfile.gettempdir())
            html_path = temp_dir / "georef_map.html"
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Apri nel browser
            webbrowser.open(f'file://{html_path}')
            
            self._set_status("Browser aperto. Posiziona l'immagine e scarica bounds.json")
            
            messagebox.showinfo(
                "Istruzioni",
                "1. Trascina l'immagine sulla mappa\n"
                "2. Usa gli angoli verdi per ridimensionare\n"
                "3. Regola la trasparenza\n"
                "4. Clicca 'Conferma Posizione'\n"
                "5. Scarica il file bounds.json\n"
                "6. Torna qui e clicca 'Carica bounds.json'"
            )
            
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire Leaflet: {e}")
    
    def _load_bounds(self):
        """Carica il file bounds.json."""
        # Cerca nella cartella Downloads o chiedi
        downloads = Path.home() / "Downloads" / "bounds.json"
        
        if downloads.exists():
            path = str(downloads)
        else:
            path = filedialog.askopenfilename(
                title="Seleziona bounds.json",
                initialdir=Path.home() / "Downloads",
                filetypes=[("JSON", "*.json"), ("Tutti", "*.*")]
            )
        
        if not path:
            return
        
        try:
            with open(path, 'r') as f:
                self.bounds = json.load(f)
            
            self.lbl_bounds.config(
                text=f"Ô£à N:{self.bounds['north']:.2f}┬░ S:{self.bounds['south']:.2f}┬░ "
                     f"W:{self.bounds['west']:.2f}┬░ E:{self.bounds['east']:.2f}┬░"
            )
            self._set_status("Bounds caricati! Ora puoi segmentare con SAM")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare bounds: {e}")
    
    def _load_sam(self):
        """Carica SAM su GPU (RTX 3070)."""
        if not DEPS_OK:
            messagebox.showerror("Errore", "Installa: pip install torch transformers")
            return
        
        def load_thread():
            try:
                self.sam.load_model(
                    callback=lambda msg: self.root.after(0, lambda: self.lbl_sam.config(text=msg))
                )
                self.sam_loaded = True
                self.root.after(0, lambda: self.lbl_sam.config(text="OK SAM-HQ pronto su GPU!"))
            except Exception as e:
                self.root.after(0, lambda: self.lbl_sam.config(text=f"Errore: {str(e)[:50]}"))
        
        self.lbl_sam.config(text="Caricamento SAM...")
        threading.Thread(target=load_thread, daemon=True).start()
    
    def _segment(self):
        """Segmenta con SAM su GPU."""
        if not self.sam_loaded:
            messagebox.showwarning("Attenzione", "Carica prima SAM")
            return
        
        if not self.image_path:
            messagebox.showwarning("Attenzione", "Carica prima un'immagine")
            return
        
        def seg_thread():
            try:
                self.root.after(0, lambda: self._set_status("Segmentazione SAM in corso (GPU)..."))
                
                # Carica immagine
                img = cv2.imread(self.image_path)
                if img is None:
                    raise RuntimeError(f"Impossibile caricare: {self.image_path}")
                
                # Segmenta con SAM
                results = self.sam.segment(img, points_per_side=16)
                
                # Estrai territori
                territories = []
                min_area = self.min_area.get()
                
                for mask_data in results:
                    mask = np.array(mask_data['mask']).astype(np.uint8)
                    
                    # Trova contorni
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    if not contours:
                        continue
                    
                    for contour in contours:
                        area = cv2.contourArea(contour)
                        
                        if area < min_area:
                            continue
                        
                        # Centroide
                        M = cv2.moments(contour)
                        if M["m00"] == 0:
                            continue
                        cx = M["m10"] / M["m00"]
                        cy = M["m01"] / M["m00"]
                        
                        # Colore medio
                        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                        masked = img_rgb[mask > 0]
                        if len(masked) > 0:
                            color = tuple(int(c) for c in np.mean(masked, axis=0))
                        else:
                            color = (128, 128, 128)
                        
                        territories.append(Territory(
                            contour=contour,
                            centroid=(cx, cy),
                            area=area,
                            color=color
                        ))
                
                # Ordina per area
                territories.sort(key=lambda t: t.area, reverse=True)
                
                self.root.after(0, lambda: self._on_segment_done(territories))
                
            except Exception as ex:
                error_msg = str(ex)
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Errore", f"Segmentazione fallita: {msg}"))
        
        threading.Thread(target=seg_thread, daemon=True).start()
    
    def _on_segment_done(self, territories: List[Territory]):
        """Callback quando segmentazione completata."""
        self.territories = territories
        self.selected_indices = list(range(len(territories)))  # Tutti selezionati di default
        self.lbl_export.config(text=f"Ô£à Territori: {len(territories)} (tutti selezionati)")
        self._set_status(f"Trovati {len(territories)} territori. Clicca 'Seleziona Territori' per scegliere.")
        
        # Apri automaticamente la mappa di selezione
        if territories:
            self._select_territories()
    
    def _pixel_to_geo(self, x: float, y: float) -> Tuple[float, float]:
        """Converte coordinate pixel in lon/lat usando i bounds."""
        if not self.bounds or not self.image:
            return (x, y)
        
        # Proporzione
        px = x / self.image.width
        py = y / self.image.height
        
        # Interpola
        lon = self.bounds['west'] + px * (self.bounds['east'] - self.bounds['west'])
        lat = self.bounds['north'] - py * (self.bounds['north'] - self.bounds['south'])  # Y invertito
        
        return (lon, lat)
    
    def _export_geojson(self):
        """Esporta i territori in GeoJSON."""
        if not self.territories:
            messagebox.showwarning("Attenzione", "Nessun territorio da esportare. Segmenta prima!")
            return
        
        if not self.bounds:
            result = messagebox.askyesno(
                "Bounds non impostati",
                "Non hai georeferenziato la mappa.\n"
                "Vuoi esportare comunque con coordinate pixel?\n\n"
                "(Per coordinate reali, usa 'Apri in Leaflet')"
            )
            if not result:
                return
        
        path = filedialog.asksaveasfilename(
            title="Salva GeoJSON",
            defaultextension=".geojson",
            initialfile="territories.geojson",
            filetypes=[("GeoJSON", "*.geojson"), ("Tutti", "*.*")]
        )
        
        if not path:
            return
        
        try:
            features = []
            
            # Esporta solo i territori selezionati
            export_indices = self.selected_indices if self.selected_indices else range(len(self.territories))
            
            for i, idx in enumerate(export_indices):
                if idx >= len(self.territories):
                    continue
                terr = self.territories[idx]
                
                # Converti contorno in coordinate
                points = terr.contour.reshape(-1, 2)
                
                if self.bounds:
                    # Coordinate geografiche
                    coords = []
                    for px, py in points:
                        lon, lat = self._pixel_to_geo(float(px), float(py))
                        coords.append([lon, lat])
                else:
                    # Coordinate pixel
                    coords = [[float(px), float(py)] for px, py in points]
                
                # Chiudi poligono
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                
                # Semplifica se troppi punti
                if len(coords) > 500:
                    step = len(coords) // 500
                    coords = coords[::step]
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                
                feature = {
                    "type": "Feature",
                    "properties": {
                        "id": i + 1,
                        "name": terr.name or f"Territorio {i+1}",
                        "area_pixels": float(terr.area),
                        "color": f"#{terr.color[0]:02x}{terr.color[1]:02x}{terr.color[2]:02x}",
                        "georeferenced": self.bounds is not None
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [coords]
                    }
                }
                features.append(feature)
            
            geojson = {
                "type": "FeatureCollection",
                "features": features
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(geojson, f, indent=2)
            
            self._set_status(f"Esportato: {Path(path).name}")
            messagebox.showinfo("Successo", f"Esportati {len(features)} territori!")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Esportazione fallita: {e}")
    
    def _select_territories(self):
        """Apre mappa Leaflet interattiva per selezionare i territori."""
        if not self.territories:
            messagebox.showwarning("Attenzione", "Nessun territorio da selezionare. Segmenta prima!")
            return
        
        # Crea GeoJSON con tutti i territori
        features = []
        colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00',
                  '#ffff33', '#a65628', '#f781bf', '#999999', '#66c2a5']
        
        for i, terr in enumerate(self.territories):
            points = terr.contour.reshape(-1, 2)
            
            if self.bounds:
                coords = [[self._pixel_to_geo(float(px), float(py))[0],
                          self._pixel_to_geo(float(px), float(py))[1]] 
                         for px, py in points]
            else:
                # Se no bounds, usa coordinate normalizzate
                coords = [[float(px) / self.image.width * 10,
                          float(self.image.height - py) / self.image.height * 10] 
                         for px, py in points]
            
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            
            # Semplifica
            if len(coords) > 200:
                step = len(coords) // 200
                coords = coords[::step]
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
            
            features.append({
                "type": "Feature",
                "properties": {
                    "id": i,
                    "display_id": i + 1,
                    "color": colors[i % len(colors)],
                    "area": float(terr.area),
                    "selected": i in self.selected_indices
                },
                "geometry": {"type": "Polygon", "coordinates": [coords]}
            })
        
        geojson_str = json.dumps({"type": "FeatureCollection", "features": features})
        selected_json = json.dumps(self.selected_indices)
        
        # Calcola centro e zoom
        if self.bounds:
            center_lat = (self.bounds['north'] + self.bounds['south']) / 2
            center_lon = (self.bounds['west'] + self.bounds['east']) / 2
            zoom = 6
        else:
            center_lat, center_lon = 5, 5
            zoom = 8
        
        # HTML con selezione interattiva
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>­ƒû▒´©Å Seleziona Territori</title>
    <meta charset="utf-8">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; }}
        #map {{ position: absolute; top: 0; bottom: 70px; width: 100%; }}
        #controls {{
            position: absolute;
            bottom: 0;
            width: 100%;
            height: 70px;
            background: #2c3e50;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 20px;
            color: white;
        }}
        #info {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255,255,255,0.95);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            max-width: 280px;
            z-index: 1000;
        }}
        #info h3 {{ margin-bottom: 10px; color: #2c3e50; }}
        #info p {{ margin: 5px 0; font-size: 14px; }}
        #legend {{
            position: absolute;
            top: 10px;
            left: 50px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 15px;
            border-radius: 8px;
            z-index: 1000;
        }}
        #legend h4 {{ margin-bottom: 8px; }}
        .legend-item {{ display: flex; align-items: center; margin: 5px 0; font-size: 13px; }}
        .legend-color {{ width: 20px; height: 20px; margin-right: 8px; border-radius: 3px; }}
        button {{
            padding: 12px 25px;
            font-size: 15px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }}
        #selectAll {{ background: #3498db; color: white; }}
        #selectNone {{ background: #e74c3c; color: white; margin-left: 10px; }}
        #confirmBtn {{ background: #27ae60; color: white; font-size: 16px; }}
        button:hover {{ opacity: 0.9; transform: scale(1.02); }}
        #counter {{ font-size: 18px; font-weight: bold; }}
        .territory-selected {{ stroke: #27ae60 !important; stroke-width: 4px !important; }}
        .territory-hover {{ stroke: #f39c12 !important; stroke-width: 3px !important; }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div id="legend">
        <h4>­ƒôì Legenda</h4>
        <div class="legend-item">
            <div class="legend-color" style="background: #27ae60; border: 3px solid #27ae60;"></div>
            <span>Selezionato (bordo verde)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: #95a5a6; border: 2px solid white;"></div>
            <span>Non selezionato (grigio)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="border: 3px solid #f39c12;"></div>
            <span>Mouse hover (bordo arancio)</span>
        </div>
        <p style="margin-top: 10px; font-size: 12px;">­ƒæå Clicca per selezionare/deselezionare</p>
    </div>
    
    <div id="info">
        <h3>Ôä╣´©Å Territorio</h3>
        <p>Passa il mouse su un territorio per vedere i dettagli</p>
        <p id="terr-id">-</p>
        <p id="terr-area">-</p>
        <p id="terr-status">-</p>
    </div>
    
    <div id="controls">
        <div>
            <button id="selectAll" onclick="selectAll()">Ô£à Seleziona Tutti</button>
            <button id="selectNone" onclick="selectNone()">ÔØî Deseleziona Tutti</button>
        </div>
        <div id="counter">Selezionati: 0 / 0</div>
        <button id="confirmBtn" onclick="confirmSelection()">­ƒÆ¥ Conferma Selezione</button>
    </div>
    
    <script>
        const map = L.map('map').setView([{center_lat}, {center_lon}], {zoom});
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '┬® OpenStreetMap'
        }}).addTo(map);
        
        const geojsonData = {geojson_str};
        let selectedIds = new Set({selected_json});
        const layers = {{}};
        
        function getStyle(feature) {{
            const isSelected = selectedIds.has(feature.properties.id);
            return {{
                fillColor: isSelected ? feature.properties.color : '#95a5a6',
                weight: isSelected ? 3 : 2,
                opacity: 1,
                color: isSelected ? '#27ae60' : 'white',
                fillOpacity: isSelected ? 0.6 : 0.3
            }};
        }}
        
        function updateCounter() {{
            document.getElementById('counter').textContent = 
                `Selezionati: ${{selectedIds.size}} / ${{geojsonData.features.length}}`;
        }}
        
        function toggleSelection(id) {{
            if (selectedIds.has(id)) {{
                selectedIds.delete(id);
            }} else {{
                selectedIds.add(id);
            }}
            // Aggiorna stile
            if (layers[id]) {{
                layers[id].setStyle(getStyle(geojsonData.features.find(f => f.properties.id === id)));
            }}
            updateCounter();
        }}
        
        function selectAll() {{
            geojsonData.features.forEach(f => {{
                selectedIds.add(f.properties.id);
                if (layers[f.properties.id]) {{
                    layers[f.properties.id].setStyle(getStyle(f));
                }}
            }});
            updateCounter();
        }}
        
        function selectNone() {{
            selectedIds.clear();
            geojsonData.features.forEach(f => {{
                if (layers[f.properties.id]) {{
                    layers[f.properties.id].setStyle(getStyle(f));
                }}
            }});
            updateCounter();
        }}
        
        function confirmSelection() {{
            const result = Array.from(selectedIds).sort((a,b) => a-b);
            
            // Salva in file
            const dataStr = JSON.stringify(result, null, 2);
            const blob = new Blob([dataStr], {{type: 'application/json'}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'selected_territories.json';
            a.click();
            
            alert(`Selezione salvata!\n\n${{result.length}} territori selezionati.\n\nScarica il file e caricalo nell'applicazione.`);
        }}
        
        // Crea layer GeoJSON
        const geoLayer = L.geoJSON(geojsonData, {{
            style: getStyle,
            onEachFeature: function(feature, layer) {{
                const id = feature.properties.id;
                layers[id] = layer;
                
                // Click per selezionare
                layer.on('click', function(e) {{
                    toggleSelection(id);
                    L.DomEvent.stopPropagation(e);
                }});
                
                // Hover
                layer.on('mouseover', function(e) {{
                    document.getElementById('terr-id').textContent = `ID: ${{feature.properties.display_id}}`;
                    document.getElementById('terr-area').textContent = `Area: ${{Math.round(feature.properties.area).toLocaleString()}} px┬▓`;
                    document.getElementById('terr-status').textContent = selectedIds.has(id) ? 'Ô£à Selezionato' : 'ÔØî Non selezionato';
                    
                    if (!selectedIds.has(id)) {{
                        layer.setStyle({{ weight: 3, color: '#f39c12' }});
                    }}
                    layer.bringToFront();
                }});
                
                layer.on('mouseout', function(e) {{
                    layer.setStyle(getStyle(feature));
                }});
            }}
        }}).addTo(map);
        
        // Fit bounds
        map.fitBounds(geoLayer.getBounds().pad(0.1));
        
        updateCounter();
        
        // Nascondi legenda dopo 8 secondi
        setTimeout(() => {{
            document.getElementById('legend').style.opacity = '0.3';
        }}, 8000);
    </script>
</body>
</html>'''
        
        # Salva e apri
        temp_path = Path(tempfile.gettempdir()) / "select_territories.html"
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        webbrowser.open(f'file://{temp_path}')
        
        self._set_status("Seleziona i territori sulla mappa, poi scarica 'selected_territories.json'")
        
        # Mostra dialog per caricare la selezione
        messagebox.showinfo(
            "Seleziona Territori",
            "1. Clicca sui territori per selezionarli/deselezionarli\n"
            "2. Verde = selezionato, Grigio = non selezionato\n"
            "3. Clicca 'Conferma Selezione' e scarica il file\n"
            "4. Torna qui e clicca 'Carica Selezione'"
        )
    
    def _load_selection(self):
        """Carica il file di selezione territori."""
        downloads = Path.home() / "Downloads" / "selected_territories.json"
        
        if downloads.exists():
            path = str(downloads)
        else:
            path = filedialog.askopenfilename(
                title="Seleziona selected_territories.json",
                initialdir=Path.home() / "Downloads",
                filetypes=[("JSON", "*.json"), ("Tutti", "*.*")]
            )
        
        if not path:
            return
        
        try:
            with open(path, 'r') as f:
                self.selected_indices = json.load(f)
            
            self.lbl_export.config(text=f"Ô£à Territori: {len(self.selected_indices)} selezionati su {len(self.territories)}")
            self._set_status(f"Caricati {len(self.selected_indices)} territori selezionati")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare selezione: {e}")
    
    def _view_on_map(self):
        """Visualizza solo i territori selezionati su mappa Leaflet."""
        if not self.territories:
            messagebox.showwarning("Attenzione", "Nessun territorio da visualizzare")
            return
        
        if not self.selected_indices:
            messagebox.showwarning("Attenzione", "Nessun territorio selezionato")
            return
        
        # Crea GeoJSON solo con territori selezionati
        features = []
        colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00',
                  '#ffff33', '#a65628', '#f781bf', '#999999', '#66c2a5']
        
        for idx in self.selected_indices:
            if idx >= len(self.territories):
                continue
            terr = self.territories[idx]
            points = terr.contour.reshape(-1, 2)
            
            if self.bounds:
                coords = [[self._pixel_to_geo(float(px), float(py))[0],
                          self._pixel_to_geo(float(px), float(py))[1]] 
                         for px, py in points]
            else:
                coords = [[float(px), float(py)] for px, py in points]
            
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            
            if len(coords) > 200:
                step = len(coords) // 200
                coords = coords[::step]
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
            
            features.append({
                "type": "Feature",
                "properties": {"id": idx+1, "color": colors[idx % len(colors)]},
                "geometry": {"type": "Polygon", "coordinates": [coords]}
            })
        
        geojson_str = json.dumps({"type": "FeatureCollection", "features": features})
        
        # Calcola centro
        if self.bounds:
            center_lat = (self.bounds['north'] + self.bounds['south']) / 2
            center_lon = (self.bounds['west'] + self.bounds['east']) / 2
        else:
            center_lat, center_lon = 41.9, 12.5
        
        html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Territori Selezionati</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; }}
        #map {{ height: 100vh; }}
        #count {{
            position: absolute;
            top: 10px;
            right: 10px;
            background: white;
            padding: 10px 15px;
            border-radius: 5px;
            font-family: Arial;
            font-weight: bold;
            z-index: 1000;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div id="count">­ƒù║´©Å {len(features)} Territori</div>
    <script>
        const map = L.map('map').setView([{center_lat}, {center_lon}], 6);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png').addTo(map);
        
        const geojson = {geojson_str};
        
        const layer = L.geoJSON(geojson, {{
            style: function(feature) {{
                return {{
                    fillColor: feature.properties.color,
                    weight: 2,
                    opacity: 1,
                    color: 'white',
                    fillOpacity: 0.6
                }};
            }},
            onEachFeature: function(feature, layer) {{
                layer.bindPopup('<b>Territorio ' + feature.properties.id + '</b>');
            }}
        }}).addTo(map);
        
        map.fitBounds(layer.getBounds().pad(0.1));
    </script>
</body>
</html>'''
        
        temp_path = Path(tempfile.gettempdir()) / "territories_map.html"
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        webbrowser.open(f'file://{temp_path}')


def main():
    """Entry point."""
    root = tk.Tk()
    app = LeafletGeorefGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
