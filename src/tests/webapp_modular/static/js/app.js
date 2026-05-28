/**
 * 🗺️ Map to GeoJSON - Modular App
 * Entry point principale - coordina tutti i moduli
 * 
 * Author: Map to GeoJSON Converter Project
 */

// ==================== Import Modules ====================
import { state, resetState } from './state.js';
import { el, refreshElements } from './dom.js';
import * as api from './api.js';
import { 
    showLoading, hideLoading, toast, 
    updateStep, canNavigateToStep, updateExportStats,
    updateSelectionLabel, showContextMenu, hideContextMenu
} from './ui.js';
import { CookieManager } from './cookies.js';
import {
    setTool, selectRegion, startEditRegion, exitEditMode,
    addVertexAfter, deleteSelectedVertex, savePolygonEdit, cancelPolygonEdit,
    simplifyShape, smoothShape, duplicateShape, deleteSelectedShape,
    startMoveShape, startScaleShape
} from './editor.js';
import {
    getBounds, handlePresetChange, openGeorefModal, closeGeorefModal,
    updateGeorefOverlay, applyGeoref, handleReferenceUpload, clearReference, alignToTerritories,
    handleCvReferenceImageUpload, syncCvReferenceBoundsFromCurrent, updateCvAutoUiState, resetCvAutoUiState,
    clearCvReference, resetGeorefPosition, fitGeorefView, applyReferenceGeojsonBounds, resetGeorefRotation,
    getGeoreferencingPayload, validateCvAutoConfiguration
} from './georef.js';
import { generateGeoJSON, exportAndDownload, previewGeoJSON, copyGeoJSON, downloadGeoJSON } from './export.js';
import { startDrawPolygon, startDrawPoint, handleDrawClick, finishDrawing, cancelDrawing } from './drawing.js';
import { openRenameModal, closeRenameModal, saveRename } from './rename.js';

const ACCEPTED_IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'jpe', 'jfif', 'webp', 'bmp', 'tif', 'tiff'];

// ==================== Initialize ====================
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🗺️ Map to GeoJSON - Modular Version Loaded');
    
    CookieManager.init();
    setupEventListeners();
    setupKeyboardShortcuts();
    
    state.presets = await api.loadPresets();
    updateCvAutoUiState();
    updateStep(1, state);
    setTool('select');
    renderWizardGuidance();
    renderProjectHistory();
    renderJobStatus();
    await refreshOperationalDashboard();
});

