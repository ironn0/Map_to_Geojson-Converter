/**
 * 🎨 UI Module
 * Funzioni per l'interfaccia utente (toast, loading, modals)
 * 
 * Author: Map to GeoJSON Converter Project
 */

import { el } from './dom.js';

/**
 * Mostra overlay di caricamento
 * @param {string} text - Testo da mostrare
 */
export function showLoading(text = 'Elaborazione...') {
    el.loadingText.textContent = text;
    el.progressFill.style.width = '0%';
    el.loadingOverlay.classList.add('visible');
    
    // Animate progress bar
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        el.progressFill.style.width = progress + '%';
    }, 200);
    el.loadingOverlay.dataset.interval = interval;
}

/**
 * Nasconde overlay di caricamento
 */
export function hideLoading() {
    el.progressFill.style.width = '100%';
    clearInterval(el.loadingOverlay.dataset.interval);
    setTimeout(() => {
        el.loadingOverlay.classList.remove('visible');
    }, 150);
}

/**
 * Mostra un toast notification
 * @param {string} message - Messaggio da mostrare
 * @param {string} type - Tipo: 'success', 'error', 'warning', 'info'
 */
export function toast(message, type = 'info') {
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    const icons = { success: '✓', error: '✕', warning: '!', info: 'i' };
    t.innerHTML = `<span style="font-weight:600;font-size:14px;">${icons[type]}</span><span>${message}</span>`;
    el.toastContainer.appendChild(t);
    
    setTimeout(() => { 
        t.style.animation = 'toastIn 0.3s ease reverse'; 
        setTimeout(() => t.remove(), 300); 
    }, 4000);
}

/**
 * Aggiorna lo step corrente
 * @param {number} stepNum - Numero step
 * @param {Object} state - Stato applicazione
 */
export function updateStep(stepNum, state) {
    state.currentStep = stepNum;
    
    // Update step indicators
    el.steps.forEach(step => {
        const num = parseInt(step.dataset.step);
        step.classList.remove('active', 'completed');
        if (num === stepNum) step.classList.add('active');
        else if (num < stepNum && canNavigateToStep(num + 1, state)) step.classList.add('completed');
    });
    
    // Show/hide panels
    el.panelUpload.classList.toggle('hidden', stepNum !== 1);
    el.panelSegment.classList.toggle('hidden', stepNum !== 2);
    el.panelGeoref.classList.toggle('hidden', stepNum !== 3);
    el.panelExport.classList.toggle('hidden', stepNum !== 4);
    
    // Update export stats
    if (stepNum === 4) {
        updateExportStats(state);
    }
    document.dispatchEvent(new CustomEvent('wizard:step-changed', { detail: { step: stepNum } }));
}

/**
 * Verifica se si può navigare a uno step
 * @param {number} stepNum - Numero step
 * @param {Object} state - Stato applicazione
 * @returns {boolean}
 */
export function canNavigateToStep(stepNum, state) {
    if (stepNum === 1) return true;
    if (stepNum === 2) return !!state.sessionId;
    if (stepNum === 3) return state.regions.length > 0;
    if (stepNum === 4) return state.regions.length > 0 || !!state.detectedCircle;
    return false;
}

/**
 * Aggiorna statistiche export
 * @param {Object} state - Stato applicazione
 */
export function updateExportStats(state) {
    el.statRegions.textContent = state.regions.length;
    if (el.statPoints) el.statPoints.textContent = state.points.length;
    const totalVertices = state.regions.reduce((sum, r) => sum + r.points.length, 0);
    el.statVertices.textContent = totalVertices;
}

/**
 * Aggiorna label selezione
 * @param {Object} state - Stato applicazione
 */
export function updateSelectionLabel(state) {
    if (!el.selectionLabel) return;
    
    if (state.selectedPointId !== null && state.points[state.selectedPointId]) {
        const p = state.points[state.selectedPointId];
        el.selectionLabel.textContent = `Punto: ${p.name}`;
        el.selectionLabel.classList.add('has-selection');
    } else if (state.selectedRegionId !== null && state.regions[state.selectedRegionId]) {
        const r = state.regions[state.selectedRegionId];
        el.selectionLabel.textContent = `${r.name} (${r.points.length} pt)`;
        el.selectionLabel.classList.add('has-selection');
    } else {
        el.selectionLabel.textContent = 'Clicca su un\'area';
        el.selectionLabel.classList.remove('has-selection');
    }
}

/**
 * Mostra menu contestuale
 * @param {MouseEvent} e - Evento mouse
 */
export function showContextMenu(e) {
    if (!el.contextMenu) return;
    
    e.preventDefault();
    
    el.contextMenu.style.left = e.clientX + 'px';
    el.contextMenu.style.top = e.clientY + 'px';
    el.contextMenu.classList.add('show');
    
    // Ensure menu stays within viewport
    const rect = el.contextMenu.getBoundingClientRect();
    if (rect.right > window.innerWidth) {
        el.contextMenu.style.left = (e.clientX - rect.width) + 'px';
    }
    if (rect.bottom > window.innerHeight) {
        el.contextMenu.style.top = (e.clientY - rect.height) + 'px';
    }
}

/**
 * Nasconde menu contestuale
 */
export function hideContextMenu() {
    if (el.contextMenu) {
        el.contextMenu.classList.remove('show');
    }
}
