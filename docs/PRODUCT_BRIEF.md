# Product Brief

## Product Name
Map to GeoJSON Converter

## Problem
Professionisti GIS e team territoriali spendono troppo tempo a digitalizzare mappe raster,
allinearle geograficamente e validare output prima dell'uso operativo.

## Value Proposition
Convertire immagini di mappe in GeoJSON validi in pochi minuti, con georeferenziazione
assistita e metriche qualità trasparenti.

## Primary ICP
- Consulenti GIS e studi tecnici territoriali
- Team planning in enti locali
- Ricerca su cartografia storica

## Core Jobs To Be Done
1. Caricare una mappa e segmentare aree rilevanti.
2. Posizionare in coordinate geografiche con fallback robusto.
3. Esportare output GeoJSON pronto per strumenti GIS.

## Success Metrics
- Time-to-first-export < 10 minuti
- Export success rate > 95%
- Circle center error p50 < 20m (dataset target)
- API error rate (5xx) < 1%

## Scope (Current Build)
- Upload image + segmentation
- Georeferencing (bounds, GCP, cv_auto)
- Circle detection and dual export (center/radius + GeoJSON polygon)
- Benchmark and verify quality gates

## Next Product Milestones
- Auth/workspace/project persistence
- Billing and usage quotas
- Project history and job orchestration