// ==================== Event Listeners ====================
function setupEventListeners() {
    // Sidebar toggle
    el.sidebarToggle?.addEventListener('click', () => {
        el.sidebar.classList.toggle('collapsed');
    });
    
    // Step navigation
    el.steps.forEach(step => {
        step.addEventListener('click', () => {
            const stepNum = parseInt(step.dataset.step);
            if (canNavigateToStep(stepNum, state)) {
                updateStep(stepNum, state);
            }
        });
    });
    
    // Upload area
    el.uploadArea.addEventListener('click', () => el.fileInput.click());
    el.fileInput.addEventListener('change', e => e.target.files[0] && uploadFile(e.target.files[0]));
    
    // Drag & drop
    [el.uploadArea, el.canvasWrapper].forEach(zone => {
        zone.addEventListener('dragover', e => { 
            e.preventDefault(); 
            el.uploadArea.classList.add('dragover');
        });
        zone.addEventListener('dragleave', () => el.uploadArea.classList.remove('dragover'));
        zone.addEventListener('drop', e => {
            e.preventDefault();
            el.uploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (isLikelyImageFile(file)) {
                uploadFile(file);
            } else if (file) {
                toast('File non supportato. Usa PNG, JPG, WebP, BMP o TIFF.', 'error');
            }
        });
    });
    
    // Canvas
    el.canvas.addEventListener('click', handleCanvasClick);
    el.canvas.addEventListener('mousemove', handleCanvasMove);
    
    // Sliders
    el.nColors.addEventListener('input', e => el.nColorsValue.textContent = e.target.value);
    el.minArea.addEventListener('input', e => el.minAreaValue.textContent = e.target.value);
    el.snapStrength.addEventListener('input', e => el.snapStrengthValue.textContent = Math.round(e.target.value * 100) + '%');
    el.cvConfidenceThreshold?.addEventListener('input', e => {
        el.cvConfidenceThresholdValue.textContent = parseFloat(e.target.value).toFixed(2);
    });
    el.cvAutoEnabled?.addEventListener('change', updateCvAutoUiState);
    
    // Actions
    el.segmentBtn.addEventListener('click', runSegmentation);
    el.clickModeBtn.addEventListener('click', toggleClickMode);
    el.georefBtn.addEventListener('click', openGeorefModal);
    el.detectCircleBtn?.addEventListener('click', detectCircle);
    el.previewBtn.addEventListener('click', previewGeoJSON);
    el.copyBtn.addEventListener('click', copyGeoJSON);
    el.exportBtn.addEventListener('click', async () => {
        await exportAndDownload();
        addProjectHistory('Export completato', 'GeoJSON scaricato');
        refreshOperationalDashboard();
    });
    el.clearBtn.addEventListener('click', clearSession);
    el.wizardNextActionBtn?.addEventListener('click', executeNextRecommendedAction);
    el.refreshOpsBtn?.addEventListener('click', () => refreshOperationalDashboard());
    document.addEventListener('wizard:step-changed', () => renderWizardGuidance());
    
    // Presets
    el.presetSelect.addEventListener('change', handlePresetChange);
    
    // Editor toolbar
    el.addVertexBtn.addEventListener('click', () => toast('Clicca sui punti medi per aggiungere vertici', 'info'));
    el.deleteVertexBtn.addEventListener('click', () => deleteSelectedVertex(renderPolygons));
    el.savePolygonBtn.addEventListener('click', () => savePolygonEdit(renderPolygons, updateRegionsList));
    el.cancelEditBtn.addEventListener('click', () => cancelPolygonEdit(renderPolygons));
    
    // Tool buttons
    el.toolSelect?.addEventListener('click', () => setTool('select'));
    el.toolEdit?.addEventListener('click', () => {
        if (state.selectedRegionId !== null) {
            startEditRegion(state.selectedRegionId, renderPolygons);
        } else {
            toast('Seleziona prima un\'area cliccandoci sopra', 'warning');
        }
    });
    el.toolMove?.addEventListener('click', () => {
        if (state.selectedRegionId !== null) {
            setTool('move');
            toast('Trascina l\'area per spostarla', 'info');
        } else {
            toast('Seleziona prima un\'area', 'warning');
        }
    });
    el.toolScale?.addEventListener('click', () => {
        if (state.selectedRegionId !== null) {
            setTool('scale');
            toast('Trascina su/giù sull\'area per ridimensionarla', 'info');
        } else {
            toast('Seleziona prima un\'area', 'warning');
        }
    });
    
    el.simplifyBtn?.addEventListener('click', () => simplifyShape(renderPolygons, updateRegionsList));
    el.smoothBtn?.addEventListener('click', () => smoothShape(renderPolygons, updateRegionsList));
    el.duplicateBtn?.addEventListener('click', () => duplicateShape(renderPolygons, updateRegionsList));
    el.deleteShapeBtn?.addEventListener('click', () => deleteSelectedShape(deleteRegion));
    
    // Context menu
    document.addEventListener('contextmenu', handleContextMenu);
    document.addEventListener('click', () => hideContextMenu());
    
    // Context menu items
    document.getElementById('ctx-edit')?.addEventListener('click', () => { hideContextMenu(); if (state.selectedRegionId !== null) startEditRegion(state.selectedRegionId, renderPolygons); });
    document.getElementById('ctx-move')?.addEventListener('click', () => { hideContextMenu(); setTool('move'); });
    document.getElementById('ctx-duplicate')?.addEventListener('click', () => { hideContextMenu(); duplicateShape(renderPolygons, updateRegionsList); });
    document.getElementById('ctx-simplify')?.addEventListener('click', () => { hideContextMenu(); simplifyShape(renderPolygons, updateRegionsList); });
    document.getElementById('ctx-smooth')?.addEventListener('click', () => { hideContextMenu(); smoothShape(renderPolygons, updateRegionsList); });
    document.getElementById('ctx-delete')?.addEventListener('click', () => { hideContextMenu(); deleteSelectedShape(deleteRegion); });
    document.getElementById('ctx-rename')?.addEventListener('click', () => { hideContextMenu(); openRenameModal(); });
    
    // Draw tools
    el.toolDrawPolygon?.addEventListener('click', () => startDrawPolygon(renderPolygons));
    el.toolDrawPoint?.addEventListener('click', () => startDrawPoint());
    el.finishDrawBtn?.addEventListener('click', () => finishDrawing(renderPolygons, openRenameModal));
    el.cancelDrawBtn?.addEventListener('click', () => cancelDrawing(renderPolygons));
    
    // Rename
    el.renameBtn?.addEventListener('click', () => openRenameModal());
    el.renameModalClose?.addEventListener('click', () => closeRenameModal());
    el.renameCancel?.addEventListener('click', () => closeRenameModal());
    el.renameSave?.addEventListener('click', () => saveRename(renderPolygons));
    el.renameInput?.addEventListener('keydown', e => { if (e.key === 'Enter') saveRename(renderPolygons); });
    el.renameModal?.addEventListener('click', e => { if (e.target === el.renameModal) closeRenameModal(); });
    
    // Preview modal
    el.modalClose.addEventListener('click', () => el.previewModal.classList.remove('visible'));
    el.modalCopy.addEventListener('click', () => { 
        navigator.clipboard.writeText(el.geojsonPreview.textContent); 
        toast('Copiato negli appunti!', 'success'); 
    });
    el.modalDownload.addEventListener('click', downloadGeoJSON);
    el.previewModal.addEventListener('click', e => e.target === el.previewModal && el.previewModal.classList.remove('visible'));
    
    // Georef modal
    el.georefModalClose.addEventListener('click', closeGeorefModal);
    el.georefCancel.addEventListener('click', closeGeorefModal);
    el.georefApply.addEventListener('click', applyGeoref);
    el.georefRotation?.addEventListener('input', updateGeorefOverlay);
    el.georefOpacity.addEventListener('input', updateGeorefOverlay);
    el.georefReset?.addEventListener('click', resetGeorefPosition);
    el.georefResetRotation?.addEventListener('click', resetGeorefRotation);
    el.georefFit?.addEventListener('click', fitGeorefView);
    
    // Alignment controls
    el.loadReferenceBtn.addEventListener('click', () => el.referenceFile.click());
    el.referenceFile.addEventListener('change', handleReferenceUpload);
    el.clearReferenceBtn.addEventListener('click', clearReference);
    el.referenceBoundsBtn?.addEventListener('click', applyReferenceGeojsonBounds);
    el.loadCvReferenceBtn?.addEventListener('click', () => el.cvReferenceFile.click());
    el.cvReferenceFile?.addEventListener('change', handleCvReferenceImageUpload);
    el.clearCvReferenceBtn?.addEventListener('click', () => clearCvReference());
    el.cvRefUseCurrentBoundsBtn?.addEventListener('click', syncCvReferenceBoundsFromCurrent);
    el.alignBtn.addEventListener('click', () => alignToTerritories(displayImage, updateRegionsList));
    
    // Window resize
    window.addEventListener('resize', () => { 
        if (state.imageBase64) displayImage(state.imageBase64); 
    });
}

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', e => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        const key = e.key.toLowerCase();
        
        switch(key) {
            case 'v': setTool('select'); break;
            case 'e': setTool('edit'); break;
            case 'm': setTool('move'); break;
            case 's': if (!e.ctrlKey) setTool('scale'); break;
            case 'delete':
            case 'backspace':
                e.preventDefault();
                if (state.selectedVertexIndex !== null && state.editingRegionId !== null) {
                    deleteSelectedVertex(renderPolygons);
                } else if (state.selectedRegionId !== null) {
                    deleteSelectedShape(deleteRegion);
                }
                break;
            case 'escape':
                if (state.editingRegionId !== null) {
                    cancelPolygonEdit(renderPolygons);
                } else {
                    state.selectedRegionId = null;
                    renderPolygons();
                }
                break;
            case 'd':
                if (e.ctrlKey) { e.preventDefault(); duplicateShape(renderPolygons, updateRegionsList); }
                break;
        }
    });
}

