/**
 * 📦 Export Module
 * Gestione esportazione GeoJSON
 * 
 * Author: Map to GeoJSON Converter Project
 */

import { state } from './state.js';
import { el } from './dom.js';
import { toast, showLoading, hideLoading } from './ui.js';
import { getBounds } from './georef.js';
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
        const geojson = await api.exportGeoJSON({
            session_id: state.sessionId,
            bounds: getBounds(),
            regions: state.regions.map((region, idx) => ({
                id: region.id ?? idx,
                name: region.name || `Regione ${idx + 1}`,
                type: region.clientSide ? 'drawn-polygon' : 'area',
                area: region.area ?? null,
                color: region.color || '#3b82f6',
                points: region.points || []
            })),
            points: state.points.map((point, idx) => ({
                id: point.id ?? idx,
                name: point.name || `Punto ${idx + 1}`,
                x: point.x,
                y: point.y
            }))
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
    const geojson = await generateGeoJSON();
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
