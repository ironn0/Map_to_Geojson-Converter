Project Management - Map to GeoJSON Converter
=============================================
[TOC]

v1.0.0 - 2026-03-07

---

# Project Objectives

Project objectives define the specific results that the project aims to achieve. These objectives should be clear, measurable, and realistic, allowing for evaluation of project success upon completion.

## Continuity Objectives

The Map to GeoJSON Converter project was born as a free and open-source alternative to expensive commercial databases (e.g., Geochron, €500). The continuity objective is to ensure accessibility to geospatial data for students, researchers, and organizations with limited resources.

**Long-term Vision:**
- Keep the project completely free and open-source
- Build an active community of contributors
- Become a de facto standard for map-to-GeoJSON conversion

## Specific Project Objectives

### Quality Objectives

| Objective | Description | KPI |
|-----------|-------------|-----|
| Conversion accuracy | Precision in polygon extraction from maps | ≥ 85% accuracy |
| Format support | Support for PNG, JPG, WebP, SVG | 4+ formats supported |
| Output quality | Valid and standards-compliant GeoJSON | 100% GeoJSON validity |
| Usability | Intuitive web interface | Setup time < 5 minutes |
| Stability | Reliable application without crashes | Uptime ≥ 99% |

**Technical output specifications:**
- Format: Standard GeoJSON FeatureCollection
- Coordinates: WGS84 system (EPSG:4254)
- Properties: Customizable metadata for each region
- Compatibility: Direct import into QGIS, Leaflet, Mapbox

### Time Objectives

| Milestone | Description | Deadline |
|-----------|-------------|----------|
| v0.1.x | Working prototype with basic segmentation | ✅ Completed |
| v0.2.0 | Web app with interactive georeferencing | Q1 2026 |
| v0.3.0 | Advanced polygon editor | Q2 2026 |
| v1.0.0 | Stable release with complete documentation | Q3 2026 |

### Cost Objectives

| Item | Budget | Notes |
|------|--------|-------|
| Software licenses | €0 | 100% open-source (PyTorch, OpenCV, GDAL) |
| Infrastructure | €0 | Local execution |
| Human resources | Volunteer | Student team |
| Hardware | Existing | Use of local resources |

**Total budget: €0** (zero-cost project)

---

## SMART Objectives

Following the SMART methodology, project objectives are defined as:

| Criterion | Application to Project |
|-----------|------------------------|
| **S**pecific | Convert geographic map images to GeoJSON format using computer vision and AI |
| **M**easurable | ≥85% accuracy, <30s conversion time, 4+ formats supported |
| **A**chievable | Mature open-source technologies (OpenCV, PyTorch), existing team skills |
| **R**elevant | Responds to growing demand for accessible geospatial data |
| **T**ime-bound | v1.0.0 release by Q3 2026 |

---

# Project Organizational Structures

## Adopted Structure: Lightweight Matrix

The Map to GeoJSON Converter project adopts a **lightweight matrix structure**, typical of university open-source projects:

```
┌─────────────────────────────────────────────────────────┐
│                    COORDINATION                         │
│              (Strategic decisions)                      │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  DEVELOPMENT  │ │   UI/UX       │ │   RESEARCH    │
│  Fabio Ferro  │ │ Mattia Marrocu│ │ Luca Cortinovis│
│               │ │               │ │               │
│ - Backend     │ │ - Frontend    │ │ - GIS/Geo     │
│ - AI/CV       │ │ - Web Design  │ │ - Marketing   │
│ - Core Logic  │ │ - UX Testing  │ │ - Use Cases   │
└───────────────┘ └───────────────┘ └───────────────┘
```

## Team and Responsibilities

| Role | Owner | Responsibilities |
|------|-------|------------------|
| Lead Developer | Fabio Ferro | Core development, CV algorithms, AI integration |
| UI/UX Designer | Mattia Marrocu | Web interface, frontend, user experience |
| GIS Researcher | Luca Cortinovis | Geospatial research, competitor analysis, marketing |
| Community | Open-source | Contributions, bug reports, feature requests |

## Why Matrix Structure

The matrix structure was chosen because:

