/**
 * 🗺️ Georef Module
 * Gestione della georeferenziazione interattiva
 * 
 * Author: Map to GeoJSON Converter Project
 */

import { state } from './state.js';
import { el } from './dom.js';
import { toast, updateStep, showLoading, hideLoading } from './ui.js';
import * as api from './api.js';

let cornerMarkers = [];
const CV_QUALITY_CLASSES = ['cv-quality-neutral', 'cv-quality-success', 'cv-quality-warning'];

function setCvQualityStatus(text, tone = 'neutral') {
    if (!el.cvQualityStatus) return;
    el.cvQualityStatus.classList.remove(...CV_QUALITY_CLASSES);
    if (tone === 'success') {
        el.cvQualityStatus.classList.add('cv-quality-success');
    } else if (tone === 'warning') {
        el.cvQualityStatus.classList.add('cv-quality-warning');
    } else {
        el.cvQualityStatus.classList.add('cv-quality-neutral');
    }
    el.cvQualityStatus.textContent = text;
}

/**
 * Ottiene i bounds correnti
 * @returns {Object}
 */
export function getBounds() {
    return {
        north: parseFloat(el.boundNorth.value),
        south: parseFloat(el.boundSouth.value),
        east: parseFloat(el.boundEast.value),
        west: parseFloat(el.boundWest.value)
    };
}

/**
 * Valida bounds geografici prima delle chiamate API.
 * @param {Object} bounds
 * @returns {boolean}
 */
export function validateBounds(bounds) {
    const values = [bounds.north, bounds.south, bounds.east, bounds.west];
    if (values.some(v => !Number.isFinite(v))) return false;
    if (bounds.north <= bounds.south) return false;
    if (bounds.east <= bounds.west) return false;
    if (bounds.north > 90 || bounds.south < -90) return false;
    if (bounds.east > 180 || bounds.west < -180) return false;
    return true;
}

function getCvReferenceBounds() {
    return {
        north: parseFloat(el.cvRefBoundNorth.value),
        south: parseFloat(el.cvRefBoundSouth.value),
        east: parseFloat(el.cvRefBoundEast.value),
        west: parseFloat(el.cvRefBoundWest.value)
    };
}

/**
 * Restituisce payload georeferencing opt-in.
 * Torna null per comportamento legacy invariato.
 */
export function getGeoreferencingPayload() {
    if (!el.cvAutoEnabled?.checked) {
        return null;
    }

    if (!state.cvReferenceImageBase64) {
        toast('Carica un raster di riferimento per usare cv_auto', 'warning');
        return null;
    }

    const cvBounds = getCvReferenceBounds();
    if (!validateBounds(cvBounds)) {
        toast('Bounds del raster di riferimento non validi', 'error');
        return null;
    }

    return {
        mode: 'cv_auto',
        allow_fallback: true,
        min_matches: 30,
        inlier_threshold: 3.0,
        confidence_threshold: parseFloat(el.cvConfidenceThreshold.value || '0.35'),
        cv_reference_image_base64: state.cvReferenceImageBase64,
        cv_reference_bounds: cvBounds
    };
}

export function isCvAutoEnabled() {
    return !!el.cvAutoEnabled?.checked;
}

export function validateCvAutoConfiguration() {
    if (!isCvAutoEnabled()) return true;
    if (!state.cvReferenceImageBase64) {
        toast('cv_auto attivo: carica un raster di riferimento', 'warning');
        return false;
    }
    const cvBounds = getCvReferenceBounds();
    if (!validateBounds(cvBounds)) {
        toast('cv_auto attivo: bounds del raster di riferimento non validi', 'error');
        return false;
    }
    return true;
}

export function updateCvAutoUiState() {
    const enabled = isCvAutoEnabled();
    if (el.cvAutoControls) {
        el.cvAutoControls.classList.toggle('hidden', !enabled);
    }
    const inputs = [
        el.loadCvReferenceBtn,
        el.cvRefBoundNorth,
        el.cvRefBoundSouth,
        el.cvRefBoundEast,
        el.cvRefBoundWest,
        el.cvRefUseCurrentBoundsBtn,
        el.cvConfidenceThreshold,
    ];
    inputs.forEach((node) => {
        if (node) node.disabled = !enabled;
    });

    if (!enabled) {
        setCvQualityStatus('Qualità registrazione CV: non attiva (legacy default)', 'neutral');
    } else {
        setCvQualityStatus('Qualità registrazione CV: in attesa di esecuzione', 'neutral');
    }
}