// ==================== File Upload ====================
async function uploadFile(file) {
    showLoading('Caricamento immagine...');
    try {
        const data = await api.uploadImage(file);
        
        state.sessionId = data.session_id;
        state.imageWidth = data.width;
        state.imageHeight = data.height;
        state.regions = [];
        state.imageBase64 = data.image;
        state.detectedCircle = null;
        
        displayImage(data.image);
        el.emptyState.classList.add('hidden');
        el.bottomBar.classList.remove('hidden');
        el.imageInfo.textContent = `${data.filename} • ${data.width}×${data.height}px`;
        
        el.clearBtn.disabled = false;
        updateStep(2, state);
        addProjectHistory('Upload completato', `${data.filename} (${data.width}x${data.height})`);
        updateCircleStatus();
        
        toast('Immagine caricata! Procedi con la segmentazione.', 'success');
    } catch (e) {
        toast('Errore nel caricamento: ' + e.message, 'error');
    } finally {
        hideLoading();
    }
}

function isLikelyImageFile(file) {
    if (!file) return false;
    if (file.type?.startsWith('image/')) return true;
    const parts = (file.name || '').toLowerCase().split('.');
    const ext = parts.length > 1 ? parts.pop() : '';
    return ACCEPTED_IMAGE_EXTENSIONS.includes(ext);
}