1. **Complex and innovative projects**: The project combines AI, computer vision, and GIS
2. **Multidisciplinary team**: Diverse skills (development, design, research)
3. **Part-time resources**: Members dedicate partial time to the project
4. **Flexibility**: Allows rapid adaptation to changes

### Socio-Organizational Conditions

For the matrix structure to be effective, the team maintains:

| Condition | Implementation in Project |
|-----------|---------------------------|
| High communication | GitHub Issues, Pull Requests, Discussions |
| Teamwork orientation | Code reviews, pair programming |
| Goal orientation | Clear milestones, defined KPIs |
| Delegation and autonomy | Each member manages their own domain |
| Problem solving | Iterative approach, experimentation |
| Knowledge sharing | Complete documentation, code comments |

---

# Work Breakdown Structure (WBS)

## Work Decomposition

```
Map to GeoJSON Converter
│
├── 1. CORE ENGINE
│   ├── 1.1 Image segmentation
│   │   ├── 1.1.1 K-Means clustering
│   │   ├── 1.1.2 Edge detection
│   │   └── 1.1.3 Contour extraction
│   ├── 1.2 Georeferencing
│   │   ├── 1.2.1 Control point alignment
│   │   ├── 1.2.2 Coordinate transformation
│   │   └── 1.2.3 WGS84 projection
│   └── 1.3 GeoJSON Export
│       ├── 1.3.1 FeatureCollection generation
│       ├── 1.3.2 Output validation
│       └── 1.3.3 Polygon optimization
│
├── 2. WEB APPLICATION
│   ├── 2.1 Backend (FastAPI)
│   │   ├── 2.1.1 API routes
│   │   ├── 2.1.2 Session management
│   │   └── 2.1.3 File handling
│   ├── 2.2 Frontend
│   │   ├── 2.2.1 UI components
│   │   ├── 2.2.2 Polygon editor
│   │   └── 2.2.3 Interactive map
│   └── 2.3 Integration
│       ├── 2.3.1 JavaScript API
│       └── 2.3.2 State management
│
├── 3. DOCUMENTATION
│   ├── 3.1 README and guides
│   ├── 3.2 API documentation
│   ├── 3.3 Use cases
│   └── 3.4 Feasibility study
│
└── 4. TESTING & QUALITY
    ├── 4.1 Unit tests
    ├── 4.2 Integration tests
    └── 4.3 User acceptance testing
```

---

# Risk Management

## Risk Matrix

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Training data quality | Medium | High | Use verified open-source datasets |
| Code complexity | Medium | Medium | Documentation, code reviews |
| Long development times | High | Medium | Iterative approach, MVP |
| Market adoption | Medium | High | Community-driven marketing |
| Competition | Low | Medium | Focus on AI and ease of use |
| Library dependencies | Low | High | Pin versions, continuous testing |

## Contingency Plan

1. **Development delays**: Scope reduction, focus on core functionality
2. **Critical bugs**: Version rollback, priority hotfixes
3. **Insufficient resources**: Open-source community involvement

---

# Communication and Reporting

## Communication Channels

| Channel | Purpose | Frequency |
|---------|---------|-----------|
| GitHub Issues | Bug reports, feature requests | Continuous |
| GitHub Discussions | Q&A, community support | Continuous |
| Pull Requests | Code review, contributions | Per change |
| CHANGELOG | Change history | Per release |
| README | Main documentation | Continuous updates |

## Project Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Version | v1.0.0 | v0.1.3 |
| GitHub Stars | 100+ | Growing |
| Contributors | 10+ | 3 |
| Issues resolved | 80%+ | To monitor |
| Test coverage | 70%+ | To implement |

---

# Conclusions

The Map to GeoJSON Converter project follows an agile and open-source management approach, with:

- **Clear and measurable SMART objectives**
- **Lightweight matrix structure** suitable for distributed teams
- **Zero budget** thanks to open-source technologies
- **Proactive risk management**
- **Transparent communication** via GitHub

The chosen organizational structure balances result orientation with the flexibility needed for an evolving open-source project.

---

## References

- [Main README](../README.md)
- [Feasibility Study](feasibility/README.md)
- [Contributing Guide](../CONTRIBUTING.md)
- [Use Cases](../USE_CASES.md)
- [Competitor Analysis](feasibility/requirements/Competitor_Analysis.md)
