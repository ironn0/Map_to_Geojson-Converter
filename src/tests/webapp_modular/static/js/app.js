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
    updateGeorefOverlay, applyGeoref, handleReferenceUpload, clearReference, alignToTerritories
} from './georef.js';
import { generateGeoJSON, exportAndDownload, previewGeoJSON, copyGeoJSON, downloadGeoJSON } from './export.js';
import { startDrawPolygon, startDrawPoint, handleDrawClick, finishDrawing, cancelDrawing } from './drawing.js';
import { openRenameModal, closeRenameModal, saveRename } from './rename.js';

// ==================== Initialize ====================
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🗺️ Map to GeoJSON - Modular Version Loaded');
    
    CookieManager.init();
    setupEventListeners();
    setupKeyboardShortcuts();
    
    state.presets = await api.loadPresets();
    updateStep(1, state);
    setTool('select');
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
            if (file?.type.startsWith('image/')) uploadFile(file);
        });
    });
    
    // Canvas
    el.canvas.addEventListener('click', handleCanvasClick);
    el.canvas.addEventListener('mousemove', handleCanvasMove);
    
    // Sliders
    el.nColors.addEventListener('input', e => el.nColorsValue.textContent = e.target.value);
    el.minArea.addEventListener('input', e => el.minAreaValue.textContent = e.target.value);
    el.snapStrength.addEventListener('input', e => el.snapStrengthValue.textContent = Math.round(e.target.value * 100) + '%');
    
    // Actions
    el.segmentBtn.addEventListener('click', runSegmentation);
    el.clickModeBtn.addEventListener('click', toggleClickMode);
    el.georefBtn.addEventListener('click', openGeorefModal);
    el.previewBtn.addEventListener('click', previewGeoJSON);
    el.copyBtn.addEventListener('click', copyGeoJSON);
    el.exportBtn.addEventListener('click', exportAndDownload);
    el.clearBtn.addEventListener('click', clearSession);
    
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
    el.deleteShapeBtn?.addEventListener('click', () => deleteSelectedShape(deleteRegion, renderPolygons, updateRegionsList));
    
    // Context menu
    document.addEventListener('contextmenu', handleContextMenu);
    document.addEventListener('click', () => hideContextMenu());
    
    // Context menu items
    document.getElementById('ctx-edit')?.addEventListener('click', () => { hideContextMenu(); if (state.selectedRegionId !== null) startEditRegion(state.selectedRegionId, renderPolygons); });
    document.getElementById('ctx-move')?.addEventListener('click', () => { hideContextMenu(); setTool('move'); });
    document.getElementById('ctx-duplicate')?.addEventListener('click', () => { hideContextMenu(); duplicateShape(renderPolygons, updateRegionsList); });
    document.getElementById('ctx-simplify')?.addEventListener('click', () => { hideContextMenu(); simplifyShape(renderPolygons, updateRegionsList); });
    document.getElementById('ctx-smooth')?.addEventListener('click', () => { hideContextMenu(); smoothShape(renderPolygons, updateRegionsList); });
    document.getElementById('ctx-delete')?.addEventListener('click', () => { hideContextMenu(); deleteSelectedShape(deleteRegion, renderPolygons, updateRegionsList); });
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
    el.georefRotation.addEventListener('input', updateGeorefOverlay);
    el.georefOpacity.addEventListener('input', updateGeorefOverlay);
    
    // Alignment controls
    el.loadReferenceBtn.addEventListener('click', () => el.referenceFile.click());
    el.referenceFile.addEventListener('change', handleReferenceUpload);
    el.clearReferenceBtn.addEventListener('click', clearReference);
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
                    deleteSelectedShape(deleteRegion, renderPolygons, updateRegionsList);
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
        
        displayImage(data.image);
        el.emptyState.classList.add('hidden');
        el.bottomBar.classList.remove('hidden');
        el.imageInfo.textContent = `${data.filename} • ${data.width}×${data.height}px`;
        
        el.clearBtn.disabled = false;
        updateStep(2, state);
        
        toast('Immagine caricata! Procedi con la segmentazione.', 'success');
    } catch (e) {
        toast('Errore nel caricamento: ' + e.message, 'error');
    } finally {
        hideLoading();
    }
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
    }
    
    resetState();
    exitEditMode(renderPolygons);
    
    el.canvas.getContext('2d').clearRect(0, 0, el.canvas.width, el.canvas.height);
    el.polygonEditor.innerHTML = '';
    el.emptyState.classList.remove('hidden');
    el.bottomBar.classList.add('hidden');
    el.fileInput.value = '';
    el.clearBtn.disabled = true;
    
    updateStep(1, state);
    toast('Sessione terminata', 'info');
}

