"""
Map Region Selector - GUI con Mouse
Estrae regioni da immagini e permette selezione interattiva
"""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import geopandas as gpd


class Region:
    """Rappresenta una regione estratta"""
    def __init__(self, id: int, contour: np.ndarray, color: Tuple[int, int, int], area: float):
        self.id = id
        self.contour = contour
        self.color = color
        self.area = area
        self.selected = True  # Default: selezionata
        self.name = f"Regione {id}"
        
        # Calcola centroide
        M = cv2.moments(contour)
        if M["m00"] != 0:
            self.centroid = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
        else:
            self.centroid = (contour[0][0][0], contour[0][0][1])
        
        # Bounding box
        self.bbox = cv2.boundingRect(contour)


class MapSelectorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("🗺️ Map Region Selector")
        self.root.geometry("1200x800")
        
        # Stato
        self.image_path: Optional[Path] = None
        self.original_image: Optional[np.ndarray] = None
        self.display_image: Optional[np.ndarray] = None
        self.regions: List[Region] = []
        self.scale_factor = 1.0
        self.italy_regions: Optional[gpd.GeoDataFrame] = None
        
        # Calibrazione
        self.calibration = {
            'lat_range': (36.0, 47.5),
            'lon_range': (6.5, 18.5)
        }
        
        self._setup_ui()
        self._load_gadm_database()
    
    def _setup_ui(self):
        """Crea interfaccia utente"""
        # Frame principale
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # --- Toolbar ---
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=5)
        
        ttk.Button(toolbar, text="📁 Apri Immagine", command=self._open_image).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🔍 Estrai Regioni", command=self._extract_regions).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="✅ Seleziona Tutto", command=self._select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="❌ Deseleziona Tutto", command=self._deselect_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="💾 Esporta GeoJSON", command=self._export_geojson).pack(side=tk.LEFT, padx=2)
        
        # Separatore
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        # Parametri estrazione
        ttk.Label(toolbar, text="Colori:").pack(side=tk.LEFT, padx=2)
        self.n_colors_var = tk.StringVar(value="60")
        ttk.Entry(toolbar, textvariable=self.n_colors_var, width=5).pack(side=tk.LEFT, padx=2)
        
        ttk.Label(toolbar, text="Area min:").pack(side=tk.LEFT, padx=2)
        self.min_area_var = tk.StringVar(value="300")
        ttk.Entry(toolbar, textvariable=self.min_area_var, width=6).pack(side=tk.LEFT, padx=2)
        
        # --- Area principale ---
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Canvas per immagine
        canvas_frame = ttk.LabelFrame(paned, text="Mappa", padding="5")
        paned.add(canvas_frame, weight=3)
        
        self.canvas = tk.Canvas(canvas_frame, bg='#2b2b2b', cursor="hand2")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Configure>", self._on_resize)
        
        # Lista regioni
        list_frame = ttk.LabelFrame(paned, text="Regioni Estratte", padding="5")
        paned.add(list_frame, weight=1)
        
        # Listbox con scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.region_listbox = tk.Listbox(
            list_container, 
            yscrollcommand=scrollbar.set,
            selectmode=tk.SINGLE,
            font=('Consolas', 10)
        )
        self.region_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.region_listbox.yview)
        
        self.region_listbox.bind('<<ListboxSelect>>', self._on_list_select)
        self.region_listbox.bind('<Double-Button-1>', self._on_list_double_click)
        
        # Frame per modifica nome
        edit_frame = ttk.Frame(list_frame)
        edit_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(edit_frame, text="Nome:").pack(side=tk.LEFT)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(edit_frame, textvariable=self.name_var)
        self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(edit_frame, text="Applica", command=self._apply_name).pack(side=tk.LEFT)
        
        # Dropdown database regioni con filtro
        db_frame = ttk.Frame(list_frame)
        db_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(db_frame, text="Cerca:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(db_frame, textvariable=self.search_var, width=15)
        self.search_entry.pack(side=tk.LEFT, padx=2)
        self.search_entry.bind('<KeyRelease>', self._filter_db_regions)
        
        self.db_region_var = tk.StringVar()
        self.db_combo = ttk.Combobox(db_frame, textvariable=self.db_region_var, state="readonly", width=25)
        self.db_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(db_frame, text="Usa", command=self._use_db_name).pack(side=tk.LEFT)
        
        # Pulsante per assegnare automaticamente regioni italiane
        auto_frame = ttk.Frame(list_frame)
        auto_frame.pack(fill=tk.X, pady=5)
        ttk.Button(auto_frame, text="🇮🇹 Assegna Regioni Italiane", command=self._auto_assign_italian_regions).pack(fill=tk.X)
        
        # Memorizza lista completa per filtro
        self.all_db_regions = []
        self.italian_regions_list = []  # Lista regioni italiane da GADM
        
        # --- Status bar ---
        self.status_var = tk.StringVar(value="Pronto. Apri un'immagine per iniziare.")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=2)
    
    def _load_gadm_database(self):
        """Carica database regioni mondiali (Natural Earth + GADM Italy)"""
        region_list = []
        
        # 1. GADM Italy - Regioni italiane (priorità)
        gadm_path = Path(__file__).parent / "geodata" / "gadm_italy" / "gadm41_ITA_1.shp"
        if gadm_path.exists():
            try:
                self.italy_regions = gpd.read_file(str(gadm_path))
                self.italian_regions_list = sorted(self.italy_regions['NAME_1'].unique())
                # Aggiungi regioni italiane in cima alla lista
                for r in self.italian_regions_list:
                    region_list.append(f"{r} (Italia - Regione)")
                print(f"Caricate {len(self.italian_regions_list)} regioni italiane da GADM")
            except Exception as e:
                print(f"Errore caricamento GADM Italy: {e}")
                self.italian_regions_list = []
        
        # 2. Natural Earth - Database mondiale
        ne_path = Path(__file__).parent / "geodata" / "ne_10m_admin_1_states_provinces" / "ne_10m_admin_1_states_provinces.shp"
        if ne_path.exists():
            try:
                self.world_regions = gpd.read_file(str(ne_path))
                
                # Crea lista formattata: "Regione (Paese)"
                for _, row in self.world_regions.iterrows():
                    name = row.get('name', 'Unknown')
                    admin = row.get('admin', 'Unknown')
                    if name and admin and admin != 'Italy':  # Escludi Italia (già da GADM)
                        region_list.append(f"{name} ({admin})")
                
            except Exception as e:
                print(f"Errore caricamento Natural Earth: {e}")
                self.world_regions = None
        
        # Ordina e salva
        region_list = sorted(set(region_list))
        self.all_db_regions = region_list
        self.db_combo['values'] = [''] + region_list
        
        n_italy = len(self.italian_regions_list) if hasattr(self, 'italian_regions_list') else 0
        self.status_var.set(f"Database: {n_italy} regioni italiane + {len(region_list) - n_italy} mondiali")
    
    def _open_image(self):
        """Apri dialog per selezionare immagine"""
        file_path = filedialog.askopenfilename(
            title="Seleziona immagine mappa",
            filetypes=[
                ("Immagini", "*.png *.jpg *.jpeg *.bmp *.tiff"),
                ("Tutti i file", "*.*")
            ]
        )
        
        if file_path:
            self.image_path = Path(file_path)
            self.original_image = cv2.imread(str(self.image_path))
            
            if self.original_image is not None:
                self.regions = []
                self._update_display()
                self._update_region_list()
                self.status_var.set(f"Immagine caricata: {self.image_path.name} ({self.original_image.shape[1]}x{self.original_image.shape[0]})")
            else:
                messagebox.showerror("Errore", "Impossibile caricare l'immagine")
    
    def _extract_regions(self):
        """Estrai regioni usando K-Means"""
        if self.original_image is None:
            messagebox.showwarning("Attenzione", "Prima carica un'immagine!")
            return
        
        try:
            n_colors = int(self.n_colors_var.get())
            min_area = int(self.min_area_var.get())
        except ValueError:
            messagebox.showerror("Errore", "Parametri non validi")
            return
        
        self.status_var.set("Estrazione in corso...")
        self.root.update()
        
        # K-Means clustering
        image = self.original_image
        height, width = image.shape[:2]
        
        pixels = image.reshape((-1, 3)).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(pixels, n_colors, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
        
        self.regions = []
        region_id = 0
        
        for color_idx in range(n_colors):
            mask = (labels.flatten() == color_idx).reshape((height, width)).astype(np.uint8) * 255
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                if area < min_area:
                    continue
                
                # Colore medio
                mask_single = np.zeros((height, width), dtype=np.uint8)
                cv2.drawContours(mask_single, [contour], 0, 255, -1)
                mean_color = cv2.mean(image, mask=mask_single)[:3]
                b, g, r = int(mean_color[0]), int(mean_color[1]), int(mean_color[2])
                
                # Filtra bianco/nero puro
                if min(r, g, b) > 240 or max(r, g, b) < 30:
                    continue
                
                # Semplifica contorno
                epsilon = 0.001 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                region = Region(region_id, approx, (r, g, b), area)
                self.regions.append(region)
                region_id += 1
        
        # Ordina per area (più grandi prima)
        self.regions.sort(key=lambda r: r.area, reverse=True)
        
        # Riassegna ID
        for i, region in enumerate(self.regions):
            region.id = i
            region.name = f"Regione {i}"
        
        self._update_display()
        self._update_region_list()
        self.status_var.set(f"Estratte {len(self.regions)} regioni. Clicca per selezionare/deselezionare.")
    
    def _update_display(self):
        """Aggiorna visualizzazione canvas"""
        if self.original_image is None:
            return
        
        # Crea copia per disegno
        display = self.original_image.copy()
        
        # Disegna regioni
        for region in self.regions:
            if region.selected:
                # Regione selezionata: bordo verde spesso
                cv2.drawContours(display, [region.contour], 0, (0, 255, 0), 3)
                
                # Etichetta
                cx, cy = region.centroid
                cv2.putText(display, str(region.id), (cx-10, cy+5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 3)
                cv2.putText(display, str(region.id), (cx-10, cy+5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 100, 0), 2)
            else:
                # Regione deselezionata: bordo rosso sottile
                cv2.drawContours(display, [region.contour], 0, (0, 0, 255), 1)
        
        # Ridimensiona per canvas
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        if canvas_w > 1 and canvas_h > 1:
            img_h, img_w = display.shape[:2]
            
            scale_w = canvas_w / img_w
            scale_h = canvas_h / img_h
            self.scale_factor = min(scale_w, scale_h, 1.0)
            
            new_w = int(img_w * self.scale_factor)
            new_h = int(img_h * self.scale_factor)
            
            display = cv2.resize(display, (new_w, new_h))
        
        # Converti per Tkinter
        display_rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        self.display_image = display
        
        pil_image = Image.fromarray(display_rgb)
        self.tk_image = ImageTk.PhotoImage(pil_image)
        
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
    
    def _update_region_list(self):
        """Aggiorna listbox regioni"""
        self.region_listbox.delete(0, tk.END)
        
        for region in self.regions:
            status = "✅" if region.selected else "❌"
            text = f"{status} [{region.id}] {region.name} ({region.area:.0f}px²)"
            self.region_listbox.insert(tk.END, text)
            
            # Colora sfondo
            if region.selected:
                self.region_listbox.itemconfig(tk.END, bg='#d4edda')
            else:
                self.region_listbox.itemconfig(tk.END, bg='#f8d7da')
    
    def _on_click(self, event):
        """Gestisce click su canvas"""
        if not self.regions or self.original_image is None:
            return
        
        # Converti coordinate canvas → immagine originale
        x = int(event.x / self.scale_factor)
        y = int(event.y / self.scale_factor)
        
        # Trova regione cliccata
        for region in self.regions:
            result = cv2.pointPolygonTest(region.contour, (float(x), float(y)), False)
            if result >= 0:
                # Toggle selezione
                region.selected = not region.selected
                self._update_display()
                self._update_region_list()
                
                status = "selezionata" if region.selected else "deselezionata"
                self.status_var.set(f"Regione {region.id} ({region.name}) {status}")
                return
    
    def _on_resize(self, event):
        """Gestisce ridimensionamento finestra"""
        self._update_display()
    
    def _on_list_select(self, event):
        """Gestisce selezione nella lista"""
        selection = self.region_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.regions):
                region = self.regions[idx]
                self.name_var.set(region.name)
    
    def _on_list_double_click(self, event):
        """Toggle selezione con doppio click"""
        selection = self.region_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.regions):
                region = self.regions[idx]
                region.selected = not region.selected
                self._update_display()
                self._update_region_list()
    
    def _apply_name(self):
        """Applica nome alla regione selezionata"""
        selection = self.region_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.regions):
                self.regions[idx].name = self.name_var.get()
                self._update_region_list()
    
    def _use_db_name(self):
        """Usa nome dal database"""
        selection = self.region_listbox.curselection()
        db_name = self.db_region_var.get()
        
        if selection and db_name:
            idx = selection[0]
            if idx < len(self.regions):
                # Estrai solo il nome (senza paese)
                name = db_name.split(' (')[0] if ' (' in db_name else db_name
                self.regions[idx].name = name
                self.name_var.set(name)
                self._update_region_list()
    
    def _filter_db_regions(self, event=None):
        """Filtra regioni nel dropdown in base alla ricerca"""
        search_text = self.search_var.get().lower()
        
        if not search_text:
            self.db_combo['values'] = [''] + self.all_db_regions
        else:
            filtered = [r for r in self.all_db_regions if search_text in r.lower()]
            self.db_combo['values'] = [''] + filtered[:100]  # Limita a 100 risultati
    
    def _auto_assign_italian_regions(self):
        """Abbina automaticamente le regioni estratte confrontando le forme con GADM"""
        if not hasattr(self, 'italy_regions') or self.italy_regions is None:
            messagebox.showerror("Errore", "Database regioni italiane non caricato!")
            return
        
        if not self.regions:
            messagebox.showerror("Errore", "Nessuna regione estratta! Estrai prima le regioni dall'immagine.")
            return
        
        selected_regions = [(i, r) for i, r in enumerate(self.regions) if r.selected]
        if not selected_regions:
            messagebox.showwarning("Attenzione", "Nessuna regione selezionata!")
            return
        
        self.status_var.set("Confronto forme in corso...")
        self.root.update()
        
        # Prepara contorni dal database GADM
        db_contours = {}
        for _, row in self.italy_regions.iterrows():
            name = row['NAME_1']
            geom = row.geometry
            
            # Estrai coordinate del poligono principale
            if geom.geom_type == 'MultiPolygon':
                largest = max(geom.geoms, key=lambda p: p.area)
                coords = np.array(largest.exterior.coords)
            elif geom.geom_type == 'Polygon':
                coords = np.array(geom.exterior.coords)
            else:
                continue
            
            # Normalizza (0-1000)
            coords_norm = coords - coords.min(axis=0)
            if coords_norm.max() > 0:
                coords_norm = coords_norm / coords_norm.max() * 1000
            
            contour = coords_norm.astype(np.int32).reshape(-1, 1, 2)
            db_contours[name] = contour
        
        # Calcola TUTTI gli score per ogni coppia (regione estratta, regione DB)
        all_scores = []
        
        for i, region in selected_regions:
            # Normalizza il contorno estratto
            contour = region.contour.copy()
            contour_2d = contour.reshape(-1, 2)
            contour_norm = contour_2d - contour_2d.min(axis=0)
            if contour_norm.max() > 0:
                contour_norm = contour_norm / contour_norm.max() * 1000
            contour_norm = contour_norm.astype(np.int32).reshape(-1, 1, 2)
            
            for name, db_contour in db_contours.items():
                try:
                    # Prova diversi metodi e prendi il migliore
                    score1 = cv2.matchShapes(contour_norm, db_contour, cv2.CONTOURS_MATCH_I1, 0)
                    score2 = cv2.matchShapes(contour_norm, db_contour, cv2.CONTOURS_MATCH_I2, 0)
                    score3 = cv2.matchShapes(contour_norm, db_contour, cv2.CONTOURS_MATCH_I3, 0)
                    
                    # Usa la media pesata (I1 è spesso migliore)
                    score = min(score1, score2, score3)
                    
                    all_scores.append((i, name, score, region.area))
                except:
                    continue
        
        # Ordina per score (migliori prima)
        all_scores.sort(key=lambda x: x[2])
        
        # Assegnazione greedy: prendi i migliori match senza duplicati
        assignments = {}
        used_db_regions = set()
        used_extracted = set()
        match_details = []
        
        for idx, db_name, score, area in all_scores:
            if idx in used_extracted or db_name in used_db_regions:
                continue
            
            # Accetta match con soglia più alta
            if score < 2.0:  # Soglia molto più permissiva
                assignments[idx] = (db_name, score)
                used_db_regions.add(db_name)
                used_extracted.add(idx)
                match_details.append((idx, db_name, score))
        
        # Applica le assegnazioni
        for idx, (name, score) in assignments.items():
            self.regions[idx].name = name
        
        self._update_region_list()
        
        count = len(assignments)
        selected_count = len(selected_regions)
        self.status_var.set(f"✓ Abbinate {count}/{selected_count} regioni tramite confronto forme")
        
        # Mostra risultato dettagliato
        if count > 0:
            match_details.sort(key=lambda x: x[2])
            msg = f"Abbinate automaticamente {count} regioni!\n\n"
            
            msg += "Migliori match:\n"
            for idx, name, score in match_details[:5]:
                msg += f"  • {name} (score: {score:.3f})\n"
            
            if len(match_details) > 5:
                msg += f"\nPeggiori match:\n"
                for idx, name, score in match_details[-3:]:
                    msg += f"  • {name} (score: {score:.3f})\n"
            
            unassigned = selected_count - count
            if unassigned > 0:
                msg += f"\n{unassigned} regioni non abbinate"
                # Trova quali regioni DB non sono state usate
                unused_db = set(db_contours.keys()) - used_db_regions
                if unused_db and len(unused_db) <= 5:
                    msg += f"\nRegioni mancanti: {', '.join(sorted(unused_db))}"
            
            messagebox.showinfo("Abbinamento completato", msg)
        else:
            messagebox.showwarning("Nessun abbinamento", 
                "Non è stato possibile abbinare le regioni.\n\n"
                "Le forme estratte potrebbero essere troppo diverse da quelle reali.\n"
                "Prova a:\n"
                "- Usare meno colori nell'estrazione\n"
                "- Aumentare l'area minima\n"
                "- Verificare che le regioni estratte siano corrette")

    def _select_all(self):
        """Seleziona tutte le regioni"""
        for region in self.regions:
            region.selected = True
        self._update_display()
        self._update_region_list()
    
    def _deselect_all(self):
        """Deseleziona tutte le regioni"""
        for region in self.regions:
            region.selected = False
        self._update_display()
        self._update_region_list()
    
    def _pixel_to_latlon(self, x: int, y: int) -> Tuple[float, float]:
        """Converti pixel in lat/lon"""
        if self.original_image is None:
            return (x, y)
        
        height, width = self.original_image.shape[:2]
        lat_min, lat_max = self.calibration['lat_range']
        lon_min, lon_max = self.calibration['lon_range']
        
        lon = lon_min + (x / width) * (lon_max - lon_min)
        lat = lat_max - (y / height) * (lat_max - lat_min)
        
        return (lon, lat)
    
    def _export_geojson(self):
        """Esporta regioni selezionate in GeoJSON"""
        selected_regions = [r for r in self.regions if r.selected]
        
        if not selected_regions:
            messagebox.showwarning("Attenzione", "Nessuna regione selezionata!")
            return
        
        # Dialog calibrazione
        if not self._show_calibration_dialog():
            return
        
        # Crea features
        features = []
        
        for region in selected_regions:
            # Converti contorno in coordinate
            points = [(int(p[0][0]), int(p[0][1])) for p in region.contour]
            coordinates = [list(self._pixel_to_latlon(x, y)) for x, y in points]
            
            # Chiudi poligono
            if coordinates and coordinates[0] != coordinates[-1]:
                coordinates.append(coordinates[0])
            
            feature = {
                "type": "Feature",
                "properties": {
                    "id": region.id,
                    "name": region.name,
                    "color": f"rgb({region.color[0]},{region.color[1]},{region.color[2]})",
                    "area_pixels": region.area
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coordinates]
                }
            }
            features.append(feature)
        
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }
        
        # Dialog salvataggio
        if self.image_path:
            default_name = self.image_path.stem + "_selected.geojson"
        else:
            default_name = "export.geojson"
        
        file_path = filedialog.asksaveasfilename(
            title="Salva GeoJSON",
            defaultextension=".geojson",
            initialfile=default_name,
            filetypes=[("GeoJSON", "*.geojson"), ("JSON", "*.json")]
        )
        
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(geojson, f, indent=2, ensure_ascii=False)
            
            self.status_var.set(f"Esportate {len(selected_regions)} regioni in {Path(file_path).name}")
            messagebox.showinfo("Successo", f"GeoJSON salvato!\n\n{len(selected_regions)} regioni esportate.\n\nVisualizza su: http://geojson.io")
    
    def _show_calibration_dialog(self) -> bool:
        """Mostra dialog per calibrazione geografica"""
        dialog = tk.Toplevel(self.root)
        dialog.title("🎯 Calibrazione Geografica")
        dialog.geometry("350x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        result = {'ok': False}
        
        ttk.Label(dialog, text="Inserisci le coordinate dell'area della mappa:", 
                 font=('Arial', 10, 'bold')).pack(pady=10)
        
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Preset
        ttk.Label(frame, text="Preset:").grid(row=0, column=0, sticky=tk.W)
        preset_var = tk.StringVar(value="italy")
        preset_combo = ttk.Combobox(frame, textvariable=preset_var, values=["italy", "europe", "world", "custom"])
        preset_combo.grid(row=0, column=1, columnspan=2, sticky=tk.EW, pady=2)
        
        # Coordinate
        lat_min_var = tk.StringVar(value="36.0")
        lat_max_var = tk.StringVar(value="47.5")
        lon_min_var = tk.StringVar(value="6.5")
        lon_max_var = tk.StringVar(value="18.5")
        
        def update_preset(*args):
            preset = preset_var.get()
            if preset == "italy":
                lat_min_var.set("36.0"); lat_max_var.set("47.5")
                lon_min_var.set("6.5"); lon_max_var.set("18.5")
            elif preset == "europe":
                lat_min_var.set("35.0"); lat_max_var.set("72.0")
                lon_min_var.set("-25.0"); lon_max_var.set("45.0")
            elif preset == "world":
                lat_min_var.set("-90.0"); lat_max_var.set("90.0")
                lon_min_var.set("-180.0"); lon_max_var.set("180.0")
        
        preset_combo.bind('<<ComboboxSelected>>', update_preset)
        
        ttk.Label(frame, text="Lat min (sud):").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(frame, textvariable=lat_min_var, width=10).grid(row=1, column=1)
        ttk.Label(frame, text="Lat max (nord):").grid(row=2, column=0, sticky=tk.W)
        ttk.Entry(frame, textvariable=lat_max_var, width=10).grid(row=2, column=1)
        ttk.Label(frame, text="Lon min (ovest):").grid(row=3, column=0, sticky=tk.W)
        ttk.Entry(frame, textvariable=lon_min_var, width=10).grid(row=3, column=1)
        ttk.Label(frame, text="Lon max (est):").grid(row=4, column=0, sticky=tk.W)
        ttk.Entry(frame, textvariable=lon_max_var, width=10).grid(row=4, column=1)
        
        def on_ok():
            try:
                self.calibration = {
                    'lat_range': (float(lat_min_var.get()), float(lat_max_var.get())),
                    'lon_range': (float(lon_min_var.get()), float(lon_max_var.get()))
                }
                result['ok'] = True
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Errore", "Inserisci coordinate valide")
        
        def on_cancel():
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Annulla", command=on_cancel).pack(side=tk.LEFT, padx=5)
        
        dialog.wait_window()
        return result['ok']


def main():
    root = tk.Tk()
    app = MapSelectorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
