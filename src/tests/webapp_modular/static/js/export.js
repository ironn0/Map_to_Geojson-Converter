/**
 * 📦 Export Module
 * Gestione esportazione GeoJSON
 * 
 * Author: Map to GeoJSON Converter Project
 */

import { state } from './state.js';
import { el } from './dom.js';
import { toast, showLoading, hideLoading } from './ui.js';
import {
    getBounds,
    validateBounds,
    getGeoreferencingPayload,
    validateCvAutoConfiguration,
    applyCvQualityFromMetadata,
} from './georef.js';
import * as api from './api.js';

/**
 * Genera il GeoJSON dalle regioni
 * @returns {Promise<Object|null>}
 */
export async function generateGeoJSON() {
    if (!state.sessionId) {
        toast('Carica prima un\'immagine', 'warning');
        return null;
    }
    if (state.regions.length === 0 && state.points.length === 0) {
        toast('Nessuna regione o punto da esportare. Esegui prima la segmentazione!', 'warning');
        return null;
    }
    
    try {
        let geojson = {
            type: 'FeatureCollection',
            properties: {
                source: 'Map to GeoJSON Converter',
                bounds: getBounds()
            },
            features: []
        };
        
        const bounds = getBounds();
        if (!validateBounds(bounds)) {
            toast('Bounds geografici non validi. Correggi i campi prima dell\'export.', 'error');
            return null;
        }

        const backendRegions = state.regions.filter(r => !r.clientSide);
        const clientRegions = state.regions.filter(r => r.clientSide);
        
        // Get backend regions if any
        if (backendRegions.length > 0) {
            if (!validateCvAutoConfiguration()) {
                return null;
            }
            const georeferencing = getGeoreferencingPayload();
            const backendGeojson = await api.exportGeoJSON({ 
                session_id: state.sessionId, 
                bounds: bounds,
                georeferencing: georeferencing || undefined
            });
            geojson.features = backendGeojson.features || [];
            if (georeferencing) {
                const georefMeta = backendGeojson?.properties?.georeferencing;
                if (georefMeta?.fallback_from === 'cv_auto') {
                    toast(
                        `cv_auto fallback su legacy (${georefMeta.fallback_reason || 'motivo non disponibile'})`,
                        'warning',
                    );
                } else if (georefMeta?.mode === 'cv_auto') {
                    toast(`cv_auto applicato (confidence ${georefMeta.cv_confidence})`, 'success');
                }
                if (georefMeta?.projection_warning) {
                    toast(georefMeta.projection_warning, 'warning');
                }
                applyCvQualityFromMetadata(georefMeta, Boolean(georeferencing));
            }
        }
        
        // Add client-side drawn regions
        clientRegions.forEach((region, idx) => {
            const coords = region.points.map(p => {
                const lng = bounds.west + (p[0] / state.imageWidth) * (bounds.east - bounds.west);
                const lat = bounds.north - (p[1] / state.imageHeight) * (bounds.north - bounds.south);
                return [lng, lat];
            });
            // Close the polygon
            if (coords.length > 0) {
                coords.push([...coords[0]]);
            }
            
            geojson.features.push({
                type: 'Feature',
                properties: {
                    name: region.name,
                    type: 'drawn-polygon',
                    color: region.color
                },
                geometry: {
                    type: 'Polygon',
                    coordinates: [coords]
                }
            });
        });
        
        // Add client-side points
        state.points.forEach(point => {
            const lng = bounds.west + (point.x / state.imageWidth) * (bounds.east - bounds.west);
            const lat = bounds.north - (point.y / state.imageHeight) * (bounds.north - bounds.south);
            
            geojson.features.push({
                type: 'Feature',
                properties: {
                    name: point.name,
                    type: 'point'
                },
                geometry: {
                    type: 'Point',
                    coordinates: [lng, lat]
                }
            });
        });
        
        state.geojsonData = geojson;
        return state.geojsonData;
    } catch (e) {
        toast('Errore nella generazione: ' + e.message, 'error');
        return null;
    }
}

/**
 * Esporta e scarica GeoJSON
 */
export async function exportAndDownload() {
    showLoading('Generazione GeoJSON...');
    const geojson = await generateGeoJSON();
    hideLoading();
    if (geojson) downloadGeoJSON();
}

/**
 * Anteprima GeoJSON
 */
export async function previewGeoJSON() {
    showLoading('Generazione anteprima...');
    const geojson = await generateGeoJSON();
    hideLoading();
    if (geojson) {
        el.geojsonPreview.textContent = JSON.stringify(geojson, null, 2);
        el.previewModal.classList.add('visible');
    }
}

/**
 * Copia GeoJSON negli appunti
 */
export async function copyGeoJSON() {
    const geojson = state.geojsonData || await generateGeoJSON();
    if (geojson) { 
        navigator.clipboard.writeText(JSON.stringify(geojson, null, 2)); 
        toast('GeoJSON copiato negli appunti!', 'success'); 
    }
}

/**
 * Scarica il file GeoJSON
 */
export function downloadGeoJSON() {
    if (!state.geojsonData) return;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(state.geojsonData, null, 2)], { type: 'application/json' }));
    a.download = 'map_regions.geojson';
    a.click();
    toast('GeoJSON scaricato!', 'success');
}
