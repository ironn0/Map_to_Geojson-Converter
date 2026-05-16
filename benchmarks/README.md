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
- errore centro cerchio georeferenziato (p50, metri)
- errore raggio cerchio georeferenziato (p50, metri)
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

## Soglia cv_auto (stato attuale e fase successiva)

- Gate corrente: `cv_auto_min_improvement_m = 10000` (target positivo minimo per release).
- Target fase successiva: `cv_auto_target_next_phase_m = 20000`.
- Il report benchmark include `cv_auto_next_phase_gap_m` per misurare quanto manca al target successivo.
- Gate cerchi ad alta precisione:
  - `circle_center_error_p50_max_m = 20`
  - `circle_radius_error_p50_max_m = 30`
