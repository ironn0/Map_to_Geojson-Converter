# Roadmap to v1.0.0

This roadmap translates the current technical gaps into measurable milestones.

## Scope baseline
- Primary runtime path: `src/tests/webapp_modular/`
- Quality gates: `python scripts/verify.py` and CI workflow in `.github/workflows/ci.yml`
- Version target: `v1.0.0`

## Milestone plan

### M1 - Core Reliability (target: 2 weeks)
Focus:
- Boundaries and geometry validation hardening in export/alignment.
- Defensive checks around invalid image dimensions and malformed contours.
- Georeferencing UX coherence (rotation policy documented and enforced).

Acceptance criteria:
- 0 unhandled exceptions for invalid bounds/contour payloads in `/api/export` and `/api/align`.
- API returns 4xx (not 5xx) for client-invalid geospatial inputs.
- Unit/API tests cover bounds ordering, non-finite values, and empty contours.

KPIs:
- At least 6 automated tests passing locally and in CI.
- 100% of known invalid-input scenarios mapped to explicit HTTP errors.

### M2 - Quality Baseline Expansion (target: 2 weeks after M1)
Focus:
- Extend test coverage for segmentation and session lifecycle.
- Keep lint/test checks mandatory on PRs.
- Add contributor-friendly verification flow and docs.

Acceptance criteria:
- CI green on pull requests (lint + tests).
- New backend routes are covered by at least one test each.
- Contribution docs include one-command local quality checks.

KPIs:
- Minimum 15 backend-focused tests.
- 90%+ PRs merged with green CI on first rerun.

### M3 - Architecture Cleanup (target: 3 weeks after M2)
Focus:
- Clarify maintenance boundary between `webapp_modular`, `webapp`, and `test SAM`.
- Reduce duplication in pixel-to-geo conversion logic.
- Improve doc consistency (paths, runbooks, feature status).

Acceptance criteria:
- README and module docs reference only existing files/commands.
- Shared conversion behavior is documented in a single technical note.
- Legacy folders explicitly marked as `legacy` or `experimental`.

KPIs:
- 0 broken documentation references in top-level docs.
- 1 canonical conversion spec used by both API and frontend.

### M4 - v1 Product Readiness (target: 4 weeks after M3)
Focus:
- GeoJSON robustness improvements (shape validity/simplification policies).
- Session scalability safeguards (TTL, memory limits, cleanup strategy).
- Minimal observability for operational debugging.

Acceptance criteria:
- Exported polygons pass GeoJSON validity checks for supported workflows.
- Session cleanup strategy documented and tested.
- Structured error logs available for API failures.

KPIs:
- Conversion success rate >= 95% on curated benchmark maps.
- Median conversion time < 30 seconds for standard map inputs.
- No unresolved P1 bugs at release cut.

## Release checklist for v1.0.0
- [ ] `python scripts/verify.py` passes locally.
- [ ] CI workflow green on `main`.
- [ ] Changelog updated under release section.
- [ ] README screenshots and instructions validated against current UI.
- [ ] Tag `v1.0.0` created with release notes.