function displayImage(base64) {
    const img = new Image();
    img.onload = () => {
        const ctx = el.canvas.getContext('2d');
        const wrapperRect = el.canvasWrapper.getBoundingClientRect();
        const maxW = wrapperRect.width - 60;
        const maxH = wrapperRect.height - 60;
        
        state.canvasScale = Math.min(maxW / img.width, maxH / img.height, 1);
        el.canvas.width = img.width * state.canvasScale;
        el.canvas.height = img.height * state.canvasScale;
        ctx.drawImage(img, 0, 0, el.canvas.width, el.canvas.height);
        
        el.zoomLevel.textContent = Math.round(state.canvasScale * 100) + '%';
        
        requestAnimationFrame(() => {
            if (state.regions.length > 0) renderPolygons();
        });
    };
    img.src = base64.startsWith('data:') ? base64 : 'data:image/png;base64,' + base64;
}

// ==================== Session ====================
async function clearSession() {
    if (state.sessionId) {
        try { await api.deleteSession(state.sessionId); } catch (e) {}
        try { await api.clearDetectedCircle(state.sessionId); } catch (e) {}
    }
    
    resetState();
    exitEditMode(renderPolygons);
    resetCvAutoUiState();
    clearReference(true);
    
    el.canvas.getContext('2d').clearRect(0, 0, el.canvas.width, el.canvas.height);
    el.polygonEditor.innerHTML = '';
    el.emptyState.classList.remove('hidden');
    el.bottomBar.classList.add('hidden');
    el.fileInput.value = '';
    el.clearBtn.disabled = true;
    updateCircleStatus();
    
    updateStep(1, state);
    addProjectHistory('Sessione resettata', 'Hai ricominciato da zero');
    renderJobStatus();
    toast('Sessione terminata', 'info');
}

async function detectCircle() {
    if (!state.sessionId) {
        toast('Carica prima un\'immagine', 'warning');
        return;
    }

    if (!validateCvAutoConfiguration()) {
        return;
    }
    showLoading('Rilevamento cerchio in coda...');
    try {
        const payload = {
            session_id: state.sessionId,
            bounds: getBounds(),
            strict_center_target_m: 5.0,
        };
        const georeferencing = getGeoreferencingPayload();
        if (georeferencing) {
            payload.georeferencing = georeferencing;
        }
        const queued = await api.startDetectCircleJob(payload);
        const data = await waitForJobResult(queued.job.id, 'Rilevamento cerchio');
        state.detectedCircle = data.circle;
        updateCircleStatus();
        const c = data.circle;
        addProjectHistory(
            'Cerchio georeferenziato',
            `${Math.round(c.radius_m)}m • ${c.accuracy_level || 'n/d'}`,
        );
        toast(
            `Cerchio rilevato • centro ${c.geo_center[1].toFixed(5)}, ${c.geo_center[0].toFixed(5)} • raggio ${Math.round(c.radius_m)}m`,
            'success',
        );
    } catch (e) {
        state.detectedCircle = null;
        updateCircleStatus();
        toast('Errore rilevamento cerchio: ' + e.message, 'error');
    } finally {
        hideLoading();
    }
}

