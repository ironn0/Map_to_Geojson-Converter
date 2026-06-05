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

function imageAspectRatio() {
    if (!state.imageWidth || !state.imageHeight) return 1;
    return state.imageWidth / state.imageHeight;
}

function aspectBoundsInside(baseBounds) {
    const zoom = state.georefMap.getZoom();
    const nw = state.georefMap.project(baseBounds.getNorthWest(), zoom);
    const se = state.georefMap.project(baseBounds.getSouthEast(), zoom);
    const center = state.georefMap.project(baseBounds.getCenter(), zoom);
    const baseWidth = Math.abs(se.x - nw.x);
    const baseHeight = Math.abs(se.y - nw.y);
    const aspect = imageAspectRatio();

    let width = baseWidth;
    let height = width / aspect;
    if (height > baseHeight) {
        height = baseHeight;
        width = height * aspect;
    }

    const nextNw = L.point(center.x - width / 2, center.y - height / 2);
    const nextSe = L.point(center.x + width / 2, center.y + height / 2);
    return L.latLngBounds(
        state.georefMap.unproject(nextSe, zoom),
        state.georefMap.unproject(nextNw, zoom)
    );
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
    
    const presetBounds = L.latLngBounds([b.south, b.west], [b.north, b.east]);
    const bounds = aspectBoundsInside(presetBounds);
    state.imageOverlay = L.imageOverlay('data:image/png;base64,' + state.imageBase64, bounds, { 
        opacity: 0.7, 
        interactive: true,
        className: 'georef-image-overlay'
    }).addTo(state.georefMap);
    state.overlayBounds = bounds;
    
    createCornerMarkers();
    state.imageOverlay.once('load', setupImageDragging);
    setupImageDragging();
    
    state.georefMap.fitBounds(presetBounds.pad(0.1));
}

function setupImageDragging() {
    const img = state.imageOverlay?.getElement();
    if (!img || img.dataset.dragBound === 'true') return;

    img.dataset.dragBound = 'true';
    img.style.cursor = 'move';
    L.DomEvent.disableClickPropagation(img);
    L.DomEvent.disableScrollPropagation(img);

    let dragging = false;
    let startLatLng = null;
    let startBounds = null;

    const finishDrag = () => {
        if (!dragging) return;
        dragging = false;
        startLatLng = null;
        startBounds = null;
        state.georefMap.dragging.enable();
    };

    img.addEventListener('mousedown', e => {
        if (e.button !== 0) return;
        dragging = true;
        startLatLng = state.georefMap.mouseEventToLatLng(e);
        startBounds = L.latLngBounds(state.overlayBounds.getSouthWest(), state.overlayBounds.getNorthEast());
        state.georefMap.dragging.disable();
        L.DomEvent.preventDefault(e);
        L.DomEvent.stopPropagation(e);
    });

    state.georefMap.on('mousemove', e => {
        if (!dragging || !startLatLng || !startBounds) return;
        const dLat = e.latlng.lat - startLatLng.lat;
        const dLng = e.latlng.lng - startLatLng.lng;
        state.overlayBounds = L.latLngBounds(
            [startBounds.getSouth() + dLat, startBounds.getWest() + dLng],
            [startBounds.getNorth() + dLat, startBounds.getEast() + dLng]
        );
        state.imageOverlay.setBounds(state.overlayBounds);
        updateCornerMarkers();
    });

    state.georefMap.on('mouseup', finishDrag);
    state.georefMap.on('mouseout', finishDrag);
}

/**
 * Crea i marker agli angoli per il ridimensionamento
 */
function createCornerMarkers() {
    cornerMarkers.forEach(m => m.remove());
    cornerMarkers = [];
    
    const b = state.overlayBounds;
    const handles = [
        { pos: 'nw', latlng: [b.getNorth(), b.getWest()], cursor: 'nw-resize' },
        { pos: 'n', latlng: [b.getNorth(), (b.getWest() + b.getEast()) / 2], cursor: 'ns-resize' },
        { pos: 'ne', latlng: [b.getNorth(), b.getEast()], cursor: 'ne-resize' },
        { pos: 'e', latlng: [(b.getNorth() + b.getSouth()) / 2, b.getEast()], cursor: 'ew-resize' },
        { pos: 'se', latlng: [b.getSouth(), b.getEast()], cursor: 'se-resize' },
        { pos: 's', latlng: [b.getSouth(), (b.getWest() + b.getEast()) / 2], cursor: 'ns-resize' },
        { pos: 'sw', latlng: [b.getSouth(), b.getWest()], cursor: 'sw-resize' },
        { pos: 'w', latlng: [(b.getNorth() + b.getSouth()) / 2, b.getWest()], cursor: 'ew-resize' }
    ];
    
    handles.forEach(handle => {
        const horizontal = ['n', 's'].includes(handle.pos);
        const vertical = ['e', 'w'].includes(handle.pos);
        const iconSize = horizontal ? [28, 20] : vertical ? [20, 28] : [20, 20];
        const iconAnchor = horizontal ? [14, 10] : vertical ? [10, 14] : [10, 10];
        const icon = L.divIcon({
            className: 'corner-marker',
            html: `<div class="corner-handle handle-${handle.pos}" style="cursor:${handle.cursor}"></div>`,
            iconSize,
            iconAnchor
        });
        
        const marker = L.marker(handle.latlng, { 
            icon, 
            draggable: true,
            autoPan: false
        }).addTo(state.georefMap);
        
        marker.cornerPos = handle.pos;
        marker.on('drag', e => handleResizeDrag(handle.pos, e.latlng));
        marker.on('dragend', () => updateCornerMarkers());
        
        cornerMarkers.push(marker);
    });
}

