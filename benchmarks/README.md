# Benchmarks

Benchmark minimale per valutare conversioni su mappe difficili (rumore, testo, skew/rotazione).

## Struttura

- `fixtures/*.json`: dataset rappresentativo (attualmente sintetico e versionato)
- `thresholds.json`: soglie minime per release
- `run_benchmark.py`: harness KPI + report pass/fail

## KPI calcolati

- precisione poligoni (matching IoU)
- recall poligoni (matching IoU)
- errore spaziale medio (metri, distanza centroidi georeferenziati)
- confronto errore georeferenziazione `legacy` vs `cv_auto` (metri)
- tempo medio di conversione (secondi)

## Esecuzione

```bash
python benchmarks/run_benchmark.py
```

Oppure via gate completo:

```bash
python scripts/verify.py
```

Il comando termina con codice `0` se tutte le soglie sono rispettate, altrimenti `1`.