function updateCircleStatus() {
    if (!el.circleDetectionStatus) return;
    if (!state.detectedCircle) {
        el.circleDetectionStatus.textContent = 'Cerchio: non rilevato';
        state.latestQualityMessage = 'Nessun cerchio rilevato: procedi pure con i poligoni.';
        renderWizardGuidance();
        return;
    }
    const c = state.detectedCircle;
    const acc = c.accuracy_level || 'n/d';
    const conf = typeof c.confidence === 'number' ? c.confidence.toFixed(3) : 'n/d';
    el.circleDetectionStatus.textContent = `Cerchio: ${Math.round(c.radius_m)}m • accuratezza ${acc} • conf ${conf}`;
    if (acc === 'strict') {
        state.latestQualityMessage = 'Qualita alta: cerchio preciso, pronto per export.';
    } else if (acc === 'medium') {
        state.latestQualityMessage = 'Qualita media: verifica visualmente il cerchio prima di esportare.';
    } else {
        state.latestQualityMessage = 'Qualita bassa: usa "Posiziona su Mappa" o riferimenti CV per migliorare il risultato.';
    }
    renderWizardGuidance();
}

// ==================== Segmentation ====================
async function runSegmentation() {
    if (!state.sessionId) return;
    showLoading('Segmentazione in coda...');
    exitEditMode(renderPolygons);
    
    try {
        const queued = await api.startSegmentationJob({
            session_id: state.sessionId,
            n_colors: parseInt(el.nColors.value),
            min_area: parseInt(el.minArea.value)
        });
        const data = await waitForJobResult(queued.job.id, 'Segmentazione');
        
        state.regions = data.regions;
        displayImage(data.visualization);
        renderPolygons();
        updateRegionsList();
        
        if (state.regions.length > 0) {
            updateStep(3, state);
        }
        addProjectHistory('Segmentazione completata', `${data.num_regions} regioni rilevate`);
        
        toast(`Trovate ${data.num_regions} regioni!`, 'success');
    } catch (e) {
        toast('Errore nella segmentazione: ' + e.message, 'error');
    } finally {
        hideLoading();
    }
}

function toggleClickMode() {
    state.clickMode = !state.clickMode;
    el.clickModeBtn.classList.toggle('active', state.clickMode);
    if (state.clickMode) exitEditMode(renderPolygons);
    toast(state.clickMode ? 'Clicca sull\'immagine per aggiungere regioni' : 'Modalità click disattivata', 'info');
}

async function handleCanvasClick(e) {
    if (state.isDrawing || state.currentTool === 'draw-point') {
        handleDrawClick(e, renderPolygons, openRenameModal);
        return;
    }
    
    if (!state.sessionId || state.editingRegionId !== null || !state.clickMode) return;
    
    const rect = el.canvas.getBoundingClientRect();
    const x = Math.round((e.clientX - rect.left) / state.canvasScale);
    const y = Math.round((e.clientY - rect.top) / state.canvasScale);
    
    showLoading('Rilevamento regione...');
    try {
        const data = await api.segmentAtPoint({ session_id: state.sessionId, x, y });
        
        if (data.success) {
            state.regions = data.regions;
            displayImage(data.visualization);
            renderPolygons();
            updateRegionsList();
            toast('Regione aggiunta!', 'success');
        } else {
            toast(data.message || 'Nessuna regione trovata in questo punto', 'warning');
        }
    } catch (e) {
        toast('Errore: ' + e.message, 'error');
    } finally {
        hideLoading();
    }
}

function handleCanvasMove(e) {
    if (!state.sessionId) return;
    const rect = el.canvas.getBoundingClientRect();
    const x = Math.round((e.clientX - rect.left) / state.canvasScale);
    const y = Math.round((e.clientY - rect.top) / state.canvasScale);
    el.cursorInfo.textContent = `x: ${x}, y: ${y}`;
}

