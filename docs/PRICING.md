# Pricing Draft

## Principles
- Prezzi semplici e leggibili.
- Limiti legati a uso reale (upload/export).
- Upgrade naturale per team e uso continuativo.

## Plans

### Free
- 20 upload/mese
- Max 5 MB per file
- Export GeoJSON base
- Nessun supporto prioritario

### Pro
- 500 upload/mese
- Max 25 MB per file
- Export completo + circle metrics
- Supporto email standard

### Team
- Upload condivisi workspace
- Max 50 MB per file
- Gestione utenti e progetti
- Supporto prioritario

## Metering Candidates
- upload_count_monthly
- export_count_monthly
- total_processing_seconds

## Billing Notes
- Provider suggerito: Stripe
- Webhook minimi: checkout completed, subscription updated, invoice paid/failed
- Enforcement quote lato API middleware