export function resetCvAutoUiState() {
    if (el.cvAutoEnabled) el.cvAutoEnabled.checked = false;
    if (el.cvReferenceInfo) el.cvReferenceInfo.classList.add('hidden');
    if (el.cvReferenceName) el.cvReferenceName.textContent = '';
    if (el.cvReferenceFile) el.cvReferenceFile.value = '';
    if (el.cvConfidenceThreshold) el.cvConfidenceThreshold.value = '0.35';
    if (el.cvConfidenceThresholdValue) el.cvConfidenceThresholdValue.textContent = '0.35';
    setCvQualityStatus('Qualità registrazione CV: n/d', 'neutral');
    updateCvAutoUiState();
}

function updateCvQualityFromMetadata(meta, attemptedCvAuto) {
    if (!attemptedCvAuto || !meta) return;
    if (meta.fallback_from === 'cv_auto') {
        setCvQualityStatus(
            `Qualità registrazione CV: fallback (${meta.fallback_reason || 'motivo non disponibile'})`,
            'warning',
        );
        return;
    }
    if (meta.mode === 'cv_auto') {
        const conf = typeof meta.cv_confidence === 'number' ? meta.cv_confidence.toFixed(3) : String(meta.cv_confidence);
        const inlier = typeof meta.cv_inlier_ratio === 'number' ? meta.cv_inlier_ratio.toFixed(3) : String(meta.cv_inlier_ratio);
        setCvQualityStatus(`Qualità registrazione CV: confidence ${conf}, inlier ratio ${inlier}`, 'success');
    }
}

export function applyCvQualityFromMetadata(meta, attemptedCvAuto) {
    updateCvQualityFromMetadata(meta, attemptedCvAuto);
}

/**
 * Gestisce cambio preset
 */
export function handlePresetChange() {
    const preset = el.presetSelect.value;
    if (preset !== 'custom' && state.presets[preset]) {
        const b = state.presets[preset];
        el.boundNorth.value = b.north;
        el.boundSouth.value = b.south;
        el.boundEast.value = b.east;
        el.boundWest.value = b.west;
    }
}

/**
 * Apre il modal di georeferenziazione
 */
export function openGeorefModal() {
    if (!state.sessionId || !state.imageBase64) { 
        toast('Carica prima un\'immagine', 'warning'); 
        return; 
    }
    el.georefModal.classList.add('visible');
    setTimeout(initGeorefMap, 100);
}

/**
 * Chiude il modal di georeferenziazione
 */
export function closeGeorefModal() {
    el.georefModal.classList.remove('visible');
    cornerMarkers = [];
    if (state.georefMap) { 
        state.georefMap.remove(); 
        state.georefMap = null; 
        state.imageOverlay = null; 
    }
    if (el.georefMap) {
        el.georefMap.innerHTML = '';
    }
}

/**
 * Inizializza la mappa di georeferenziazione
 */