// ==================== Polygon Rendering ====================
function renderPolygons() {
    el.polygonEditor.innerHTML = '';
    
    if (state.regions.length > 0) {
        el.editorToolbar.classList.add('visible');
    } else {
        el.editorToolbar.classList.remove('visible');
    }
    
    updateSelectionLabel(state);
    
    // Position and size to match canvas
    const wrapperRect = el.canvasWrapper.getBoundingClientRect();
    const rect = el.canvas.getBoundingClientRect();
    el.polygonEditor.style.left = (rect.left - wrapperRect.left) + 'px';
    el.polygonEditor.style.top = (rect.top - wrapperRect.top) + 'px';
    el.polygonEditor.style.width = rect.width + 'px';
    el.polygonEditor.style.height = rect.height + 'px';
    el.polygonEditor.setAttribute('width', rect.width);
    el.polygonEditor.setAttribute('height', rect.height);
    el.polygonEditor.setAttribute('viewBox', `0 0 ${rect.width} ${rect.height}`);
    
    state.regions.forEach((region, idx) => {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        
        const points = region.points.map(p => `${p[0] * state.canvasScale},${p[1] * state.canvasScale}`).join(' ');
        const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        polygon.classList.add('polygon-path');
        polygon.setAttribute('points', points);
        if (idx === state.selectedRegionId) polygon.classList.add('selected');
        
        polygon.onclick = e => { 
            e.stopPropagation(); 
            if (state.editingRegionId === null) {
                selectRegion(idx, renderPolygons); 
            }
        };
        polygon.ondblclick = e => { 
            e.stopPropagation(); 
            startEditRegion(idx, renderPolygons); 
        };
        polygon.onmousedown = e => {
            if (e.button !== 0) return;
            
            if (state.currentTool === 'move') {
                e.stopPropagation();
                e.preventDefault();
                selectRegion(idx, renderPolygons);
                startMoveShape(idx, e, renderPolygons, updateRegionsList);
            } else if (state.currentTool === 'scale') {
                e.stopPropagation();
                e.preventDefault();
                selectRegion(idx, renderPolygons);
                startScaleShape(idx, e, renderPolygons, updateRegionsList);
            } else if (state.currentTool === 'edit') {
                e.stopPropagation();
                startEditRegion(idx, renderPolygons);
            }
        };
        
        g.appendChild(polygon);
        
        if (idx === state.editingRegionId) {
            renderVertices(g, region, idx);
        }
        
        el.polygonEditor.appendChild(g);
    });
    
    // Render points
    state.points.forEach((point, idx) => {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.classList.add('map-point');
        circle.setAttribute('cx', point.x * state.canvasScale);
        circle.setAttribute('cy', point.y * state.canvasScale);
        circle.setAttribute('r', 8);
        if (idx === state.selectedPointId) circle.classList.add('selected');
        
        circle.onclick = e => {
            e.stopPropagation();
            state.selectedPointId = idx;
            state.selectedRegionId = null;
            updateSelectionLabel(state);
            renderPolygons();
        };
        
        const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text.classList.add('point-label');
        text.setAttribute('x', point.x * state.canvasScale + 12);
        text.setAttribute('y', point.y * state.canvasScale + 4);
        text.textContent = point.name;
        
        g.appendChild(circle);
        g.appendChild(text);
        el.polygonEditor.appendChild(g);
    });
    
    // Render drawing preview
    if (state.isDrawing && state.drawingPoints.length > 0) {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        g.classList.add('drawing-preview');
        
        if (state.drawingPoints.length > 1) {
            const pathData = state.drawingPoints.map((p, i) => 
                `${i === 0 ? 'M' : 'L'} ${p[0] * state.canvasScale} ${p[1] * state.canvasScale}`
            ).join(' ');
            
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.classList.add('drawing-line');
            path.setAttribute('d', pathData);
            g.appendChild(path);
        }
        
        state.drawingPoints.forEach((p, i) => {
            const v = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            v.classList.add('drawing-vertex');
            v.setAttribute('cx', p[0] * state.canvasScale);
            v.setAttribute('cy', p[1] * state.canvasScale);
            v.setAttribute('r', 6);
            g.appendChild(v);
        });
        
        el.polygonEditor.appendChild(g);
    }
}

