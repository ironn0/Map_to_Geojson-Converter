/**
 * 🎨 Drawing Module
 * Gestione disegno manuale di poligoni e punti
 * 
 * Author: Map to GeoJSON Converter Project
 */

import { state } from './state.js';
import { el } from './dom.js';
import { toast, updateSelectionLabel } from './ui.js';

/**
 * Inizia disegno poligono
 * @param {Function} renderPolygons - Callback per rendering
 */
export function startDrawPolygon(renderPolygons) {
    if (!state.sessionId) {
        toast('Carica prima un\'immagine', 'warning');
        return;
    }
    
    state.isDrawing = true;
    state.drawingPoints = [];
    state.currentTool = 'draw-polygon';
    state.selectedRegionId = null;
    state.selectedPointId = null;
    
    // Show draw controls
    if (el.drawTools) el.drawTools.classList.remove('hidden');
    if (el.vertexTools) el.vertexTools.classList.add('hidden');
    
    // Highlight draw button
    el.toolDrawPolygon?.classList.add('active');
    el.toolDrawPoint?.classList.remove('active');
    
    toast('Clicca sulla mappa per disegnare un poligono. Premi "Completa" quando hai finito.', 'info');
    if (renderPolygons) renderPolygons();
}

/**
 * Inizia disegno punto
 */
export function startDrawPoint() {
    if (!state.sessionId) {
        toast('Carica prima un\'immagine', 'warning');
        return;
    }
    
    state.currentTool = 'draw-point';
    state.selectedRegionId = null;
    state.selectedPointId = null;
    
    el.toolDrawPoint?.classList.add('active');
    el.toolDrawPolygon?.classList.remove('active');
    
    toast('Clicca sulla mappa per aggiungere un punto', 'info');
}

/**
 * Gestisce click durante il disegno
 * @param {MouseEvent} e - Evento mouse
 * @param {Function} renderPolygons - Callback per rendering
 * @param {Function} openRenameModal - Callback per rinomina
 */
export function handleDrawClick(e, renderPolygons, openRenameModal) {
    const rect = el.canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / state.canvasScale;
    const y = (e.clientY - rect.top) / state.canvasScale;
    
    if (state.currentTool === 'draw-polygon' && state.isDrawing) {
        state.drawingPoints.push([x, y]);
        if (renderPolygons) renderPolygons();
        toast(`Punto ${state.drawingPoints.length} aggiunto`, 'success');
    } else if (state.currentTool === 'draw-point') {
        addPoint(x, y, renderPolygons, openRenameModal);
    }
}

/**
 * Aggiunge un punto alla mappa
 */
function addPoint(x, y, renderPolygons, openRenameModal) {
    const pointId = state.points.length;
    const newPoint = {
        id: pointId,
        name: `Punto ${pointId + 1}`,
        x: x,
        y: y
    };
    state.points.push(newPoint);
    state.selectedPointId = pointId;
    state.currentTool = 'select';
    
    el.toolDrawPoint?.classList.remove('active');
    
    if (renderPolygons) renderPolygons();
    updateSelectionLabel(state);
    
    // Open rename modal for the new point
    if (openRenameModal) {
        setTimeout(() => openRenameModal(), 100);
    }
    toast('Punto aggiunto! Assegna un nome.', 'success');
}

/**
 * Completa il disegno del poligono
 * @param {Function} renderPolygons - Callback per rendering
 * @param {Function} openRenameModal - Callback per rinomina
 */
export function finishDrawing(renderPolygons, openRenameModal) {
    if (!state.isDrawing || state.drawingPoints.length < 3) {
        toast('Servono almeno 3 punti per creare un poligono', 'warning');
        return;
    }
    
    // Create new region (client-side)
    const newRegion = {
        name: `Territorio ${state.regions.length + 1}`,
        points: state.drawingPoints.map(p => [...p]),
        color: getRandomColor(),
        clientSide: true
    };
    
    state.regions.push(newRegion);
    state.selectedRegionId = state.regions.length - 1;
    
    // Reset drawing state
    state.isDrawing = false;
    state.drawingPoints = [];
    state.currentTool = 'select';
    
    // Hide draw controls
    if (el.drawTools) el.drawTools.classList.add('hidden');
    el.toolDrawPolygon?.classList.remove('active');
    
    if (renderPolygons) renderPolygons();
    updateSelectionLabel(state);
    
    // Open rename modal for the new region
    if (openRenameModal) {
        setTimeout(() => openRenameModal(), 100);
    }
    toast('Territorio creato! Assegna un nome.', 'success');
}

/**
 * Annulla il disegno corrente
 * @param {Function} renderPolygons - Callback per rendering
 */
export function cancelDrawing(renderPolygons) {
    state.isDrawing = false;
    state.drawingPoints = [];
    state.currentTool = 'select';
    
    if (el.drawTools) el.drawTools.classList.add('hidden');
    el.toolDrawPolygon?.classList.remove('active');
    el.toolDrawPoint?.classList.remove('active');
    
    if (renderPolygons) renderPolygons();
    toast('Disegno annullato', 'info');
}

/**
 * Genera un colore casuale
 * @returns {string}
 */
function getRandomColor() {
    const colors = [
        '#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f97316', 
        '#eab308', '#22c55e', '#14b8a6', '#06b6d4', '#3b82f6'
    ];
    return colors[Math.floor(Math.random() * colors.length)];
}
