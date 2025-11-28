# Test Comparison - Shape Matching with Worldwide Database

Questo folder contiene il nuovo approccio basato su **shape matching**: invece di segmentare pixel, confronta forme estratte con un database geografico mondiale per riconoscere automaticamente regioni/paesi.

---

## 🎯 Come Funziona

1. **Estrazione forme** dall'immagine (K-Means + contour detection)
2. **Normalizzazione** geometrica (invariante a scala/rotazione/traslazione)
3. **Confronto** con database Natural Earth (>4000 regioni mondiali)
4. **Matching** tramite:
   - Hausdorff distance (similarità forme)
   - IoU (Intersection over Union)
5. **Riconoscimento automatico** nome regione/stato
6. **GeoJSON preciso** usando geometrie ufficiali dal database

---

## 🚀 Installazione

```bash
# Installa dipendenze aggiuntive
pip install geopandas scipy

# Al primo avvio, il database Natural Earth (~20MB) verrà scaricato automaticamente
```

---

## 📖 Uso

```bash
python shape_matcher.py
```

Quando richiesto, inserisci il path dell'immagine mappa. Il tool:
- Estrae forme automaticamente
- Le confronta con il database mondiale
- Riconosce regioni/stati con punteggio di confidenza
- Genera GeoJSON con nomi corretti e geometrie precise

---

## 🌍 Database

Usa **Natural Earth** (https://www.naturalearthdata.com):
- **Admin 1**: Stati/province/regioni (>4000 entità)
- Copertura mondiale completa
- Geometrie ufficiali ad alta risoluzione
- Gratuito e open-source

---

## ✨ Vantaggi vs K-Means

| K-Means (vecchio) | Shape Matching (nuovo) |
|-------------------|------------------------|
| Bordi imprecisi | Geometrie ufficiali precise |
| Georeferenziazione manuale | Coordinate già corrette |
| Nessun nome regione | Riconoscimento automatico nomi |
| Solo segmentazione colori | Matching semantico |

---

## 🔧 Parametri

Nel codice `shape_matcher.py`:

```python
# Estrazione
n_colors = 60          # Cluster K-Means
min_area = 300         # Area minima pixel

# Matching
confidence_threshold = 0.5   # Soglia confidenza (0.0-1.0)
top_k = 5                   # Top N candidati per forma
```

---

## 📊 Output

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "Lombardia",
        "admin": "Italy",
        "region": "Europe",
        "confidence": 0.87,
        "source": "shape_matching"
      },
      "geometry": { "type": "Polygon", "coordinates": [...] }
    }
  ]
}
```

---

## 🐛 Troubleshooting

**Download database fallisce?**
- Scarica manualmente da: https://www.naturalearthdata.com/downloads/10m-cultural-vectors/
- Cerca "Admin 1 – States, Provinces"
- Estrai in `src/tests/test comparison/geodata/`

**Score troppo bassi?**
- Abbassa `confidence_threshold` (es. 0.3)
- Aumenta `n_colors` per forme più dettagliate
- Verifica che la mappa sia ben definita (colori distinti)

**Regione non riconosciuta?**
- Il database copre stati/province principali
- Regioni molto piccole potrebbero non essere incluse
- Prova con mappe a risoluzione più alta

---

## 🔮 Prossimi Sviluppi

- [ ] Supporto per database custom (carica il tuo shapefile)
- [ ] Interfaccia web per drag&drop
- [ ] Caching dei match per velocizzare
- [ ] Supporto Multi-level (paesi → regioni → città)
- [ ] Correzione manuale match sbagliati

---

## 📚 Riferimenti

- Natural Earth: https://www.naturalearthdata.com/
- Shapely: https://shapely.readthedocs.io/
- GeoPandas: https://geopandas.org/
- Hausdorff Distance: https://en.wikipedia.org/wiki/Hausdorff_distance