/**
 * Gestisce il trascinamento degli angoli
 */
function handleResizeDrag(pos, latlng) {
    if (['n', 'e', 's', 'w'].includes(pos)) {
        handleSideDrag(pos, latlng);
        return;
    }

    const zoom = state.georefMap.getZoom();
    const fixedLatLng = getCornerPosition(oppositeCorner(pos));
    const fixed = state.georefMap.project(fixedLatLng, zoom);
    const dragged = state.georefMap.project(latlng, zoom);
    const signs = cornerSigns(pos);
    const aspect = imageAspectRatio();
    const lockAspect = el.georefLockAspect?.checked !== false;

    let width = Math.max(24, Math.abs(dragged.x - fixed.x));
    let height = Math.max(24, Math.abs(dragged.y - fixed.y));

    if (lockAspect) {
        if (width / height > aspect) {
            width = height * aspect;
        } else {
            height = width / aspect;
        }
    }

    const adjusted = L.point(
        fixed.x + signs.x * width,
        fixed.y + signs.y * height
    );
    const west = Math.min(fixed.x, adjusted.x);
    const east = Math.max(fixed.x, adjusted.x);
    const north = Math.min(fixed.y, adjusted.y);
    const south = Math.max(fixed.y, adjusted.y);

    state.overlayBounds = L.latLngBounds(
        state.georefMap.unproject(L.point(west, south), zoom),
        state.georefMap.unproject(L.point(east, north), zoom)
    );
    state.imageOverlay.setBounds(state.overlayBounds);
    updateCornerMarkers();
}

function handleSideDrag(pos, latlng) {
    const b = state.overlayBounds;
    const minSpan = 0.01;
    let north = b.getNorth();
    let south = b.getSouth();
    let east = b.getEast();
    let west = b.getWest();

    switch(pos) {
        case 'n':
            north = Math.max(latlng.lat, south + minSpan);
            break;
        case 's':
            south = Math.min(latlng.lat, north - minSpan);
            break;
        case 'e':
            east = Math.max(latlng.lng, west + minSpan);
            break;
        case 'w':
            west = Math.min(latlng.lng, east - minSpan);
            break;
    }

    state.overlayBounds = L.latLngBounds([south, west], [north, east]);
    state.imageOverlay.setBounds(state.overlayBounds);
    updateCornerMarkers();
}

function oppositeCorner(pos) {
    return { nw: 'se', ne: 'sw', se: 'nw', sw: 'ne' }[pos];
}

function cornerSigns(pos) {
    return {
        nw: { x: -1, y: -1 },
        ne: { x: 1, y: -1 },
        se: { x: 1, y: 1 },
        sw: { x: -1, y: 1 }
    }[pos];
}

function getCornerPosition(pos) {
    const b = state.overlayBounds;
    const centerLat = (b.getNorth() + b.getSouth()) / 2;
    const centerLng = (b.getWest() + b.getEast()) / 2;
    switch(pos) {
        case 'nw': return [b.getNorth(), b.getWest()];
        case 'n': return [b.getNorth(), centerLng];
        case 'ne': return [b.getNorth(), b.getEast()];
        case 'e': return [centerLat, b.getEast()];
        case 'se': return [b.getSouth(), b.getEast()];
        case 's': return [b.getSouth(), centerLng];
        case 'sw': return [b.getSouth(), b.getWest()];
        case 'w': return [centerLat, b.getWest()];
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
    const rotation = parseFloat(el.georefRotation.value);
    
    el.georefOpacityValue.textContent = Math.round(opacity * 100) + '%';
    el.georefRotationValue.textContent = rotation + '°';
    
    state.imageOverlay.setOpacity(opacity);
    
    const img = state.imageOverlay.getElement();
    if (img) { 
        img.style.transformOrigin = 'center'; 
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
    
    const b = state.imageOverlay.getBounds();
    el.boundNorth.value = b.getNorth().toFixed(4);
    el.boundSouth.value = b.getSouth().toFixed(4);
    el.boundEast.value = b.getEast().toFixed(4);
    el.boundWest.value = b.getWest().toFixed(4);
    el.presetSelect.value = 'custom';
    
    closeGeorefModal();
    toast('Coordinate geografiche applicate!', 'success');
    
    // Passa automaticamente allo step Export
    updateStep(4, state);
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
export function clearReference() {
    state.referenceGeojson = null;
    state.referenceName = null;
    el.referenceInfo.classList.add('hidden');
    toast('Riferimento rimosso', 'info');
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
        const requestBody = {
            session_id: state.sessionId,
            bounds: getBounds(),
            snap_strength: parseFloat(el.snapStrength.value),
            regions: state.regions.map((region, idx) => ({
                id: region.id ?? idx,
                name: region.name || `Regione ${idx + 1}`,
                color: region.color || '#3b82f6',
                type: region.clientSide ? 'drawn-polygon' : 'area',
                points: region.points || []
            }))
        };
        
        if (state.referenceGeojson) {
            requestBody.reference_geojson = state.referenceGeojson;
        }
        
        const data = await api.alignTerritories(requestBody);
        
        if (data.success) {
            state.regions = data.regions;
            if (updateRegionsList) updateRegionsList();
            
            if (displayImage) {
                displayImage(state.imageBase64);
            }
            
            if (data.aligned_geojson) {
                state.geojsonData = data.aligned_geojson;
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
