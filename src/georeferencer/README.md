# 🗺️ Map Georeferencer

## Approccio
Questo tool usa la **georeferenziazione diretta** invece del shape matching:

1. **Calibrazione**: L'utente indica 4 punti di riferimento sulla mappa con le loro coordinate reali
2. **Estrazione**: K-Means estrae le regioni colorate
3. **Point-in-Polygon**: Per ogni regione, il centroide viene convertito in coordinate geografiche e si cerca quale regione del database GADM lo contiene
4. **Risultato**: Accuratezza ~100% se la calibrazione è corretta

## Perché funziona
- Non dipende dalla forma delle regioni (che nelle mappe stilizzate è sempre diversa)
- Usa geometria matematica precisa (point-in-polygon)
- Il database GADM ha i confini REALI delle regioni

## Requisiti
```bash
pip install opencv-python numpy geopandas shapely pillow
```

## Uso
```bash
python map_georeferencer.py
```

1. Apri un'immagine di mappa
2. Clicca "Calibra" e seleziona 4 punti con le loro coordinate
3. Clicca "Estrai Regioni"
4. Clicca "Identifica Automatico" → le regioni vengono identificate dal database GADM
5. Esporta in GeoJSON