function initGeorefMap() {
    const b = getBounds();
    const center = [(b.north + b.south) / 2, (b.east + b.west) / 2];
    
    state.georefMap = L.map(el.georefMap, { center, zoom: 5 });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { 
        attribution: '© OpenStreetMap' 
    }).addTo(state.georefMap);
    
    const bounds = L.latLngBounds([b.south, b.west], [b.north, b.east]);
    state.georefInitialBounds = L.latLngBounds([b.south, b.west], [b.north, b.east]);
    state.imageOverlay = L.imageOverlay('data:image/png;base64,' + state.imageBase64, bounds, { 
        opacity: 0.7, 
        interactive: true 
    }).addTo(state.georefMap);
    state.overlayBounds = bounds;
    state.georefDirty = false;
    if (el.georefRotation) {
        el.georefRotation.value = String(state.georefRotationDegrees || 0);
    }
    if (el.georefOpacity) {
        el.georefOpacity.value = String(state.imageOverlay.options.opacity ?? 0.7);
    }
    
    createCornerMarkers();
    
    // Dragging the image
    const img = state.imageOverlay.getElement();
    if (img) {
        img.style.cursor = 'move';
        let dragging = false, startLatLng, startBounds;
        
        img.onmousedown = e => {
            dragging = true;
            startLatLng = state.georefMap.mouseEventToLatLng(e);
            startBounds = L.latLngBounds(state.overlayBounds.getSouthWest(), state.overlayBounds.getNorthEast());
            e.stopPropagation();
        };
        
        state.georefMap.on('mousemove', e => {
            if (!dragging) return;
            const dLat = e.latlng.lat - startLatLng.lat;
            const dLng = e.latlng.lng - startLatLng.lng;
            state.overlayBounds = L.latLngBounds(
                [startBounds.getSouth() + dLat, startBounds.getWest() + dLng],
                [startBounds.getNorth() + dLat, startBounds.getEast() + dLng]
            );
            state.imageOverlay.setBounds(state.overlayBounds);
            state.georefDirty = true;
            updateCornerMarkers();
        });
        
        state.georefMap.on('mouseup', () => dragging = false);
    }
    
    state.georefMap.fitBounds(bounds.pad(0.1));
    updateGeorefOverlay();
}

/**
 * Crea i marker agli angoli per il ridimensionamento
 */
function createCornerMarkers() {
    cornerMarkers.forEach(m => m.remove());
    cornerMarkers = [];
    
    const b = state.overlayBounds;
    const corners = [
        { pos: 'nw', latlng: [b.getNorth(), b.getWest()], cursor: 'nw-resize' },
        { pos: 'ne', latlng: [b.getNorth(), b.getEast()], cursor: 'ne-resize' },
        { pos: 'se', latlng: [b.getSouth(), b.getEast()], cursor: 'se-resize' },
        { pos: 'sw', latlng: [b.getSouth(), b.getWest()], cursor: 'sw-resize' }
    ];
    
    corners.forEach(corner => {
        const icon = L.divIcon({
            className: 'corner-marker',
            html: `<div class="corner-handle" style="cursor:${corner.cursor}"></div>`,
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        });
        
        const marker = L.marker(corner.latlng, { 
            icon, 
            draggable: true,
            autoPan: false
        }).addTo(state.georefMap);
        
        marker.cornerPos = corner.pos;
        marker.on('drag', e => handleCornerDrag(corner.pos, e.latlng));
        marker.on('dragend', () => updateCornerMarkers());
        
        cornerMarkers.push(marker);
    });
}

/**
 * Gestisce il trascinamento degli angoli
 */
function handleCornerDrag(pos, latlng) {
    const b = state.overlayBounds;
    let north = b.getNorth(), south = b.getSouth(), east = b.getEast(), west = b.getWest();
    
    switch(pos) {
        case 'nw': north = latlng.lat; west = latlng.lng; break;
        case 'ne': north = latlng.lat; east = latlng.lng; break;
        case 'se': south = latlng.lat; east = latlng.lng; break;
        case 'sw': south = latlng.lat; west = latlng.lng; break;
    }

    // Mantieni proporzioni immagine per evitare deformazioni durante lo scaling.
    const ratio = state.imageWidth > 0 && state.imageHeight > 0 ? state.imageWidth / state.imageHeight : 1;
    let width = east - west;
    let height = north - south;
    if (width <= 0 || height <= 0) return;
    if (width / height > ratio) {
        width = height * ratio;
    } else {
        height = width / ratio;
    }

    switch (pos) {
        case 'nw':
            west = b.getEast() - width;
            north = b.getSouth() + height;
            break;
        case 'ne':
            east = b.getWest() + width;
            north = b.getSouth() + height;
            break;
        case 'se':
            east = b.getWest() + width;
            south = b.getNorth() - height;
            break;
        case 'sw':
            west = b.getEast() - width;
            south = b.getNorth() - height;
            break;
    }

    if (north > south + 0.01 && east > west + 0.01) {
        state.overlayBounds = L.latLngBounds([south, west], [north, east]);
        state.imageOverlay.setBounds(state.overlayBounds);
        state.georefDirty = true;
        
        cornerMarkers.forEach(m => {
            if (m.cornerPos !== pos) {
                m.setLatLng(getCornerPosition(m.cornerPos));
            }
        });
    }
}

