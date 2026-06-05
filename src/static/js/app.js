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
} from './georef.js?v=ui20';
import { generateGeoJSON, exportAndDownload, previewGeoJSON, copyGeoJSON, downloadGeoJSON } from './export.js';
import { startDrawPolygon, startDrawPoint, handleDrawClick, finishDrawing, cancelDrawing } from './drawing.js';

const FEATURE_COLORS = [
    '#2563eb', '#dc2626', '#16a34a', '#f59e0b', '#7c3aed',
    '#0891b2', '#db2777', '#65a30d', '#ea580c', '#475569',
    '#0d9488', '#be123c', '#4f46e5', '#ca8a04', '#15803d'
];

let loadedRasterImage = null;
let fitCanvasScale = 1;
let manualZoomFactor = 1;
const MIN_CANVAS_SCALE = 0.2;
const MAX_CANVAS_SCALE = 8;

// ==================== Initialize ====================
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🗺️ Map to GeoJSON - Modular Version Loaded');
    
    CookieManager.init();
    document.body.classList.toggle('no-image', !state.imageBase64);
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
        document.getElementById('app')?.classList.toggle('inspector-hidden', el.sidebar.classList.contains('collapsed'));
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
    el.canvas.addEventListener('mousedown', startEraserStroke);
    el.canvas.addEventListener('click', handleCanvasClick);
    el.canvas.addEventListener('mousemove', handleCanvasMove);
    el.canvasWrapper.addEventListener('wheel', handleWheelZoom, { passive: false });
    document.addEventListener('mouseup', finishEraserStroke);
    
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
    el.toolSelect?.addEventListener('click', enterSelectTool);
    el.toolEdit?.addEventListener('click', enterEditTool);
    el.toolMove?.addEventListener('click', () => enterTransformTool('move'));
    el.toolScale?.addEventListener('click', () => enterTransformTool('scale'));
    el.toolEraser?.addEventListener('click', () => {
        if (!state.sessionId || state.regions.length === 0) {
            toast('Segmenta prima la mappa, poi usa la gomma', 'warning');
            return;
        }
        if (state.selectedRegionId === null) {
            toast('Seleziona prima la regione da correggere', 'warning');
            return;
        }
        if (state.editingRegionId !== null) {
            exitEditMode();
            renderPolygons();
        }
        state.clickMode = false;
        el.clickModeBtn.classList.remove('active');
        setTool('erase');
        updateEraserPanel();
    });
    el.eraserRadius?.addEventListener('input', e => {
        setEraserRadius(parseInt(e.target.value));
        renderPolygons();
    });
    document.querySelectorAll('.brush-size-btn').forEach(button => {
        button.addEventListener('click', () => {
            setEraserRadius(parseInt(button.dataset.radius));
            renderPolygons();
        });
    });
    el.eraseModeErase?.addEventListener('click', () => setEraserMode('erase'));
    el.eraseModeRestore?.addEventListener('click', () => setEraserMode('restore'));
    el.applyEraserBtn?.addEventListener('click', applyEraserCorrection);
    el.cancelEraserBtn?.addEventListener('click', cancelEraserCorrection);
    
    el.simplifyBtn?.addEventListener('click', () => simplifyShape(renderPolygons, updateRegionsList));
    el.smoothBtn?.addEventListener('click', () => smoothShape(renderPolygons, updateRegionsList));
    el.duplicateBtn?.addEventListener('click', () => duplicateShape(renderPolygons, updateRegionsList));
    el.deleteShapeBtn?.addEventListener('click', () => deleteSelectedShape(deleteRegion, renderPolygons, updateRegionsList));
    
    // Context menu
    document.addEventListener('contextmenu', handleContextMenu);
    document.addEventListener('click', () => hideContextMenu());
    
    // Context menu items
    document.getElementById('ctx-edit')?.addEventListener('click', () => { hideContextMenu(); if (state.selectedRegionId !== null) startEditRegion(state.selectedRegionId, renderPolygons); });
    document.getElementById('ctx-move')?.addEventListener('click', () => { hideContextMenu(); enterTransformTool('move'); });
    document.getElementById('ctx-duplicate')?.addEventListener('click', () => { hideContextMenu(); duplicateShape(renderPolygons, updateRegionsList); });
    document.getElementById('ctx-simplify')?.addEventListener('click', () => { hideContextMenu(); simplifyShape(renderPolygons, updateRegionsList); });
    document.getElementById('ctx-smooth')?.addEventListener('click', () => { hideContextMenu(); smoothShape(renderPolygons, updateRegionsList); });
    document.getElementById('ctx-delete')?.addEventListener('click', () => { hideContextMenu(); deleteSelectedShape(deleteRegion, renderPolygons, updateRegionsList); });
    document.getElementById('ctx-rename')?.addEventListener('click', () => { hideContextMenu(); openFeatureDetails(true); });
    
    // Draw tools
    el.toolDrawPolygon?.addEventListener('click', () => startDrawPolygon(renderPolygons));
    el.toolDrawPoint?.addEventListener('click', () => startDrawPoint());
    el.finishDrawBtn?.addEventListener('click', () => finishDrawing(renderPolygons, openFeatureDetails));
    el.cancelDrawBtn?.addEventListener('click', () => cancelDrawing(renderPolygons));
    
    // Feature details
    el.renameBtn?.addEventListener('click', () => openFeatureDetails(true));

    el.featureSaveBtn?.addEventListener('click', saveFeatureProperties);
    [
        el.featureNameInput,
        el.featureTypeInput,
        el.featureColorInput,
        el.featureDescriptionInput,
        el.featurePropsInput
    ].forEach(input => {
        input?.addEventListener('change', saveFeatureProperties);
    });
    el.featureDockClose?.addEventListener('click', () => {
        state.selectedRegionId = null;
        state.selectedPointId = null;
        state.selectedVertexIndex = null;
        renderPolygons();
    });
    
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
            case 'v': enterSelectTool(); break;
            case 'e': enterEditTool(); break;
            case 'm': enterTransformTool('move'); break;
            case 'g':
                if (state.sessionId && state.regions.length > 0) setTool('erase');
                break;
            case 's': if (!e.ctrlKey) enterTransformTool('scale'); break;
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
                    state.selectedPointId = null;
                    state.selectedVertexIndex = null;
                    renderPolygons();
                }
                break;
            case 'd':
                if (e.ctrlKey) { e.preventDefault(); duplicateShape(renderPolygons, updateRegionsList); }
                break;
        }
    });
}

