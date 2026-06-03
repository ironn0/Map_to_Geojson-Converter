/**
 * ✏️ Editor Module
 * Gestione dell'editor poligoni e vertici
 * 
 * Author: Map to GeoJSON Converter Project
 */

import { state, resetEditorState } from './state.js';
import { el } from './dom.js';
import { toast, updateSelectionLabel } from './ui.js';

/**
 * Imposta lo strumento corrente
 * @param {string} tool - Nome strumento
 */
export function setTool(tool) {
    console.log('setTool called with:', tool);
    const prevTool = state.currentTool;
    state.currentTool = tool;
    
    // Update UI - remove active from all tool buttons
    document.querySelectorAll('#editor-toolbar .tool-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Add active to the selected tool
    const activeBtn = document.getElementById('tool-' + tool);
    if (activeBtn) {
        activeBtn.classList.add('active');
    }
    
    // Set cursor on canvas
    if (el.canvasWrapper) {
        el.canvasWrapper.setAttribute('data-tool', tool);
    }
    
    // Show feedback
    if (prevTool !== tool) {
        const toolNames = {
            'select': 'Seleziona - Clicca su una forma per selezionarla',
            'edit': 'Modifica - Doppio click per modificare i vertici',
            'move': 'Sposta - Trascina una forma selezionata',
            'scale': 'Scala - Trascina su/giù per ridimensionare'
        };
        if (toolNames[tool]) {
            toast(toolNames[tool], 'info');
        }
    }
    
}

/**
 * Seleziona una regione
 * @param {number} idx - Indice regione
 * @param {Function} renderPolygons - Callback per rendering
 */
export function selectRegion(idx, renderPolygons) {
    const wasSelected = state.selectedRegionId === idx;
    state.selectedRegionId = idx;
    state.selectedPointId = null;
    state.selectedVertexIndex = null;
    renderPolygons();
    updateSelectionLabel(state);
    
    // Show info about selected region
    if (!wasSelected && state.regions[idx]) {
        const r = state.regions[idx];
        toast(`${r.name} selezionata • ${r.points.length} vertici`, 'info');
    }
}

/**
 * Inizia modifica regione
 * @param {number} idx - Indice regione
 * @param {Function} renderPolygons - Callback per rendering
 */
export function startEditRegion(idx, renderPolygons) {
    if (state.editingRegionId !== null && state.editingRegionId !== idx) {
        exitEditMode(renderPolygons);
    }
    
    state.editingRegionId = idx;
    state.selectedRegionId = idx;
    state.selectedVertexIndex = null;
    state.originalPoints = JSON.parse(JSON.stringify(state.regions[idx].points));
    
    el.polygonEditor.classList.add('active');
    if (el.vertexTools) el.vertexTools.classList.remove('hidden');
    setTool('edit');
    
    if (state.clickMode) { 
        state.clickMode = false; 
        el.clickModeBtn.classList.remove('active'); 
    }
    
    if (renderPolygons) renderPolygons();
    updateSelectionLabel(state);
    toast('Modifica vertici: trascina per spostare, clicca sui punti medi per aggiungere', 'info');
}

/**
 * Esce dalla modalità edit
 * @param {Function} renderPolygons - Callback per rendering
 */
export function exitEditMode(renderPolygons) {
    resetEditorState();
    el.polygonEditor.classList.remove('active');
    if (el.vertexTools) el.vertexTools.classList.add('hidden');
    setTool('select');
    if (renderPolygons) renderPolygons();
}

/**
 * Aggiunge un vertice dopo l'indice specificato
 * @param {number} afterIndex - Indice dopo cui inserire
 * @param {Function} renderPolygons - Callback per rendering
 */
export function addVertexAfter(afterIndex, renderPolygons) {
    if (state.editingRegionId === null) return;
    
    const pts = state.regions[state.editingRegionId].points;
    const next = (afterIndex + 1) % pts.length;
    pts.splice(afterIndex + 1, 0, [
        (pts[afterIndex][0] + pts[next][0]) / 2, 
        (pts[afterIndex][1] + pts[next][1]) / 2
    ]);
    state.selectedVertexIndex = afterIndex + 1;
    
    if (renderPolygons) renderPolygons();
    toast('Vertice aggiunto', 'success');
}

/**
 * Elimina il vertice selezionato
 * @param {Function} renderPolygons - Callback per rendering
 */
export function deleteSelectedVertex(renderPolygons) {
    if (state.editingRegionId === null || state.selectedVertexIndex === null) {
        toast('Seleziona prima un vertice', 'warning');
        return;
    }
    
    const pts = state.regions[state.editingRegionId].points;
    if (pts.length <= 3) { 
        toast('Un poligono deve avere almeno 3 vertici', 'error'); 
        return; 
    }
    
    pts.splice(state.selectedVertexIndex, 1);
    state.selectedVertexIndex = null;
    if (renderPolygons) renderPolygons();
    toast('Vertice eliminato', 'success');
}

/**
 * Salva le modifiche al poligono
 * @param {Function} renderPolygons - Callback per rendering
 * @param {Function} updateRegionsList - Callback per aggiornamento lista
 */
export async function savePolygonEdit(renderPolygons, updateRegionsList) {
    if (state.editingRegionId === null) return;

    exitEditMode(renderPolygons);
    if (updateRegionsList) updateRegionsList();
    toast('Modifiche salvate localmente. Saranno incluse nel GeoJSON.', 'success');
}

/**
 * Annulla le modifiche al poligono
 * @param {Function} renderPolygons - Callback per rendering
 */
export function cancelPolygonEdit(renderPolygons) {
    if (state.editingRegionId !== null && state.originalPoints) {
        state.regions[state.editingRegionId].points = state.originalPoints;
    }
    exitEditMode(renderPolygons);
    toast('Modifiche annullate', 'info');
}

/**
 * Semplifica la forma selezionata
 * @param {Function} renderPolygons - Callback per rendering
 * @param {Function} updateRegionsList - Callback per aggiornamento lista
 */
export function simplifyShape(renderPolygons, updateRegionsList) {
    if (state.selectedRegionId === null) {
        toast('Seleziona prima una forma', 'warning');
        return;
    }
    
    const region = state.regions[state.selectedRegionId];
    if (region.points.length <= 3) {
        toast('La forma ha già il minimo di vertici', 'warning');
        return;
    }
    
    const simplified = simplifyPolygon(region.points, 3);
    if (simplified.length < 3) {
        toast('Non è possibile semplificare ulteriormente', 'warning');
        return;
    }
    
    region.points = simplified;
    if (renderPolygons) renderPolygons();
    if (updateRegionsList) updateRegionsList();
    toast(`Semplificato a ${simplified.length} vertici`, 'success');
}

/**
 * Algoritmo Ramer-Douglas-Peucker per semplificare poligoni
 */
function simplifyPolygon(points, tolerance) {
    if (points.length <= 2) return points;
    
    let maxDist = 0;
    let maxIdx = 0;
    const end = points.length - 1;
    
    for (let i = 1; i < end; i++) {
        const dist = perpendicularDistance(points[i], points[0], points[end]);
        if (dist > maxDist) {
            maxDist = dist;
            maxIdx = i;
        }
    }
    
    if (maxDist > tolerance) {
        const left = simplifyPolygon(points.slice(0, maxIdx + 1), tolerance);
        const right = simplifyPolygon(points.slice(maxIdx), tolerance);
        return left.slice(0, -1).concat(right);
    } else {
        return [points[0], points[end]];
    }
}

function perpendicularDistance(point, lineStart, lineEnd) {
    const dx = lineEnd[0] - lineStart[0];
    const dy = lineEnd[1] - lineStart[1];
    const norm = Math.sqrt(dx * dx + dy * dy);
    
    if (norm === 0) return Math.sqrt(Math.pow(point[0] - lineStart[0], 2) + Math.pow(point[1] - lineStart[1], 2));
    
    return Math.abs((point[0] - lineStart[0]) * dy - (point[1] - lineStart[1]) * dx) / norm;
}

/**
 * Arrotonda la forma selezionata
 * @param {Function} renderPolygons - Callback per rendering
 * @param {Function} updateRegionsList - Callback per aggiornamento lista
 */
export function smoothShape(renderPolygons, updateRegionsList) {
    if (state.selectedRegionId === null) {
        toast('Seleziona prima una forma', 'warning');
        return;
    }
    
    const region = state.regions[state.selectedRegionId];
    const pts = region.points;
    if (pts.length < 3) return;
    
    // Simple smoothing using Laplacian smoothing
    const smoothed = pts.map((p, i) => {
        const prev = pts[(i - 1 + pts.length) % pts.length];
        const next = pts[(i + 1) % pts.length];
        return [
            p[0] * 0.5 + (prev[0] + next[0]) * 0.25,
            p[1] * 0.5 + (prev[1] + next[1]) * 0.25
        ];
    });
    
    region.points = smoothed;
    if (renderPolygons) renderPolygons();
    if (updateRegionsList) updateRegionsList();
    toast('Forma levigata', 'success');
}

/**
 * Duplica la forma selezionata
 * @param {Function} renderPolygons - Callback per rendering
 * @param {Function} updateRegionsList - Callback per aggiornamento lista
 */
export function duplicateShape(renderPolygons, updateRegionsList) {
    if (state.selectedRegionId === null) {
        toast('Seleziona prima una forma', 'warning');
        return;
    }
    
    const original = state.regions[state.selectedRegionId];
    const offset = 20;
    
    const duplicate = {
        ...original,
        id: state.regions.length,
        clientSide: true,
        name: original.name + ' (copia)',
        points: original.points.map(p => [p[0] + offset, p[1] + offset])
    };
    
    state.regions.push(duplicate);
    state.selectedRegionId = state.regions.length - 1;
    if (renderPolygons) renderPolygons();
    if (updateRegionsList) updateRegionsList();
    toast('Forma duplicata', 'success');
}

/**
 * Elimina la forma selezionata
 * @param {Function} deleteRegionCallback - Callback per eliminazione
 */
export function deleteSelectedShape(deleteRegionCallback, renderPolygons, updateRegionsList) {
    if (state.selectedPointId !== null) {
        const idx = state.selectedPointId;
        if (idx >= 0 && idx < state.points.length) {
            state.points.splice(idx, 1);
            state.points.forEach((point, i) => point.id = i);
            state.selectedPointId = null;
            if (renderPolygons) renderPolygons();
            if (updateRegionsList) updateRegionsList();
            toast('Punto eliminato', 'info');
        }
        return;
    }

    if (state.selectedRegionId === null) {
        toast('Seleziona prima una forma', 'warning');
        return;
    }
    
    if (deleteRegionCallback) {
        deleteRegionCallback(state.selectedRegionId);
    }
}

/**
 * Inizia spostamento forma
 * @param {number} regionIdx - Indice regione
 * @param {MouseEvent} startEvent - Evento mouse
 * @param {Function} renderPolygons - Callback per rendering
 */
export function startMoveShape(regionIdx, startEvent, renderPolygons) {
    const region = state.regions[regionIdx];
    const startX = startEvent.clientX;
    const startY = startEvent.clientY;
    const originalPoints = region.points.map(p => [...p]);
    
    const onMove = e => {
        const dx = (e.clientX - startX) / state.canvasScale;
        const dy = (e.clientY - startY) / state.canvasScale;
        
        region.points = originalPoints.map(p => [
            Math.max(0, Math.min(state.imageWidth, p[0] + dx)),
            Math.max(0, Math.min(state.imageHeight, p[1] + dy))
        ]);
        if (renderPolygons) renderPolygons();
    };
    
    const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        toast('Forma spostata', 'success');
    };
    
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
}

/**
 * Inizia ridimensionamento forma
 * @param {number} regionIdx - Indice regione
 * @param {MouseEvent} startEvent - Evento mouse
 * @param {Function} renderPolygons - Callback per rendering
 */
export function startScaleShape(regionIdx, startEvent, renderPolygons) {
    const region = state.regions[regionIdx];
    const pts = region.points;
    
    // Calculate centroid
    const cx = pts.reduce((s, p) => s + p[0], 0) / pts.length;
    const cy = pts.reduce((s, p) => s + p[1], 0) / pts.length;
    
    const startY = startEvent.clientY;
    const originalPoints = pts.map(p => [...p]);
    
    const onMove = e => {
        const deltaY = startY - e.clientY;
        const scale = 1 + deltaY * 0.005;
        
        region.points = originalPoints.map(p => [
            Math.max(0, Math.min(state.imageWidth, cx + (p[0] - cx) * scale)),
            Math.max(0, Math.min(state.imageHeight, cy + (p[1] - cy) * scale))
        ]);
        if (renderPolygons) renderPolygons();
    };
    
    const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        toast('Forma ridimensionata', 'success');
    };
    
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
}
