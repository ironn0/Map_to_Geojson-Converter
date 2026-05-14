/**
 * 🌐 API Module
 * Gestione chiamate API al backend
 * 
 * Author: Map to GeoJSON Converter Project
 */

/**
 * Esegue una chiamata API
 * @param {string} endpoint - L'endpoint API (es. '/upload')
 * @param {Object} options - Opzioni fetch
 * @returns {Promise<Object>} - Risposta JSON
 */
export async function api(endpoint, options = {}) {
    const res = await fetch(`/api${endpoint}`, { 
        headers: { 'Content-Type': 'application/json' }, 
        ...options 
    });
    if (!res.ok) {
        const error = await parseErrorResponse(res);
        throw new Error(error);
    }
    return res.json();
}

async function parseErrorResponse(response) {
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
        const payload = await response.json();
        return payload.detail || payload.message || `Errore API (${response.status})`;
    }
    const text = await response.text();
    return text?.trim() || `Errore API (${response.status})`;
}

/**
 * Carica i preset geografici
 * @returns {Promise<Object>} - Preset disponibili
 */
export async function loadPresets() {
    try {
        return await api('/presets');
    } catch (e) {
        console.error('Failed to load presets:', e);
        return {};
    }
}

/**
 * Carica un'immagine
 * @param {File} file - File immagine
 * @returns {Promise<Object>} - Dati sessione
 */
export async function uploadImage(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/upload', { 
        method: 'POST', 
        body: formData 
    });
    
    if (!response.ok) {
        throw new Error(await parseErrorResponse(response));
    }
    
    return response.json();
}

/**
 * Esegue la segmentazione
 * @param {Object} params - Parametri segmentazione
 * @returns {Promise<Object>} - Risultati segmentazione
 */
export async function runSegmentation(params) {
    return api('/segment', {
        method: 'POST',
        body: JSON.stringify(params)
    });
}

/**
 * Segmenta da un punto
 * @param {Object} params - session_id, x, y
 * @returns {Promise<Object>} - Risultato
 */
export async function segmentAtPoint(params) {
    return api('/segment-point', {
        method: 'POST',
        body: JSON.stringify(params)
    });
}

/**
 * Elimina una regione
 * @param {number} regionId - ID regione
 * @param {string} sessionId - ID sessione
 * @returns {Promise<Object>} - Risultato
 */
export async function deleteRegion(regionId, sessionId) {
    return api(`/delete-region/${regionId}?session_id=${sessionId}`, { 
        method: 'POST' 
    });
}

/**
 * Aggiorna una regione
 * @param {Object} params - Dati aggiornamento
 * @returns {Promise<Object>} - Risultato
 */
export async function updateRegion(params) {
    return api('/update-region', {
        method: 'POST',
        body: JSON.stringify(params)
    });
}

/**
 * Esporta in GeoJSON
 * @param {Object} params - Parametri export
 * @returns {Promise<Object>} - GeoJSON
 */
export async function exportGeoJSON(params) {
    return api('/export', {
        method: 'POST',
        body: JSON.stringify(params)
    });
}

/**
 * Allinea ai confini
 * @param {Object} params - Parametri allineamento
 * @returns {Promise<Object>} - Risultato
 */
export async function alignTerritories(params) {
    return api('/align', {
        method: 'POST',
        body: JSON.stringify(params)
    });
}

/**
 * Carica GeoJSON di riferimento
 * @param {File} file - File GeoJSON
 * @returns {Promise<Object>} - Risultato
 */
export async function uploadReferenceGeoJSON(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/upload-reference', { 
        method: 'POST', 
        body: formData 
    });
    
    if (!response.ok) {
        throw new Error(await parseErrorResponse(response));
    }
    const data = await response.json();
    return data;
}

/**
 * Elimina una sessione
 * @param {string} sessionId - ID sessione
 * @returns {Promise<Object>} - Risultato
 */
export async function deleteSession(sessionId) {
    return api(`/session/${sessionId}`, { method: 'DELETE' });
}

/**
 * Crea una nuova regione lato backend
 * @param {Object} params - session_id, points, name?, color?
 * @returns {Promise<Object>}
 */
export async function addRegion(params) {
    return api('/add-region', {
        method: 'POST',
        body: JSON.stringify(params),
    });
}