function enterTransformTool(tool) {
    if (!['move', 'scale'].includes(tool)) return;
    if (state.selectedRegionId === null) {
        toast('Seleziona prima un\'area', 'warning');
        return;
    }

    if (state.editingRegionId !== null) {
        exitEditMode();
    }

    state.selectedVertexIndex = null;
    setTool(tool);
    renderPolygons();
    toast(
        tool === 'move'
            ? 'Trascina l\'area per spostarla'
            : 'Trascina su/giù sull\'area per ridimensionarla',
        'info'
    );
}

function enterSelectTool() {
    if (state.editingRegionId !== null) {
        exitEditMode();
    } else {
        state.selectedVertexIndex = null;
        setTool('select');
    }
    renderPolygons();
}

function enterEditTool() {
    if (state.selectedRegionId === null) {
        toast('Seleziona prima un\'area cliccandoci sopra', 'warning');
        return;
    }
    startEditRegion(state.selectedRegionId, renderPolygons);
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
        state.eraseStrokes = [];
        state.eraserCursor = null;
        manualZoomFactor = 1;
        document.body.classList.remove('no-image');
        
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
        loadedRasterImage = img;
        fitCanvasScale = calculateFitScale(img);
        renderRasterAtScale(clamp(fitCanvasScale * manualZoomFactor, MIN_CANVAS_SCALE, MAX_CANVAS_SCALE));
    };
    img.src = base64.startsWith('data:') ? base64 : 'data:image/png;base64,' + base64;
}

function calculateFitScale(img) {
    const wrapperRect = el.canvasWrapper.getBoundingClientRect();
    const maxW = Math.max(240, wrapperRect.width - 120);
    const maxH = Math.max(180, wrapperRect.height - 180);
    return Math.min(maxW / img.width, maxH / img.height, 2.4);
}