// ==================== Segmentation ====================
async function runSegmentation() {
    if (!state.sessionId) return;
    showLoading('Analisi dell\'immagine...');
    exitEditMode(renderPolygons);
    
    try {
        const data = await api.runSegmentation({
            session_id: state.sessionId,
            n_colors: parseInt(el.nColors.value),
            min_area: parseInt(el.minArea.value)
        });
        
        state.regions = data.regions;
        state.segmentVisualization = data.visualization;
        displayImage(state.imageBase64);
        renderPolygons();
        updateRegionsList();
        
        if (state.regions.length > 0) {
            updateStep(3, state);
        }
        
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

    const existingRegionId = findRegionContainingPoint(x, y);
    if (existingRegionId !== null) {
        selectRegion(existingRegionId, renderPolygons);
        toast('Il punto e\' gia\' dentro una regione esistente. Eliminala prima di risegmentare.', 'info');
        return;
    }
    
    showLoading('Rilevamento regione...');
    try {
        const data = await api.segmentAtPoint({ session_id: state.sessionId, x, y });
        
        if (data.success) {
            const newRegion = data.regions[data.regions.length - 1];
            if (newRegion) {
                newRegion.id = state.regions.length;
                state.regions.push(newRegion);
            }
            state.segmentVisualization = data.visualization;
            displayImage(state.imageBase64);
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

function findRegionContainingPoint(x, y) {
    for (let i = state.regions.length - 1; i >= 0; i--) {
        const region = state.regions[i];
        if (region.points && pointInPolygon([x, y], region.points)) {
            return i;
        }
    }
    return null;
}

function pointInPolygon(point, polygon) {
    let inside = false;
    const [x, y] = point;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const xi = polygon[i][0], yi = polygon[i][1];
        const xj = polygon[j][0], yj = polygon[j][1];
        const intersects = ((yi > y) !== (yj > y)) &&
            (x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-9) + xi);
        if (intersects) inside = !inside;
    }
    return inside;
}

// ==================== Polygon Rendering ====================
function renderPolygons() {
    state.geojsonData = null;
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
            if (state.isDrawing || state.currentTool === 'draw-point') {
                handleDrawClick(e, renderPolygons, openRenameModal);
                return;
            }
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
            if (state.isDrawing || state.currentTool === 'draw-point') return;
            
            if (state.currentTool === 'move') {
                e.stopPropagation();
                e.preventDefault();
                selectRegion(idx, renderPolygons);
                startMoveShape(idx, e, renderPolygons);
            } else if (state.currentTool === 'scale') {
                e.stopPropagation();
                e.preventDefault();
                selectRegion(idx, renderPolygons);
                startScaleShape(idx, e, renderPolygons);
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
            if (state.isDrawing || state.currentTool === 'draw-point') {
                handleDrawClick(e, renderPolygons, openRenameModal);
                return;
            }
            state.selectedPointId = idx;
            state.selectedRegionId = null;
            updateSelectionLabel(state);
            renderPolygons();
        };
        circle.onmousedown = e => {
            if (e.button !== 0) return;
            if (state.isDrawing || state.currentTool === 'draw-point') return;
            e.stopPropagation();
            state.selectedPointId = idx;
            state.selectedRegionId = null;
            startDragPoint(idx);
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

function startDragPoint(pointIdx) {
    const point = state.points[pointIdx];
    if (!point) return;
    
    const onMove = e => {
        const rect = el.polygonEditor.getBoundingClientRect();
        point.x = Math.max(0, Math.min(state.imageWidth, (e.clientX - rect.left) / state.canvasScale));
        point.y = Math.max(0, Math.min(state.imageHeight, (e.clientY - rect.top) / state.canvasScale));
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
}

async function deleteRegion(id) {
    if (!state.sessionId) return;
    if (state.editingRegionId === id) exitEditMode(renderPolygons);

    state.regions.splice(id, 1);
    state.regions.forEach((region, idx) => region.id = idx);
    state.selectedRegionId = null;
    renderPolygons();
    updateRegionsList();
    toast('Regione eliminata', 'info');
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
window.deleteSelectedShape = () => deleteSelectedShape(deleteRegion, renderPolygons, updateRegionsList);
