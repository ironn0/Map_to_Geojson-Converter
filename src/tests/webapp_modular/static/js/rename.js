/**
 * 📝 Rename Module
 * Gestione rinomina elementi
 * 
 * Author: Map to GeoJSON Converter Project
 */

import { state } from './state.js';
import { el } from './dom.js';
import { toast, updateSelectionLabel } from './ui.js';

/**
 * Apre il modal di rinomina
 */
export function openRenameModal() {
    if (state.selectedRegionId === null && state.selectedPointId === null) {
        toast('Seleziona prima un elemento', 'warning');
        return;
    }
    
    let currentName = '';
    if (state.selectedRegionId !== null && state.regions[state.selectedRegionId]) {
        currentName = state.regions[state.selectedRegionId].name;
    } else if (state.selectedPointId !== null && state.points[state.selectedPointId]) {
        currentName = state.points[state.selectedPointId].name;
    }
    
    el.renameInput.value = currentName;
    el.renameModal.classList.add('visible');
    setTimeout(() => el.renameInput.focus(), 100);
}

/**
 * Chiude il modal di rinomina
 */
export function closeRenameModal() {
    el.renameModal.classList.remove('visible');
}

/**
 * Salva il nuovo nome
 * @param {Function} renderPolygons - Callback per rendering
 */
export function saveRename(renderPolygons) {
    const newName = el.renameInput.value.trim();
    if (!newName) {
        toast('Inserisci un nome valido', 'warning');
        return;
    }
    
    if (state.selectedRegionId !== null && state.regions[state.selectedRegionId]) {
        state.regions[state.selectedRegionId].name = newName;
        toast(`Territorio rinominato: ${newName}`, 'success');
    } else if (state.selectedPointId !== null && state.points[state.selectedPointId]) {
        state.points[state.selectedPointId].name = newName;
        toast(`Punto rinominato: ${newName}`, 'success');
    }
    
    closeRenameModal();
    updateSelectionLabel(state);
    if (renderPolygons) renderPolygons();
}