function renderVertices(g, region, regionIdx) {
    const pts = region.points;
    
    // Midpoints
    pts.forEach((p, i) => {
        const next = pts[(i + 1) % pts.length];
        const midX = (p[0] + next[0]) / 2 * state.canvasScale;
        const midY = (p[1] + next[1]) / 2 * state.canvasScale;
        
        const mid = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        mid.classList.add('midpoint');
        mid.setAttribute('cx', midX);
        mid.setAttribute('cy', midY);
        mid.setAttribute('r', 4);
        mid.onclick = e => { e.stopPropagation(); addVertexAfter(i, renderPolygons); };
        g.appendChild(mid);
    });
    
    // Vertices
    pts.forEach((p, i) => {
        const v = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        v.classList.add('vertex');
        v.setAttribute('cx', p[0] * state.canvasScale);
        v.setAttribute('cy', p[1] * state.canvasScale);
        v.setAttribute('r', 6);
        if (i === state.selectedVertexIndex) v.classList.add('selected');
        
        v.onclick = e => { e.stopPropagation(); state.selectedVertexIndex = i; renderPolygons(); };
        v.onmousedown = e => { e.stopPropagation(); startDragVertex(regionIdx, i); };
        g.appendChild(v);
    });
}

function startDragVertex(regionIdx, vertexIdx) {
    const region = state.regions[regionIdx];
    
    const onMove = e => {
        const rect = el.polygonEditor.getBoundingClientRect();
        region.points[vertexIdx] = [
            Math.max(0, Math.min(state.imageWidth, (e.clientX - rect.left) / state.canvasScale)),
            Math.max(0, Math.min(state.imageHeight, (e.clientY - rect.top) / state.canvasScale))
        ];
        renderPolygons();
    };
    
    const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
    };
    
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
}

// ==================== Regions List ====================
function updateRegionsList() {
    if (el.alignBtn) el.alignBtn.disabled = state.regions.length === 0;
    renderWizardGuidance();
}

function addProjectHistory(action, details = '') {
    const ts = new Date().toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' });
    state.projectHistory.unshift({ ts, action, details });
    if (state.projectHistory.length > 25) state.projectHistory.length = 25;
    renderProjectHistory();
}

function renderProjectHistory() {
    if (!el.projectHistoryList) return;
    if (!state.projectHistory.length) {
        el.projectHistoryList.innerHTML = '<li class="text-muted">Nessuna attivita ancora</li>';
        return;
    }
    el.projectHistoryList.innerHTML = state.projectHistory
        .map(item => `<li><strong>${item.ts}</strong> - ${item.action}${item.details ? ` (${item.details})` : ''}</li>`)
        .join('');
}

function getNextRecommendedAction() {
    if (!state.sessionId) return { label: 'Carica una mappa', fn: () => el.fileInput?.click() };
    if (state.currentStep <= 2 && state.regions.length === 0) return { label: 'Avvia segmentazione', fn: runSegmentation };
    if (state.currentStep <= 3 && state.regions.length > 0) return { label: 'Controlla georeferenziazione', fn: openGeorefModal };
    if (state.currentStep < 4 && (state.regions.length > 0 || state.detectedCircle)) return { label: 'Vai a Export', fn: () => updateStep(4, state) };
    return { label: 'Scarica GeoJSON', fn: exportAndDownload };
}

function renderWizardGuidance() {
    const next = getNextRecommendedAction();
    if (el.wizardGuidance) {
        const stepLabels = {
            1: 'Step 1/4 - Upload',
            2: 'Step 2/4 - Segmentazione',
            3: 'Step 3/4 - Georeferenziazione',
            4: 'Step 4/4 - Export',
        };
        el.wizardGuidance.textContent = `${stepLabels[state.currentStep] || ''}: ${next.label}`;
    }
    if (el.qualityMessage) {
        el.qualityMessage.textContent = state.latestQualityMessage;
    }
    if (el.wizardNextActionBtn) {
        el.wizardNextActionBtn.textContent = next.label;
    }
}