function getCornerPosition(pos) {
    const b = state.overlayBounds;
    switch(pos) {
        case 'nw': return [b.getNorth(), b.getWest()];
        case 'ne': return [b.getNorth(), b.getEast()];
        case 'se': return [b.getSouth(), b.getEast()];
        case 'sw': return [b.getSouth(), b.getWest()];
    }
}

function updateCornerMarkers() {
    cornerMarkers.forEach(m => m.setLatLng(getCornerPosition(m.cornerPos)));
}

/**
 * Aggiorna l'overlay di georeferenziazione
 */
export function updateGeorefOverlay() {
    if (!state.imageOverlay || !state.overlayBounds) return;
    
    const opacity = parseFloat(el.georefOpacity.value);
    const rotation = parseFloat(el.georefRotation.value || '0');
    
    el.georefOpacityValue.textContent = Math.round(opacity * 100) + '%';
    el.georefRotationValue.textContent = `${Math.round(rotation)}°`;
    
    state.imageOverlay.setOpacity(opacity);
    state.georefRotationDegrees = rotation;

    const img = state.imageOverlay.getElement();
    if (img) {
        img.style.transformOrigin = 'center center';
        img.style.transform = `rotate(${rotation}deg)`;
    }
}

/**
 * Applica la georeferenziazione
 */
export function applyGeoref() {
    if (!state.overlayBounds) { 
        toast('Errore nella georeferenziazione', 'error'); 
        return; 
    }

    const overlayFromMap = state.imageOverlay?.getBounds?.();
    const b = overlayFromMap || state.overlayBounds;
    state.overlayBounds = b;
    if (!validateBounds({ north: b.getNorth(), south: b.getSouth(), east: b.getEast(), west: b.getWest() })) {
        toast('Bounds risultanti non validi. Reimposta e riprova.', 'error');
        return;
    }

    if (!state.georefDirty) {
        toast('Nessuna modifica rilevata: bounds invariati.', 'info');
    }

    el.boundNorth.value = b.getNorth().toFixed(4);
    el.boundSouth.value = b.getSouth().toFixed(4);
    el.boundEast.value = b.getEast().toFixed(4);
    el.boundWest.value = b.getWest().toFixed(4);
    el.presetSelect.value = 'custom';

    const latSpan = b.getNorth() - b.getSouth();
    if (b.getNorth() > 75 || b.getSouth() < -75 || latSpan > 120) {
        toast(
            'Attenzione: bounds molto estesi o vicini ai poli possono deformare la scala su planisfero.',
            'warning',
        );
    }
    
    if (Math.abs(state.georefRotationDegrees) > 0.5) {
        toast(
            'Rotazione applicata solo come guida visiva: i bounds export restano assiali.',
            'warning',
        );
    }

    closeGeorefModal();
    toast('Coordinate geografiche applicate!', 'success');
    
    // Passa automaticamente allo step Export
    updateStep(4, state);
}

export function resetGeorefPosition() {
    if (!state.imageOverlay || !state.georefInitialBounds) return;
    state.overlayBounds = L.latLngBounds(
        state.georefInitialBounds.getSouthWest(),
        state.georefInitialBounds.getNorthEast(),
    );
    state.imageOverlay.setBounds(state.overlayBounds);
    state.georefDirty = true;
    updateCornerMarkers();
    toast('Posizione ripristinata ai bounds iniziali', 'info');
}

export function fitGeorefView() {
    if (!state.georefMap || !state.overlayBounds) return;
    state.georefMap.fitBounds(state.overlayBounds.pad(0.12));
}