function renderRasterAtScale(scale) {
    if (!loadedRasterImage) return;

    const ctx = el.canvas.getContext('2d');
    state.canvasScale = scale;
    const displayWidth = Math.max(1, Math.round(loadedRasterImage.width * state.canvasScale));
    const displayHeight = Math.max(1, Math.round(loadedRasterImage.height * state.canvasScale));

    el.canvas.width = displayWidth;
    el.canvas.height = displayHeight;
    el.canvas.style.width = displayWidth + 'px';
    el.canvas.style.height = displayHeight + 'px';

    const stage = el.canvas.parentElement;
    if (stage) {
        stage.style.width = displayWidth + 'px';
        stage.style.height = displayHeight + 'px';
    }

    ctx.clearRect(0, 0, displayWidth, displayHeight);
    ctx.drawImage(loadedRasterImage, 0, 0, displayWidth, displayHeight);
    el.zoomLevel.textContent = Math.round(state.canvasScale * 100) + '%';

    requestAnimationFrame(() => {
        if (state.regions.length > 0 || state.points.length > 0) renderPolygons();
    });
}

function handleWheelZoom(e) {
    if (!loadedRasterImage || !state.imageBase64) return;

    const canvasRect = el.canvas.getBoundingClientRect();
    const isOverCanvas = e.clientX >= canvasRect.left
        && e.clientX <= canvasRect.right
        && e.clientY >= canvasRect.top
        && e.clientY <= canvasRect.bottom;
    if (!isOverCanvas) return;

    e.preventDefault();
    const imageX = (e.clientX - canvasRect.left) / state.canvasScale;
    const imageY = (e.clientY - canvasRect.top) / state.canvasScale;
    const zoomStep = e.deltaY < 0 ? 1.15 : 1 / 1.15;
    const nextScale = clamp(state.canvasScale * zoomStep, MIN_CANVAS_SCALE, MAX_CANVAS_SCALE);
    manualZoomFactor = nextScale / fitCanvasScale;

    renderRasterAtScale(nextScale);

    requestAnimationFrame(() => {
        const nextRect = el.canvas.getBoundingClientRect();
        el.canvasWrapper.scrollLeft += nextRect.left + imageX * state.canvasScale - e.clientX;
        el.canvasWrapper.scrollTop += nextRect.top + imageY * state.canvasScale - e.clientY;
    });
}