function executeNextRecommendedAction() {
    const next = getNextRecommendedAction();
    if (typeof next.fn === 'function') next.fn();
}

function renderJobStatus() {
    if (!el.jobStatusList) return;
    if (!state.activeJobs.length) {
        el.jobStatusList.innerHTML = '<li class="text-muted">Nessun job in corso</li>';
        return;
    }
    el.jobStatusList.innerHTML = state.activeJobs
        .map(job => `<li><strong>${job.type}</strong> - ${job.status} (tentativi ${job.attempts}/${job.max_attempts})</li>`)
        .join('');
}

async function waitForJobResult(jobId, label = 'Job') {
    const maxPoll = 120;
    for (let i = 0; i < maxPoll; i += 1) {
        const statusRes = await api.getJobStatus(jobId);
        const job = statusRes.job;
        const existingIdx = state.activeJobs.findIndex(j => j.id === job.id);
        if (existingIdx >= 0) state.activeJobs[existingIdx] = job;
        else state.activeJobs.push(job);
        renderJobStatus();
        if (job.status === 'completed') {
            state.activeJobs = state.activeJobs.filter(j => j.id !== job.id);
            renderJobStatus();
            refreshOperationalDashboard();
            return job.result;
        }
        if (job.status === 'failed') {
            state.activeJobs = state.activeJobs.filter(j => j.id !== job.id);
            renderJobStatus();
            addProjectHistory(`${label} fallito`, job.error || 'Errore generico');
            refreshOperationalDashboard();
            throw new Error(job.error || `${label} fallito`);
        }
        await new Promise(resolve => setTimeout(resolve, 700));
    }
    throw new Error(`${label}: timeout monitoraggio job`);
}

async function refreshOperationalDashboard() {
    if (!el.errorDashboardList) return;
    try {
        const [jobsRes, errorsRes] = await Promise.all([
            api.listJobs(state.sessionId, 8),
            api.listOperationalErrors(8),
        ]);
        const jobs = jobsRes.jobs || [];
        const errors = errorsRes.errors || [];
        state.activeJobs = jobs.filter(j => ['queued', 'running', 'retrying'].includes(j.status));
        renderJobStatus();
        if (!errors.length) {
            el.errorDashboardList.innerHTML = '<li class="text-muted">Nessun errore operativo recente</li>';
            return;
        }
        el.errorDashboardList.innerHTML = errors
            .map(e => {
                const code = e.extra?.code || 'N/A';
                return `<li><strong>${code}</strong> - ${e.message}</li>`;
            })
            .join('');
    } catch (err) {
        el.errorDashboardList.innerHTML = `<li class="text-muted">Dashboard non disponibile: ${err.message}</li>`;
    }
}

async function deleteRegion(id) {
    if (!state.sessionId) return;
    if (state.editingRegionId === id) exitEditMode(renderPolygons);
    
    try {
        const data = await api.deleteRegion(id, state.sessionId);
        if (data.success) {
            state.regions = data.regions;
            state.selectedRegionId = null;
            displayImage(data.visualization);
            renderPolygons();
            updateRegionsList();
            toast('Regione eliminata', 'info');
        }
    } catch (e) {
        toast('Errore: ' + e.message, 'error');
    }
}

// ==================== Context Menu ====================
function handleContextMenu(e) {
    const isPolygon = e.target.classList.contains('polygon-path');
    if (!isPolygon && state.selectedRegionId === null) return;
    showContextMenu(e);
}

// ==================== Global Functions ====================
window.deleteRegion = deleteRegion;
window.selectRegion = (idx) => selectRegion(idx, renderPolygons);
window.startEditRegion = (idx) => startEditRegion(idx, renderPolygons);
window.setTool = setTool;
window.simplifyShape = () => simplifyShape(renderPolygons, updateRegionsList);
window.smoothShape = () => smoothShape(renderPolygons, updateRegionsList);
window.duplicateShape = () => duplicateShape(renderPolygons, updateRegionsList);
window.deleteSelectedShape = () => deleteSelectedShape(deleteRegion);