export function resetGeorefRotation() {
    if (!el.georefRotation) return;
    el.georefRotation.value = '0';
    state.georefRotationDegrees = 0;
    updateGeorefOverlay();
    toast('Rotazione azzerata', 'info');
}

function _iterCoords(geometry, push) {
    if (!geometry || !geometry.type || !geometry.coordinates) return;
    if (geometry.type === 'Point') {
        push(geometry.coordinates);
        return;
    }
    if (geometry.type === 'MultiPoint' || geometry.type === 'LineString') {
        geometry.coordinates.forEach(push);
        return;
    }
    if (geometry.type === 'MultiLineString' || geometry.type === 'Polygon') {
        geometry.coordinates.forEach((ring) => ring.forEach(push));
        return;
    }
    if (geometry.type === 'MultiPolygon') {
        geometry.coordinates.forEach((poly) => poly.forEach((ring) => ring.forEach(push)));
    }
}

export function applyReferenceGeojsonBounds() {
    if (!state.referenceGeojson) {
        toast('Carica prima un GeoJSON di riferimento', 'warning');
        return;
    }
    let minLon = Infinity;
    let minLat = Infinity;
    let maxLon = -Infinity;
    let maxLat = -Infinity;
    const collect = (coord) => {
        if (!Array.isArray(coord) || coord.length < 2) return;
        const lon = Number(coord[0]);
        const lat = Number(coord[1]);
        if (!Number.isFinite(lon) || !Number.isFinite(lat)) return;
        minLon = Math.min(minLon, lon);
        maxLon = Math.max(maxLon, lon);
        minLat = Math.min(minLat, lat);
        maxLat = Math.max(maxLat, lat);
    };

    const gj = state.referenceGeojson;
    if (gj.type === 'FeatureCollection') {
        (gj.features || []).forEach((f) => _iterCoords(f.geometry, collect));
    } else if (gj.type === 'Feature') {
        _iterCoords(gj.geometry, collect);
    } else {
        _iterCoords(gj, collect);
    }

    const bounds = { north: maxLat, south: minLat, east: maxLon, west: minLon };
    if (!validateBounds(bounds)) {
        toast('Impossibile derivare bounds validi dal riferimento', 'error');
        return;
    }

    el.boundNorth.value = bounds.north.toFixed(4);
    el.boundSouth.value = bounds.south.toFixed(4);
    el.boundEast.value = bounds.east.toFixed(4);
    el.boundWest.value = bounds.west.toFixed(4);
    el.presetSelect.value = 'custom';
    toast('Bounds impostati dal GeoJSON di riferimento', 'success');
}

/**
 * Gestisce upload GeoJSON di riferimento
 * @param {Event} e - Evento change
 */
export async function handleReferenceUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    showLoading('Caricamento riferimento...');
    
    try {
        const data = await api.uploadReferenceGeoJSON(file);
        
        state.referenceGeojson = data.geojson;
        state.referenceName = file.name;
        
        el.referenceInfo.classList.remove('hidden');
        el.referenceInfo.querySelector('.reference-name').textContent = `${file.name} (${data.num_features} territories)`;
        el.alignBtn.disabled = state.regions.length === 0;
        
        toast(`Riferimento caricato: ${data.num_features} territori`, 'success');
        
    } catch (err) {
        toast('Errore: ' + err.message, 'error');
    } finally {
        hideLoading();
        e.target.value = '';
    }
}

/**
 * Rimuove il riferimento caricato
 */
export function clearReference(silent = false) {
    state.referenceGeojson = null;
    state.referenceName = null;
    el.referenceInfo.classList.add('hidden');
    if (!silent) {
        toast('Riferimento rimosso', 'info');
    }
}

/**
 * Gestisce upload raster riferimento per cv_auto.
 * @param {Event} e
 */
