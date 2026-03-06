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
    
    const bounds = L.latLngBounds([b.south, b.west], [b.north, b.east]);
    state.imageOverlay = L.imageOverlay('data:image/png;base64,' + state.imageBase64, bounds, { 
        opacity: 0.7, 
        interactive: true 
    }).addTo(state.georefMap);
    state.overlayBounds = bounds;
    
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
            updateCornerMarkers();
        });
        
        state.georefMap.on('mouseup', () => dragging = false);
    }
    
    state.georefMap.fitBounds(bounds.pad(0.1));
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
    
    if (north > south + 0.01 && east > west + 0.01) {
        state.overlayBounds = L.latLngBounds([south, west], [north, east]);
        state.imageOverlay.setBounds(state.overlayBounds);
        
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
            snap_strength: parseFloat(el.snapStrength.value)
        };
        
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