// ==================== Session ====================
async function clearSession() {
    if (state.sessionId) {
        try { await api.deleteSession(state.sessionId); } catch (e) {}
    }
    
    resetState();
    exitEditMode(renderPolygons);
    loadedRasterImage = null;
    fitCanvasScale = 1;
    manualZoomFactor = 1;
    
    el.canvas.getContext('2d').clearRect(0, 0, el.canvas.width, el.canvas.height);
    el.canvas.removeAttribute('style');
    el.canvas.width = 0;
    el.canvas.height = 0;
    el.polygonEditor.innerHTML = '';
    el.polygonEditor.removeAttribute('style');
    const stage = el.canvas.parentElement;
    if (stage) {
        stage.removeAttribute('style');
    }
    document.body.classList.add('no-image');
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
        assignFeatureColors();
        state.segmentVisualization = data.visualization;
        state.eraseStrokes = [];
        state.currentEraseStroke = null;
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
    if (state.currentTool === 'erase') {
        e.preventDefault();
        return;
    }

    if (state.isDrawing || state.currentTool === 'draw-point') {
        handleDrawClick(e, renderPolygons, openFeatureDetails);
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
                prepareFeature(newRegion, 'region', state.regions.length);
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

    if (state.isErasing) {
        appendEraserPoint(e);
    } else if (state.currentTool === 'erase') {
        state.eraserCursor = [x, y];
        renderPolygons();
    }
}

function setEraserMode(mode) {
    state.eraserMode = mode;
    el.eraseModeErase?.classList.toggle('active', mode === 'erase');
    el.eraseModeRestore?.classList.toggle('active', mode === 'restore');
    updateEraserPanel();
    renderPolygons();
}

function setEraserRadius(radius) {
    state.eraserRadius = Number.isFinite(radius) ? radius : 18;
    if (el.eraserRadius) el.eraserRadius.value = String(state.eraserRadius);
    if (el.eraserRadiusValue) el.eraserRadiusValue.textContent = String(state.eraserRadius);

    document.querySelectorAll('.brush-size-btn').forEach(button => {
        const buttonRadius = parseInt(button.dataset.radius);
        button.classList.toggle('active', buttonRadius === state.eraserRadius);
    });
}

function updateEraserPanel() {
    const count = state.eraseStrokes.filter(stroke => stroke.length > 0).length;
    if (el.eraserStrokesCount) {
        el.eraserStrokesCount.textContent = count === 1
            ? '1 area evidenziata'
            : `${count} aree evidenziate`;
    }
    if (el.applyEraserBtn) el.applyEraserBtn.disabled = count === 0;
    if (el.cancelEraserBtn) el.cancelEraserBtn.disabled = count === 0;
}

function imagePointFromEvent(e) {
    const rect = el.canvas.getBoundingClientRect();
    return [
        Math.max(0, Math.min(state.imageWidth, (e.clientX - rect.left) / state.canvasScale)),
        Math.max(0, Math.min(state.imageHeight, (e.clientY - rect.top) / state.canvasScale))
    ];
}

function startEraserStroke(e) {
    if (state.currentTool !== 'erase' || !state.sessionId) return;
    e.preventDefault();
    state.isErasing = true;
    state.currentEraseStroke = [imagePointFromEvent(e)];
    state.eraseStrokes.push(state.currentEraseStroke);
    updateEraserPanel();
    renderPolygons();
}

function appendEraserPoint(e) {
    if (!state.currentEraseStroke) return;
    const point = imagePointFromEvent(e);
    const last = state.currentEraseStroke[state.currentEraseStroke.length - 1];
    const dx = point[0] - last[0];
    const dy = point[1] - last[1];
    if (Math.sqrt(dx * dx + dy * dy) < 3) return;
    state.currentEraseStroke.push(point);
    updateEraserPanel();
    renderPolygons();
}

function finishEraserStroke() {
    if (!state.isErasing) return;
    state.isErasing = false;
    state.currentEraseStroke = null;
    updateEraserPanel();
    renderPolygons();
}

async function applyEraserCorrection() {
    if (!state.sessionId || state.eraseStrokes.length === 0) {
        toast('Passa prima la gomma sui dettagli da ignorare', 'warning');
        return;
    }
    if (state.eraserMode === 'erase' && state.selectedRegionId === null) {
        toast('Seleziona prima la regione da correggere, poi pennella la parte da ignorare', 'warning');
        return;
    }

    if (state.eraserMode === 'erase') {
        showLoading('Risegmentazione guidata...');
        try {
            const data = await api.resegmentWithBrush({
                session_id: state.sessionId,
                regions: state.regions,
                strokes: state.eraseStrokes,
                radius: state.eraserRadius,
                selected_region_id: state.selectedRegionId,
                n_colors: parseInt(el.nColors.value),
                min_area: parseInt(el.minArea.value)
            });

            if (!data.success) {
                toast(data.message || 'La risegmentazione guidata non ha modificato il segmento', 'warning');
                return;
            }

            state.regions = data.regions;
            assignFeatureColors();
            if (data.image) state.imageBase64 = data.image;
            state.eraseStrokes = [];
            state.currentEraseStroke = null;
            state.isErasing = false;
            state.eraserCursor = null;
            state.selectedRegionId = data.selected_region_id ?? state.selectedRegionId;
            state.selectedPointId = null;
            state.geojsonData = null;
            updateEraserPanel();
            if (data.image) displayImage(state.imageBase64);
            setTool('select');
            renderPolygons();
            updateRegionsList();
            updateStep(3, state);
            const seedText = data.seed ? ` seed ${Math.round(data.seed[0])},${Math.round(data.seed[1])}` : '';
            toast(`Regione risegmentata ignorando l'area marcata.${seedText}`, 'success');
        } catch (e) {
            toast('Errore risegmentazione guidata: ' + e.message, 'error');
        } finally {
            hideLoading();
        }
        return;
    }

    await applyRasterEraserCorrection();
}

async function applyRasterEraserCorrection() {
    showLoading('Correzione raster e nuova segmentazione...');
    try {
        const data = await api.eraseAndSegment({
            session_id: state.sessionId,
            strokes: state.eraseStrokes,
            radius: state.eraserRadius,
            mode: state.eraserMode,
            n_colors: parseInt(el.nColors.value),
            min_area: parseInt(el.minArea.value)
        });

        if (!data.success) {
            toast(data.message || 'Gomma non applicata', 'warning');
            return;
        }

        state.imageBase64 = data.image;
        state.regions = data.regions;
        assignFeatureColors();
        state.segmentVisualization = data.visualization;
        state.eraseStrokes = [];
        state.currentEraseStroke = null;
        state.isErasing = false;
        state.eraserCursor = null;
        state.selectedRegionId = null;
        updateEraserPanel();
        displayImage(state.imageBase64);
        renderPolygons();
        updateRegionsList();
        updateStep(3, state);
        toast(`Correzione applicata: ${data.num_regions} regioni`, 'success');
    } catch (e) {
        toast('Errore gomma: ' + e.message, 'error');
    } finally {
        hideLoading();
    }
}

function cancelEraserCorrection() {
    state.eraseStrokes = [];
    state.currentEraseStroke = null;
    state.isErasing = false;
    state.eraserCursor = null;
    updateEraserPanel();
    setTool('select');
    renderPolygons();
    toast('Pennellate gomma annullate', 'info');
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
    updateFeaturePropertiesPanel();
    renderFeatureList();
    
    // Position and size to match the canvas-stage, not the whole wrapper.
    const rect = el.canvas.getBoundingClientRect();
    el.polygonEditor.style.left = '0px';
    el.polygonEditor.style.top = '0px';
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
        if (region.color) {
            polygon.style.stroke = region.color;
            polygon.style.fill = hexToRgba(region.color, idx === state.selectedRegionId ? 0.38 : 0.18);
        }
        if (idx === state.selectedRegionId) polygon.classList.add('selected');
        
        polygon.onclick = e => { 
            e.stopPropagation(); 
            if (state.isDrawing || state.currentTool === 'draw-point') {
                handleDrawClick(e, renderPolygons, openFeatureDetails);
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
        
        if (state.currentTool === 'edit' && idx === state.editingRegionId) {
            renderVertices(g, region, idx);
        }
        
        el.polygonEditor.appendChild(g);
    });

    renderTransformGuide();
    
    // Render points
    state.points.forEach((point, idx) => {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.classList.add('map-point');
        circle.setAttribute('cx', point.x * state.canvasScale);
        circle.setAttribute('cy', point.y * state.canvasScale);
        circle.setAttribute('r', 8);
        circle.style.fill = normalizeHexColor(point.color || FEATURE_COLORS[(state.regions.length + idx) % FEATURE_COLORS.length]);
        circle.style.stroke = '#ffffff';
        if (idx === state.selectedPointId) circle.classList.add('selected');
        
        circle.onclick = e => {
            e.stopPropagation();
            if (state.isDrawing || state.currentTool === 'draw-point') {
                handleDrawClick(e, renderPolygons, openFeatureDetails);
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
            state.selectedPointId = idx;
            state.selectedRegionId = null;
            startDragPoint(idx, e);
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

    renderEraserPreview();
}

function renderEraserPreview() {
    if (state.currentTool !== 'erase' || (state.eraseStrokes.length === 0 && !state.eraserCursor)) return;

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.classList.add('eraser-preview');
    g.classList.add(`mode-${state.eraserMode}`);
    const radius = state.eraserRadius * state.canvasScale;

    state.eraseStrokes.forEach(stroke => {
        if (!stroke.length) return;
        const pathData = stroke.map((p, i) =>
            `${i === 0 ? 'M' : 'L'} ${p[0] * state.canvasScale} ${p[1] * state.canvasScale}`
        ).join(' ');
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.classList.add('eraser-stroke');
        path.setAttribute('d', pathData);
        path.setAttribute('stroke-width', radius * 2);
        g.appendChild(path);

        if (stroke.length === 1) {
            const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            dot.classList.add('eraser-dot');
            dot.setAttribute('cx', stroke[0][0] * state.canvasScale);
            dot.setAttribute('cy', stroke[0][1] * state.canvasScale);
            dot.setAttribute('r', radius);
            g.appendChild(dot);
        }
    });

    if (state.eraserCursor) {
        const cursor = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        cursor.classList.add('eraser-cursor');
        cursor.setAttribute('cx', state.eraserCursor[0] * state.canvasScale);
        cursor.setAttribute('cy', state.eraserCursor[1] * state.canvasScale);
        cursor.setAttribute('r', radius);
        g.appendChild(cursor);
    }

    el.polygonEditor.appendChild(g);
}

function renderTransformGuide() {
    if (!['move', 'scale'].includes(state.currentTool)) return;
    if (state.selectedRegionId === null || !state.regions[state.selectedRegionId]) return;

    const points = state.regions[state.selectedRegionId].points || [];
    if (points.length < 3) return;

    const xs = points.map(point => point[0] * state.canvasScale);
    const ys = points.map(point => point[1] * state.canvasScale);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.classList.add('transform-guide');
    g.classList.add(`mode-${state.currentTool}`);

    const startTransformDrag = e => {
        if (e.button !== 0) return;
        e.stopPropagation();
        e.preventDefault();
        const idx = state.selectedRegionId;
        if (idx === null || !state.regions[idx]) return;
        if (state.currentTool === 'move') {
            startMoveShape(idx, e, renderPolygons);
        } else if (state.currentTool === 'scale') {
            startScaleShape(idx, e, renderPolygons);
        }
    };

    const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
    rect.setAttribute('x', minX);
    rect.setAttribute('y', minY);
    rect.setAttribute('width', Math.max(1, maxX - minX));
    rect.setAttribute('height', Math.max(1, maxY - minY));
    rect.onmousedown = startTransformDrag;
    g.appendChild(rect);

    [[minX, minY], [maxX, minY], [maxX, maxY], [minX, maxY]].forEach(([x, y]) => {
        const handle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        handle.classList.add('transform-handle');
        handle.setAttribute('cx', x);
        handle.setAttribute('cy', y);
        handle.setAttribute('r', 5);
        handle.onmousedown = startTransformDrag;
        g.appendChild(handle);
    });

    el.polygonEditor.appendChild(g);
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
        v.onmousedown = e => startDragVertex(regionIdx, i, e);
        g.appendChild(v);
    });
}

function selectedFeature() {
    if (state.selectedRegionId !== null && state.regions[state.selectedRegionId]) {
        return { kind: 'region', item: state.regions[state.selectedRegionId], index: state.selectedRegionId };
    }
    if (state.selectedPointId !== null && state.points[state.selectedPointId]) {
        return { kind: 'point', item: state.points[state.selectedPointId], index: state.selectedPointId };
    }
    return null;
}

function prepareFeature(item, kind, index) {
    if (!item) return;

    if (!item.name) item.name = kind === 'region' ? `Regione ${index + 1}` : `Punto ${index + 1}`;
    if (!item.featureType) item.featureType = kind === 'region' ? (item.clientSide ? 'drawn-polygon' : 'area') : 'point';
    if (!item.properties || typeof item.properties !== 'object' || Array.isArray(item.properties)) item.properties = {};
    if (kind === 'region' && !item.colorEdited) item.color = FEATURE_COLORS[index % FEATURE_COLORS.length];
    if (kind === 'point' && !item.color) item.color = FEATURE_COLORS[(state.regions.length + index) % FEATURE_COLORS.length];
}

function assignFeatureColors() {
    state.regions.forEach((region, idx) => prepareFeature(region, 'region', idx));
    state.points.forEach((point, idx) => prepareFeature(point, 'point', idx));
}

function allFeatures() {
    return [
        ...state.regions.map((item, index) => ({ kind: 'region', item, index })),
        ...state.points.map((item, index) => ({ kind: 'point', item, index }))
    ];
}

function renderFeatureList() {
    if (!el.featuresList) return;

    assignFeatureColors();
    const features = allFeatures();
    if (el.featureCountLabel) {
        el.featureCountLabel.textContent = `${features.length} ${features.length === 1 ? 'elemento' : 'elementi'}`;
    }

    el.featuresList.innerHTML = '';
    el.featuresList.classList.toggle('empty', features.length === 0);
    if (features.length === 0) {
        const empty = document.createElement('div');
        empty.className = 'feature-empty';
        empty.textContent = 'Segmenta o disegna una regione';
        el.featuresList.appendChild(empty);
        return;
    }

    features.forEach(feature => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'feature-list-item';
        const isSelected = feature.kind === 'region'
            ? state.selectedRegionId === feature.index
            : state.selectedPointId === feature.index;
        button.classList.toggle('active', isSelected);

        const swatch = document.createElement('span');
        swatch.className = 'feature-swatch';
        swatch.style.backgroundColor = normalizeHexColor(feature.item.color || FEATURE_COLORS[feature.index % FEATURE_COLORS.length]);

        const text = document.createElement('span');
        text.className = 'feature-row-text';

        const name = document.createElement('strong');
        name.textContent = feature.item.name || (feature.kind === 'region' ? `Regione ${feature.index + 1}` : `Punto ${feature.index + 1}`);

        const meta = document.createElement('span');
        meta.textContent = feature.kind === 'region'
            ? `${feature.item.points?.length || 0} vertici${feature.item.area ? ` · ${Math.round(feature.item.area).toLocaleString('it-IT')} px` : ''}`
            : `Punto · x ${Math.round(feature.item.x)}, y ${Math.round(feature.item.y)}`;

        text.appendChild(name);
        text.appendChild(meta);
        button.appendChild(swatch);
        button.appendChild(text);
        button.addEventListener('click', () => {
            if (feature.kind === 'region') {
                state.selectedRegionId = feature.index;
                state.selectedPointId = null;
            } else {
                state.selectedPointId = feature.index;
                state.selectedRegionId = null;
            }
            state.selectedVertexIndex = null;
            updateSelectionLabel(state);
            renderPolygons();
        });

        el.featuresList.appendChild(button);
    });
}

function openFeatureDetails(focusName = false) {
    const selected = selectedFeature();
    if (!selected) {
        toast('Seleziona prima una regione o un punto', 'warning');
        return;
    }

    updateFeaturePropertiesPanel();
    el.featureDetailsDock?.classList.remove('hidden');
    if (focusName) {
        setTimeout(() => {
            el.featureNameInput?.focus();
            el.featureNameInput?.select();
        }, 0);
    }
}

function updateFeaturePropertiesPanel() {
    if (!el.featurePropertiesPanel) return;

    const selected = selectedFeature();
    el.featureDetailsDock?.classList.toggle('hidden', !selected);
    el.featurePropertiesPanel.classList.toggle('hidden', !selected);
    if (!selected) {
        if (el.featureKindLabel) el.featureKindLabel.textContent = 'Nessuna selezione';
        return;
    }

    const item = selected.item;
    el.featureKindLabel.textContent = selected.kind === 'region'
        ? `Area ${selected.index + 1}`
        : `Punto ${selected.index + 1}`;
    el.featureNameInput.value = item.name || '';
    el.featureTypeInput.value = item.featureType || (selected.kind === 'point' ? 'point' : 'area');
    el.featureColorInput.value = normalizeHexColor(item.color || '#3b82f6');
    el.featureDescriptionInput.value = item.description || '';
    el.featurePropsInput.value = JSON.stringify(item.properties || {}, null, 2);
    el.featureAreaValue.textContent = selected.kind === 'region' && item.area ? Math.round(item.area).toLocaleString('it-IT') : '-';
    el.featureVerticesValue.textContent = selected.kind === 'region' && item.points ? item.points.length : '-';
}

function saveFeatureProperties() {
    const selected = selectedFeature();
    if (!selected) {
        toast('Seleziona prima una feature', 'warning');
        return;
    }

    let properties = {};
    const rawProperties = el.featurePropsInput.value.trim();
    if (rawProperties) {
        try {
            properties = JSON.parse(rawProperties);
            if (!properties || Array.isArray(properties) || typeof properties !== 'object') {
                throw new Error('Le proprieta devono essere un oggetto JSON');
            }
        } catch (error) {
            toast('JSON proprieta non valido', 'error');
            return;
        }
    }

    const item = selected.item;
    item.name = el.featureNameInput.value.trim() || item.name || (selected.kind === 'region' ? `Regione ${selected.index + 1}` : `Punto ${selected.index + 1}`);
    item.featureType = el.featureTypeInput.value.trim() || (selected.kind === 'point' ? 'point' : 'area');
    item.color = normalizeHexColor(el.featureColorInput.value || item.color || '#3b82f6');
    item.colorEdited = true;
    item.description = el.featureDescriptionInput.value.trim();
    item.properties = properties;
    state.geojsonData = null;

    updateSelectionLabel(state);
    renderPolygons();
    updateRegionsList();
    toast('Proprieta salvate', 'success');
}

function normalizeHexColor(value) {
    if (!value || typeof value !== 'string') return '#3b82f6';
    const trimmed = value.trim();
    if (/^#[0-9a-fA-F]{6}$/.test(trimmed)) return trimmed;
    return '#3b82f6';
}

function hexToRgba(hex, alpha) {
    const color = normalizeHexColor(hex).slice(1);
    const r = parseInt(color.slice(0, 2), 16);
    const g = parseInt(color.slice(2, 4), 16);
    const b = parseInt(color.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

function polygonArea(points) {
    if (!points || points.length < 3) return 0;
    let area = 0;
    for (let i = 0; i < points.length; i++) {
        const next = points[(i + 1) % points.length];
        area += points[i][0] * next[1] - next[0] * points[i][1];
    }
    return Math.abs(area / 2);
}

function startDragVertex(regionIdx, vertexIdx, startEvent) {
    const region = state.regions[regionIdx];
    if (!region) return;

    startEvent.preventDefault();
    startEvent.stopPropagation();
    state.selectedVertexIndex = vertexIdx;
    let animationFrame = null;

    const moveVertex = e => {
        const rect = el.canvas.getBoundingClientRect();
        region.points[vertexIdx] = [
            Math.max(0, Math.min(state.imageWidth, (e.clientX - rect.left) / state.canvasScale)),
            Math.max(0, Math.min(state.imageHeight, (e.clientY - rect.top) / state.canvasScale))
        ];
        region.area = polygonArea(region.points);
        state.geojsonData = null;

        if (animationFrame === null) {
            animationFrame = requestAnimationFrame(() => {
                animationFrame = null;
                renderPolygons();
            });
        }
    };
    
    const onMove = e => {
        if (e.buttons === 0) {
            onUp();
            return;
        }
        moveVertex(e);
    };
    
    const onUp = () => {
        if (animationFrame !== null) {
            cancelAnimationFrame(animationFrame);
            animationFrame = null;
        }
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        renderPolygons();
        updateRegionsList();
    };
    
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    moveVertex(startEvent);
}

function startDragPoint(pointIdx, startEvent) {
    const point = state.points[pointIdx];
    if (!point) return;

    startEvent.preventDefault();
    startEvent.stopPropagation();
    let animationFrame = null;

    const movePoint = e => {
        const rect = el.canvas.getBoundingClientRect();
        point.x = Math.max(0, Math.min(state.imageWidth, (e.clientX - rect.left) / state.canvasScale));
        point.y = Math.max(0, Math.min(state.imageHeight, (e.clientY - rect.top) / state.canvasScale));
        state.geojsonData = null;

        if (animationFrame === null) {
            animationFrame = requestAnimationFrame(() => {
                animationFrame = null;
                renderPolygons();
            });
        }
    };
    
    const onMove = e => {
        if (e.buttons === 0) {
            onUp();
            return;
        }
        movePoint(e);
    };
    
    const onUp = () => {
        if (animationFrame !== null) {
            cancelAnimationFrame(animationFrame);
            animationFrame = null;
        }
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        renderPolygons();
        updateRegionsList();
    };
    
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
    movePoint(startEvent);
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