export async function handleCvReferenceImageUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const allowed = ['image/png', 'image/jpeg', 'image/webp'];
    if (!allowed.includes(file.type)) {
        toast('Formato non supportato. Usa PNG/JPEG/WebP.', 'error');
        e.target.value = '';
        return;
    }

    try {
        const b64 = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(new Error('Errore lettura file'));
            reader.readAsDataURL(file);
        });

        state.cvReferenceImageBase64 = b64;
        state.cvReferenceImageName = file.name;
        el.cvReferenceInfo.classList.remove('hidden');
        el.cvReferenceName.textContent = file.name;
        setCvQualityStatus('Qualità registrazione CV: riferimento caricato, pronto', 'neutral');
        toast('Raster riferimento CV caricato', 'success');
    } catch (err) {
        toast('Errore caricamento raster: ' + err.message, 'error');
    } finally {
        e.target.value = '';
    }
}

export function clearCvReference(silent = false) {
    state.cvReferenceImageBase64 = null;
    state.cvReferenceImageName = null;
    if (el.cvReferenceInfo) el.cvReferenceInfo.classList.add('hidden');
    if (el.cvReferenceName) el.cvReferenceName.textContent = '';
    if (el.cvReferenceFile) el.cvReferenceFile.value = '';
    setCvQualityStatus('Qualità registrazione CV: riferimento rimosso', 'neutral');
    if (!silent) {
        toast('Raster riferimento CV rimosso', 'info');
    }
}

/**
 * Sincronizza i bounds CV con i bounds correnti.
 */
export function syncCvReferenceBoundsFromCurrent() {
    el.cvRefBoundNorth.value = el.boundNorth.value;
    el.cvRefBoundSouth.value = el.boundSouth.value;
    el.cvRefBoundEast.value = el.boundEast.value;
    el.cvRefBoundWest.value = el.boundWest.value;
    toast('Bounds riferimento CV sincronizzati con i bounds correnti', 'info');
}

/**
 * Allinea ai territori di riferimento
 * @param {Function} displayImage - Callback per visualizzazione
 * @param {Function} updateRegionsList - Callback per lista regioni
 */
export async function alignToTerritories(displayImage, updateRegionsList) {
    if (!state.sessionId || state.regions.length === 0) {
        toast('Nessuna regione da allineare', 'warning');
        return;
    }
    
    showLoading('Allineamento ai confini reali...');
    
    try {
        const bounds = getBounds();
        if (!validateBounds(bounds)) {
            toast('Bounds non validi. Controlla nord/sud/est/ovest.', 'error');
            return;
        }

        const requestBody = {
            session_id: state.sessionId,
            bounds: bounds,
            snap_strength: parseFloat(el.snapStrength.value)
        };

        if (!validateCvAutoConfiguration()) {
            return;
        }
        const georeferencing = getGeoreferencingPayload();
        if (georeferencing) {
            requestBody.georeferencing = georeferencing;
        }
        
        if (state.referenceGeojson) {
            requestBody.reference_geojson = state.referenceGeojson;
        }
        
        const data = await api.alignTerritories(requestBody);
        
        if (data.success) {
            state.regions = data.regions;
            if (updateRegionsList) updateRegionsList();
            
            if (data.visualization && displayImage) {
                displayImage('data:image/png;base64,' + data.visualization);
            }
            
            if (data.aligned_geojson) {
                state.geojsonData = data.aligned_geojson;
                const georefMeta = data.aligned_geojson?.properties?.georeferencing;
                if (georeferencing && georefMeta?.fallback_from === 'cv_auto') {
                    toast(
                        `cv_auto fallback su legacy (${georefMeta.fallback_reason || 'motivo non disponibile'})`,
                        'warning',
                    );
                } else if (georeferencing && georefMeta?.mode === 'cv_auto') {
                    toast(`cv_auto applicato (confidence ${georefMeta.cv_confidence})`, 'success');
                }
                if (georefMeta?.projection_warning) {
                    toast(georefMeta.projection_warning, 'warning');
                }
                updateCvQualityFromMetadata(georefMeta, Boolean(georeferencing));
            }
            
            toast(data.message || 'Allineamento completato!', 'success');
            
            // Passa automaticamente allo step Export
            updateStep(4, state);
        } else {
            toast('Allineamento non riuscito', 'warning');
        }
        
    } catch (err) {
        toast('Errore: ' + err.message, 'error');
    } finally {
        hideLoading();
    }
}
