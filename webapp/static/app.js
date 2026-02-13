/**
 * Map to GeoJSON - Modern UI Application
 * Redesigned for better user experience with step-by-step workflow
 */

// ==================== State ====================
const state = {
    sessionId: null,
    regions: [],
    imageWidth: 0,
    imageHeight: 0,
    canvasScale: 1,
    clickMode: false,
    geojsonData: null,
    presets: {},
    imageBase64: null,
    currentStep: 1,
    
    // Editor
    selectedRegionId: null,
    editingRegionId: null,
    selectedVertexIndex: null,
    originalPoints: null,
    currentTool: 'select', // select, edit, move, scale, add-vertex, delete-vertex
    
    // Georef
    georefMap: null,
    imageOverlay: null,
    overlayBounds: null,
    
    // Territory Alignment
    referenceGeojson: null,
    referenceName: null
};

// ==================== DOM Elements ====================
const $ = id => document.getElementById(id);
const el = {
    // Sidebar & steps
    sidebar: $('sidebar'),
    sidebarToggle: $('sidebar-toggle'),
    steps: document.querySelectorAll('.step'),
    
    // Panels
    panelUpload: $('panel-upload'),
    panelSegment: $('panel-segment'),
    panelGeoref: $('panel-georef'),
    panelExport: $('panel-export'),
    
    // Canvas
    canvas: $('main-canvas'),
    canvasWrapper: $('canvas-wrapper'),
    polygonEditor: $('polygon-editor'),
    emptyState: $('empty-state'),
    bottomBar: $('bottom-bar'),
    
    // Upload
    uploadArea: $('upload-area'),
    fileInput: $('file-input'),
    
    // Loading
    loadingOverlay: $('loading-overlay'),
    loadingText: $('loading-text'),
    progressFill: $('progress-fill'),
    
    // Info
    imageInfo: $('image-info'),
    cursorInfo: $('cursor-info'),
    zoomLevel: $('zoom-level'),
    
    // Controls
    nColors: $('n-colors'),
    nColorsValue: $('n-colors-value'),
    minArea: $('min-area'),
    minAreaValue: $('min-area-value'),
    presetSelect: $('preset-select'),
    boundNorth: $('bound-north'),
    boundSouth: $('bound-south'),
    boundEast: $('bound-east'),
    boundWest: $('bound-west'),
    
    // Buttons
    segmentBtn: $('segment-btn'),
    clickModeBtn: $('click-mode-btn'),
    georefBtn: $('georef-btn'),
    previewBtn: $('preview-btn'),
    copyBtn: $('copy-btn'),
    exportBtn: $('export-btn'),
    clearBtn: $('clear-btn'),
    
    // Export stats
    statRegions: $('stat-regions'),
    statVertices: $('stat-vertices'),
    
    // Editor toolbar
    editorToolbar: $('editor-toolbar'),
    addVertexBtn: $('action-add-vertex'),
    deleteVertexBtn: $('action-delete-vertex'),
    savePolygonBtn: $('save-polygon-btn'),
    cancelEditBtn: $('cancel-edit-btn'),
    
    // Tool buttons
    toolSelect: $('tool-select'),
    toolEdit: $('tool-edit'),
    toolMove: $('tool-move'),
    toolScale: $('tool-scale'),
    simplifyBtn: $('action-simplify'),
    smoothBtn: $('action-smooth'),
    duplicateBtn: $('action-duplicate'),
    deleteShapeBtn: $('action-delete'),
    
    // Context menu
    contextMenu: $('context-menu'),
    
    // Preview modal
    previewModal: $('preview-modal'),
    modalClose: $('modal-close'),
    modalCopy: $('modal-copy'),
    modalDownload: $('modal-download'),
    geojsonPreview: $('geojson-preview'),
    
    // Georef modal
    georefModal: $('georef-modal'),
    georefModalClose: $('georef-modal-close'),
    georefMap: $('georef-map'),
    georefRotation: $('georef-rotation'),
    georefRotationValue: $('georef-rotation-value'),
    georefOpacity: $('georef-opacity'),
    georefOpacityValue: $('georef-opacity-value'),
    georefCancel: $('georef-cancel'),
    georefApply: $('georef-apply'),
    
    // Alignment
    loadReferenceBtn: $('load-reference-btn'),
    referenceFile: $('reference-file'),
    referenceInfo: $('reference-info'),
    clearReferenceBtn: $('clear-reference-btn'),
    snapStrength: $('snap-strength'),
    snapStrengthValue: $('snap-strength-value'),
    alignBtn: $('align-btn'),
    
    toastContainer: $('toast-container')
};

// ==================== Initialize ====================
document.addEventListener('DOMContentLoaded', async () => {
    setupEventListeners();
    setupKeyboardShortcuts();
    await loadPresets();
    updateStep(1);
    setTool('select'); // Initialize default tool
});

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', e => {
        // Don't trigger shortcuts when typing in inputs
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        const key = e.key.toLowerCase();
        console.log('Key pressed:', key); // Debug
        
        switch(key) {
            case 'v': setTool('select'); break;
            case 'e': setTool('edit'); break;
            case 'm': setTool('move'); break;
            case 's': if (!e.ctrlKey) setTool('scale'); break;
            case 'delete':
            case 'backspace':
                e.preventDefault();
                if (state.selectedVertexIndex !== null && state.editingRegionId !== null) {
                    deleteSelectedVertex();
                } else if (state.selectedRegionId !== null) {
                    deleteSelectedShape();
                }
                break;
            case 'escape':
                if (state.editingRegionId !== null) {
                    cancelPolygonEdit();
                } else {
                    state.selectedRegionId = null;
                    renderPolygons();
                }
                break;
            case 'd':
                if (e.ctrlKey) { e.preventDefault(); duplicateShape(); }
                break;
        }
    });
    console.log('Keyboard shortcuts initialized');
}

function setupEventListeners() {
    // Sidebar toggle
    el.sidebarToggle?.addEventListener('click', () => {
        el.sidebar.classList.toggle('collapsed');
    });
    
    // Step navigation
    el.steps.forEach(step => {
        step.addEventListener('click', () => {
            const stepNum = parseInt(step.dataset.step);
            if (canNavigateToStep(stepNum)) {
                updateStep(stepNum);
            }
        });
    });
    
    // Upload area
    el.uploadArea.addEventListener('click', () => el.fileInput.click());
    el.fileInput.addEventListener('change', e => e.target.files[0] && uploadFile(e.target.files[0]));
    
    // Drag & drop on upload area and canvas wrapper
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
    el.exportBtn.addEventListener('click', exportGeoJSON);
    el.clearBtn.addEventListener('click', clearSession);
    
    // Presets
    el.presetSelect.addEventListener('change', handlePresetChange);
    
    // Editor toolbar
    el.addVertexBtn.addEventListener('click', () => toast('Clicca sui punti medi per aggiungere vertici', 'info'));
    el.deleteVertexBtn.addEventListener('click', deleteSelectedVertex);
    el.savePolygonBtn.addEventListener('click', savePolygonEdit);
    el.cancelEditBtn.addEventListener('click', cancelPolygonEdit);
    
    // Tool buttons - with null checks and logging
    if (el.toolSelect) {
        el.toolSelect.addEventListener('click', () => { console.log('Tool select clicked'); setTool('select'); });
    } else { console.warn('tool-select not found'); }
    
    if (el.toolEdit) {
        el.toolEdit.addEventListener('click', () => { console.log('Tool edit clicked'); setTool('edit'); });
    } else { console.warn('tool-edit not found'); }
    
    if (el.toolMove) {
        el.toolMove.addEventListener('click', () => { console.log('Tool move clicked'); setTool('move'); });
    } else { console.warn('tool-move not found'); }
    
    if (el.toolScale) {
        el.toolScale.addEventListener('click', () => { console.log('Tool scale clicked'); setTool('scale'); });
    } else { console.warn('tool-scale not found'); }
    
    if (el.simplifyBtn) {
        el.simplifyBtn.addEventListener('click', () => { console.log('Simplify clicked'); simplifyShape(); });
    } else { console.warn('action-simplify not found'); }
    
    if (el.smoothBtn) {
        el.smoothBtn.addEventListener('click', () => { console.log('Smooth clicked'); smoothShape(); });
    } else { console.warn('action-smooth not found'); }
    
    if (el.duplicateBtn) {
        el.duplicateBtn.addEventListener('click', () => { console.log('Duplicate clicked'); duplicateShape(); });
    } else { console.warn('action-duplicate not found'); }
    
    if (el.deleteShapeBtn) {
        el.deleteShapeBtn.addEventListener('click', () => { console.log('Delete clicked'); deleteSelectedShape(); });
    } else { console.warn('action-delete not found'); }
    
    // Context menu
    document.addEventListener('contextmenu', handleContextMenu);
    document.addEventListener('click', () => hideContextMenu());
    
    // Context menu items
    document.getElementById('ctx-edit')?.addEventListener('click', () => { hideContextMenu(); if (state.selectedRegionId !== null) startEditRegion(state.selectedRegionId); });
    document.getElementById('ctx-duplicate')?.addEventListener('click', () => { hideContextMenu(); duplicateShape(); });
    document.getElementById('ctx-simplify')?.addEventListener('click', () => { hideContextMenu(); simplifyShape(); });
    document.getElementById('ctx-smooth')?.addEventListener('click', () => { hideContextMenu(); smoothShape(); });
    document.getElementById('ctx-delete')?.addEventListener('click', () => { hideContextMenu(); deleteSelectedShape(); });
    
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
    el.alignBtn.addEventListener('click', alignTerritories);
    
    // Window resize
    window.addEventListener('resize', () => { 
        if (state.imageBase64) displayImage(state.imageBase64); 
    });
}

// ==================== Step Navigation ====================
function canNavigateToStep(stepNum) {
    if (stepNum === 1) return true;
    if (stepNum === 2) return !!state.sessionId;
    if (stepNum === 3) return state.regions.length > 0;
    if (stepNum === 4) return state.regions.length > 0;
    return false;
}

function updateStep(stepNum) {
    state.currentStep = stepNum;
    
    // Update step indicators
    el.steps.forEach(step => {
        const num = parseInt(step.dataset.step);
        step.classList.remove('active', 'completed');
        if (num === stepNum) step.classList.add('active');
        else if (num < stepNum && canNavigateToStep(num + 1)) step.classList.add('completed');
    });
    
    // Show/hide panels
    el.panelUpload.classList.toggle('hidden', stepNum !== 1);
    el.panelSegment.classList.toggle('hidden', stepNum !== 2);
    el.panelGeoref.classList.toggle('hidden', stepNum !== 3);
    el.panelExport.classList.toggle('hidden', stepNum !== 4);
    
    // Update export stats
    if (stepNum === 4) {
        updateExportStats();
    }
}

function updateExportStats() {
    el.statRegions.textContent = state.regions.length;
    const totalVertices = state.regions.reduce((sum, r) => sum + r.points.length, 0);
    el.statVertices.textContent = totalVertices;
}

// ==================== API ====================
async function api(endpoint, options = {}) {
    const res = await fetch(`/api${endpoint}`, { 
        headers: { 'Content-Type': 'application/json' }, 
        ...options 
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Errore');
    return res.json();
}

async function loadPresets() {
    try { 
        state.presets = await api('/presets'); 
    } catch (e) { 
        console.error('Failed to load presets:', e); 
    }
}

// ==================== File Upload ====================
async function uploadFile(file) {
    showLoading('Caricamento immagine...');
    try {
        const formData = new FormData();
        formData.append('file', file);
        const data = await (await fetch('/api/upload', { method: 'POST', body: formData })).json();
        
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
        updateStep(2);
        
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
        
        // Position polygon editor
        const rect = el.canvas.getBoundingClientRect();
        el.polygonEditor.style.position = 'absolute';
        el.polygonEditor.style.left = rect.left - wrapperRect.left + 'px';
        el.polygonEditor.style.top = rect.top - wrapperRect.top + 'px';
        el.polygonEditor.setAttribute('width', el.canvas.width);
        el.polygonEditor.setAttribute('height', el.canvas.height);
        
        if (state.regions.length > 0) renderPolygons();
    };
    img.src = base64.startsWith('data:') ? base64 : 'data:image/png;base64,' + base64;
}

// ==================== Session ====================
async function clearSession() {
    if (state.sessionId) {
        try { await api(`/session/${state.sessionId}`, { method: 'DELETE' }); } catch (e) {}
    }
    
    state.sessionId = null;
    state.regions = [];
    state.geojsonData = null;
    state.imageBase64 = null;
    state.selectedRegionId = null;
    exitEditMode();
    
    el.canvas.getContext('2d').clearRect(0, 0, el.canvas.width, el.canvas.height);
    el.polygonEditor.innerHTML = '';
    el.emptyState.classList.remove('hidden');
    el.bottomBar.classList.add('hidden');
    el.fileInput.value = '';
    el.clearBtn.disabled = true;
    
    updateStep(1);
    toast('Sessione terminata', 'info');
}

// ==================== Segmentation ====================
async function runSegmentation() {
    if (!state.sessionId) return;
    showLoading('Analisi dell\'immagine...');
    exitEditMode();
    
    try {
        const data = await api('/segment', {
            method: 'POST',
            body: JSON.stringify({
                session_id: state.sessionId,
                n_colors: parseInt(el.nColors.value),
                min_area: parseInt(el.minArea.value)
            })
        });
        
        state.regions = data.regions;
        displayImage(data.visualization);
        renderPolygons();
        updateRegionsList();
        
        if (state.regions.length > 0) {
            updateStep(3);
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
    if (state.clickMode) exitEditMode();
    toast(state.clickMode ? 'Clicca sull\'immagine per aggiungere regioni' : 'Modalità click disattivata', 'info');
}

async function handleCanvasClick(e) {
    if (!state.sessionId || state.editingRegionId !== null || !state.clickMode) return;
    
    const rect = el.canvas.getBoundingClientRect();
    const x = Math.round((e.clientX - rect.left) / state.canvasScale);
    const y = Math.round((e.clientY - rect.top) / state.canvasScale);
    
    showLoading('Rilevamento regione...');
    try {
        const data = await api('/segment-point', {
            method: 'POST',
            body: JSON.stringify({ session_id: state.sessionId, x, y })
        });
        
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

// ==================== Polygon Editor ====================
function renderPolygons() {
    el.polygonEditor.innerHTML = '';
    
    // Show/hide toolbar based on regions
    console.log('renderPolygons: regions count =', state.regions.length);
    if (state.regions.length > 0) {
        el.editorToolbar.classList.add('visible');
        console.log('Toolbar now visible');
    } else {
        el.editorToolbar.classList.remove('visible');
    }
    
    // Update position
    const wrapperRect = el.canvasWrapper.getBoundingClientRect();
    const rect = el.canvas.getBoundingClientRect();
    el.polygonEditor.style.left = rect.left - wrapperRect.left + 'px';
    el.polygonEditor.style.top = rect.top - wrapperRect.top + 'px';
    
    state.regions.forEach((region, idx) => {
        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        
        const points = region.points.map(p => `${p[0] * state.canvasScale},${p[1] * state.canvasScale}`).join(' ');
        const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        polygon.classList.add('polygon-path');
        polygon.setAttribute('points', points);
        if (idx === state.selectedRegionId) polygon.classList.add('selected');
        
        // Click handlers based on current tool
        polygon.onclick = e => { 
            e.stopPropagation(); 
            if (state.editingRegionId === null) {
                selectRegion(idx); 
            }
        };
        polygon.ondblclick = e => { 
            e.stopPropagation(); 
            startEditRegion(idx); 
        };
        polygon.onmousedown = e => {
            if (e.button !== 0) return; // Only left click
            
            // Move tool - works on any polygon, selects it first
            if (state.currentTool === 'move') {
                e.stopPropagation();
                e.preventDefault();
                selectRegion(idx);
                startMoveShape(idx, e);
            } 
            // Scale tool - works on any polygon, selects it first
            else if (state.currentTool === 'scale') {
                e.stopPropagation();
                e.preventDefault();
                selectRegion(idx);
                startScaleShape(idx, e);
            }
            // Edit tool - enter edit mode on click
            else if (state.currentTool === 'edit') {
                e.stopPropagation();
                startEditRegion(idx);
            }
        };
        
        g.appendChild(polygon);
        
        if (idx === state.editingRegionId) {
            renderVertices(g, region, idx);
        }
        
        el.polygonEditor.appendChild(g);
    });
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
        mid.onclick = e => { e.stopPropagation(); addVertexAfter(i); };
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

function selectRegion(idx) {
    const wasSelected = state.selectedRegionId === idx;
    state.selectedRegionId = idx;
    state.selectedVertexIndex = null;
    renderPolygons();
    
    // Show info about selected region
    if (!wasSelected && state.regions[idx]) {
        const r = state.regions[idx];
        toast(`${r.name} selezionata • ${r.points.length} vertici`, 'info');
    }
}

function startEditRegion(idx) {
    if (state.editingRegionId !== null && state.editingRegionId !== idx) exitEditMode();
    
    state.editingRegionId = idx;
    state.selectedRegionId = idx;
    state.selectedVertexIndex = null;
    state.originalPoints = JSON.parse(JSON.stringify(state.regions[idx].points));
    
    el.polygonEditor.classList.add('active');
    setTool('edit');
    
    if (state.clickMode) { 
        state.clickMode = false; 
        el.clickModeBtn.classList.remove('active'); 
    }
    
    renderPolygons();
    updateRegionsList();
    toast('Trascina i vertici per modificare la forma', 'info');
}

function exitEditMode() {
    state.editingRegionId = null;
    state.selectedVertexIndex = null;
    state.originalPoints = null;
    el.polygonEditor.classList.remove('active');
    setTool('select');
}

function addVertexAfter(afterIndex) {
    if (state.editingRegionId === null) return;
    
    const pts = state.regions[state.editingRegionId].points;
    const next = (afterIndex + 1) % pts.length;
    pts.splice(afterIndex + 1, 0, [
        (pts[afterIndex][0] + pts[next][0]) / 2, 
        (pts[afterIndex][1] + pts[next][1]) / 2
    ]);
    state.selectedVertexIndex = afterIndex + 1;
    
    renderPolygons();
    toast('Vertice aggiunto', 'success');
}

function deleteSelectedVertex() {
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
    renderPolygons();
    toast('Vertice eliminato', 'success');
}

async function savePolygonEdit() {
    if (state.editingRegionId === null) return;
    
    showLoading('Salvataggio...');
    try {
        const data = await api('/update-region', {
            method: 'POST',
            body: JSON.stringify({
                session_id: state.sessionId,
                region_id: state.editingRegionId,
                points: state.regions[state.editingRegionId].points
            })
        });
        
        if (data.success) {
            state.regions = data.regions;
            exitEditMode();
            renderPolygons();
            updateRegionsList();
            toast('Modifiche salvate!', 'success');
        }
    } catch (e) {
        toast('Errore nel salvataggio: ' + e.message, 'error');
    } finally {
        hideLoading();
    }
}

function cancelPolygonEdit() {
    if (state.editingRegionId !== null && state.originalPoints) {
        state.regions[state.editingRegionId].points = state.originalPoints;
    }
    exitEditMode();
    renderPolygons();
    toast('Modifiche annullate', 'info');
}

// ==================== Tool System ====================
function setTool(tool) {
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
        console.log('Active tool button:', activeBtn.id);
    } else {
        console.warn('Tool button not found: tool-' + tool);
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
    
    // If selecting edit tool, require a shape to be selected
    if (tool === 'edit' && state.selectedRegionId !== null) {
        startEditRegion(state.selectedRegionId);
    }
}

function simplifyShape() {
    if (state.selectedRegionId === null) {
        toast('Seleziona prima una forma', 'warning');
        return;
    }
    
    const region = state.regions[state.selectedRegionId];
    if (region.points.length <= 3) {
        toast('La forma ha già il minimo di vertici', 'warning');
        return;
    }
    
    // Ramer-Douglas-Peucker simplification
    const simplified = simplifyPolygon(region.points, 3);
    if (simplified.length < 3) {
        toast('Non è possibile semplificare ulteriormente', 'warning');
        return;
    }
    
    region.points = simplified;
    renderPolygons();
    updateRegionsList();
    toast(`Semplificato a ${simplified.length} vertici`, 'success');
}

function simplifyPolygon(points, tolerance) {
    if (points.length <= 2) return points;
    
    // Find the point with the maximum distance
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

function smoothShape() {
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
    renderPolygons();
    updateRegionsList();
    toast('Forma levigata', 'success');
}

function duplicateShape() {
    if (state.selectedRegionId === null) {
        toast('Seleziona prima una forma', 'warning');
        return;
    }
    
    const original = state.regions[state.selectedRegionId];
    const offset = 20; // Pixel offset
    
    const duplicate = {
        ...original,
        name: original.name + ' (copia)',
        points: original.points.map(p => [p[0] + offset, p[1] + offset])
    };
    
    state.regions.push(duplicate);
    state.selectedRegionId = state.regions.length - 1;
    renderPolygons();
    updateRegionsList();
    toast('Forma duplicata', 'success');
}

function deleteSelectedShape() {
    if (state.selectedRegionId === null) {
        toast('Seleziona prima una forma', 'warning');
        return;
    }
    
    deleteRegion(state.selectedRegionId);
}

// ==================== Context Menu ====================
function handleContextMenu(e) {
    // Only show context menu if clicking on a polygon or when a region is selected
    if (!el.contextMenu) return;
    
    const isPolygon = e.target.classList.contains('polygon-path');
    if (!isPolygon && state.selectedRegionId === null) return;
    
    e.preventDefault();
    
    // Position the menu
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

function hideContextMenu() {
    if (el.contextMenu) {
        el.contextMenu.classList.remove('show');
    }
}

// ==================== Move & Scale Shape ====================
function startMoveShape(regionIdx, startEvent) {
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
        renderPolygons();
    };
    
    const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        toast('Forma spostata', 'success');
    };
    
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
}

function startScaleShape(regionIdx, startEvent) {
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
        renderPolygons();
    };
    
    const onUp = () => {
        document.removeEventListener('mousemove', onMove);
        document.removeEventListener('mouseup', onUp);
        toast('Forma ridimensionata', 'success');
    };
    
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
}

// ==================== Regions List ====================
function updateRegionsList() {
    // Just update button states since we removed the regions list
    if (el.alignBtn) el.alignBtn.disabled = state.regions.length === 0;
}

async function deleteRegion(id) {
    if (!state.sessionId) return;
    if (state.editingRegionId === id) exitEditMode();
    
    try {
        const data = await api(`/delete-region/${id}?session_id=${state.sessionId}`, { method: 'POST' });
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

// ==================== Geo Bounds ====================
function handlePresetChange() {
    const preset = el.presetSelect.value;
    if (preset !== 'custom' && state.presets[preset]) {
        const b = state.presets[preset];
        el.boundNorth.value = b.north;
        el.boundSouth.value = b.south;
        el.boundEast.value = b.east;
        el.boundWest.value = b.west;
    }
}

function getBounds() {
    return {
        north: parseFloat(el.boundNorth.value),
        south: parseFloat(el.boundSouth.value),
        east: parseFloat(el.boundEast.value),
        west: parseFloat(el.boundWest.value)
    };
}

// ==================== Georeferencing ====================
let cornerMarkers = [];

function openGeorefModal() {
    if (!state.sessionId || !state.imageBase64) { 
        toast('Carica prima un\'immagine', 'warning'); 
        return; 
    }
    el.georefModal.classList.add('visible');
    setTimeout(initGeorefMap, 100);
}

function closeGeorefModal() {
    el.georefModal.classList.remove('visible');
    cornerMarkers = [];
    if (state.georefMap) { 
        state.georefMap.remove(); 
        state.georefMap = null; 
        state.imageOverlay = null; 
    }
}

function initGeorefMap() {
    const b = getBounds();
    const center = [(b.north + b.south) / 2, (b.east + b.west) / 2];
    
    state.georefMap = L.map(el.georefMap, { center, zoom: 5 });
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { 
        attribution: '© OpenStreetMap' 
    }).addTo(state.georefMap);
    
    const bounds = L.latLngBounds([b.south, b.west], [b.north, b.east]);
    state.imageOverlay = L.imageOverlay('data:image/png;base64,' + state.imageBase64, bounds, { 
        opacity: 0.7, 
        interactive: true 
    }).addTo(state.georefMap);
    state.overlayBounds = bounds;
    
    createCornerMarkers();
    
    // Dragging the image
    const img = state.imageOverlay.getElement();
    if (img) {
        img.style.cursor = 'move';
        let dragging = false, startLatLng, startBounds;
        
        img.onmousedown = e => {
            dragging = true;
            startLatLng = state.georefMap.mouseEventToLatLng(e);
            startBounds = L.latLngBounds(state.overlayBounds.getSouthWest(), state.overlayBounds.getNorthEast());
            e.stopPropagation();
        };
        
        state.georefMap.on('mousemove', e => {
            if (!dragging) return;
            const dLat = e.latlng.lat - startLatLng.lat;
            const dLng = e.latlng.lng - startLatLng.lng;
            state.overlayBounds = L.latLngBounds(
                [startBounds.getSouth() + dLat, startBounds.getWest() + dLng],
                [startBounds.getNorth() + dLat, startBounds.getEast() + dLng]
            );
            state.imageOverlay.setBounds(state.overlayBounds);
            updateCornerMarkers();
        });
        
        state.georefMap.on('mouseup', () => dragging = false);
    }
    
    state.georefMap.fitBounds(bounds.pad(0.1));
}

function createCornerMarkers() {
    cornerMarkers.forEach(m => m.remove());
    cornerMarkers = [];
    
    const b = state.overlayBounds;
    const corners = [
        { pos: 'nw', latlng: [b.getNorth(), b.getWest()], cursor: 'nw-resize' },
        { pos: 'ne', latlng: [b.getNorth(), b.getEast()], cursor: 'ne-resize' },
        { pos: 'se', latlng: [b.getSouth(), b.getEast()], cursor: 'se-resize' },
        { pos: 'sw', latlng: [b.getSouth(), b.getWest()], cursor: 'sw-resize' }
    ];
    
    corners.forEach(corner => {
        const icon = L.divIcon({
            className: 'corner-marker',
            html: `<div class="corner-handle" style="cursor:${corner.cursor}"></div>`,
            iconSize: [16, 16],
            iconAnchor: [8, 8]
        });
        
        const marker = L.marker(corner.latlng, { 
            icon, 
            draggable: true,
            autoPan: false
        }).addTo(state.georefMap);
        
        marker.cornerPos = corner.pos;
        marker.on('drag', e => handleCornerDrag(corner.pos, e.latlng));
        marker.on('dragend', () => updateCornerMarkers());
        
        cornerMarkers.push(marker);
    });
}

function handleCornerDrag(pos, latlng) {
    const b = state.overlayBounds;
    let north = b.getNorth(), south = b.getSouth(), east = b.getEast(), west = b.getWest();
    
    switch(pos) {
        case 'nw': north = latlng.lat; west = latlng.lng; break;
        case 'ne': north = latlng.lat; east = latlng.lng; break;
        case 'se': south = latlng.lat; east = latlng.lng; break;
        case 'sw': south = latlng.lat; west = latlng.lng; break;
    }
    
    if (north > south + 0.01 && east > west + 0.01) {
        state.overlayBounds = L.latLngBounds([south, west], [north, east]);
        state.imageOverlay.setBounds(state.overlayBounds);
        
        cornerMarkers.forEach(m => {
            if (m.cornerPos !== pos) {
                m.setLatLng(getCornerPosition(m.cornerPos));
            }
        });
    }
}

function getCornerPosition(pos) {
    const b = state.overlayBounds;
    switch(pos) {
        case 'nw': return [b.getNorth(), b.getWest()];
        case 'ne': return [b.getNorth(), b.getEast()];
        case 'se': return [b.getSouth(), b.getEast()];
        case 'sw': return [b.getSouth(), b.getWest()];
    }
}

function updateCornerMarkers() {
    cornerMarkers.forEach(m => m.setLatLng(getCornerPosition(m.cornerPos)));
}

function updateGeorefOverlay() {
    if (!state.imageOverlay || !state.overlayBounds) return;
    
    const opacity = parseFloat(el.georefOpacity.value);
    const rotation = parseFloat(el.georefRotation.value);
    
    el.georefOpacityValue.textContent = Math.round(opacity * 100) + '%';
    el.georefRotationValue.textContent = rotation + '°';
    
    state.imageOverlay.setOpacity(opacity);
    
    const img = state.imageOverlay.getElement();
    if (img) { 
        img.style.transformOrigin = 'center'; 
        img.style.transform = `rotate(${rotation}deg)`; 
    }
}

function applyGeoref() {
    if (!state.overlayBounds) { 
        toast('Errore nella georeferenziazione', 'error'); 
        return; 
    }
    
    const b = state.imageOverlay.getBounds();
    el.boundNorth.value = b.getNorth().toFixed(4);
    el.boundSouth.value = b.getSouth().toFixed(4);
    el.boundEast.value = b.getEast().toFixed(4);
    el.boundWest.value = b.getWest().toFixed(4);
    el.presetSelect.value = 'custom';
    
    closeGeorefModal();
    toast('Coordinate geografiche applicate!', 'success');
}

// ==================== Territory Alignment ====================
async function handleReferenceUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    showLoading('Caricamento riferimento...');
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/upload-reference', { method: 'POST', body: formData });
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Errore nel caricamento');
        }
        
        state.referenceGeojson = data.geojson;
        state.referenceName = file.name;
        
        el.referenceInfo.classList.remove('hidden');
        el.referenceInfo.querySelector('.reference-name').textContent = `${file.name} (${data.num_features} territories)`;
        el.alignBtn.disabled = state.regions.length === 0;
        
        toast(`Riferimento caricato: ${data.num_features} territori`, 'success');
        
    } catch (err) {
        toast('Errore: ' + err.message, 'error');
    } finally {
        hideLoading();
        e.target.value = '';
    }
}

function clearReference() {
    state.referenceGeojson = null;
    state.referenceName = null;
    el.referenceInfo.classList.add('hidden');
    toast('Riferimento rimosso', 'info');
}

async function alignTerritories() {
    if (!state.sessionId || state.regions.length === 0) {
        toast('Nessuna regione da allineare', 'warning');
        return;
    }
    
    showLoading('Allineamento ai confini reali...');
    
    try {
        const requestBody = {
            session_id: state.sessionId,
            bounds: getBounds(),
            snap_strength: parseFloat(el.snapStrength.value)
        };
        
        if (state.referenceGeojson) {
            requestBody.reference_geojson = state.referenceGeojson;
        }
        
        const data = await api('/align', {
            method: 'POST',
            body: JSON.stringify(requestBody)
        });
        
        if (data.success) {
            state.regions = data.regions;
            updateRegionsList();
            
            if (data.visualization) {
                displayImage('data:image/png;base64,' + data.visualization);
            }
            
            if (data.aligned_geojson) {
                state.geojsonData = data.aligned_geojson;
            }
            
            toast(data.message || 'Allineamento completato!', 'success');
        } else {
            toast('Allineamento non riuscito', 'warning');
        }
        
    } catch (err) {
        toast('Errore: ' + err.message, 'error');
    } finally {
        hideLoading();
    }
}

// ==================== Export ====================
async function generateGeoJSON() {
    if (!state.sessionId || state.regions.length === 0) return null;
    try {
        state.geojsonData = await api('/export', { 
            method: 'POST', 
            body: JSON.stringify({ session_id: state.sessionId, bounds: getBounds() }) 
        });
        return state.geojsonData;
    } catch (e) {
        toast('Errore nella generazione: ' + e.message, 'error');
        return null;
    }
}

async function exportGeoJSON() {
    showLoading('Generazione GeoJSON...');
    const geojson = await generateGeoJSON();
    hideLoading();
    if (geojson) downloadGeoJSON();
}

async function previewGeoJSON() {
    showLoading('Generazione anteprima...');
    const geojson = await generateGeoJSON();
    hideLoading();
    if (geojson) {
        el.geojsonPreview.textContent = JSON.stringify(geojson, null, 2);
        el.previewModal.classList.add('visible');
    }
}

async function copyGeoJSON() {
    const geojson = state.geojsonData || await generateGeoJSON();
    if (geojson) { 
        navigator.clipboard.writeText(JSON.stringify(geojson, null, 2)); 
        toast('GeoJSON copiato negli appunti!', 'success'); 
    }
}

function downloadGeoJSON() {
    if (!state.geojsonData) return;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(state.geojsonData, null, 2)], { type: 'application/json' }));
    a.download = 'map_regions.geojson';
    a.click();
    toast('GeoJSON scaricato!', 'success');
}

// ==================== UI Helpers ====================
function showLoading(text = 'Elaborazione...') {
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

function hideLoading() {
    el.progressFill.style.width = '100%';
    clearInterval(el.loadingOverlay.dataset.interval);
    setTimeout(() => {
        el.loadingOverlay.classList.remove('visible');
    }, 150);
}

function toast(message, type = 'info') {
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

// ==================== Global Functions ====================
window.deleteRegion = deleteRegion;
window.selectRegion = selectRegion;
window.startEditRegion = startEditRegion;
window.setTool = setTool;
window.simplifyShape = simplifyShape;
window.smoothShape = smoothShape;
window.duplicateShape = duplicateShape;
window.deleteSelectedShape = deleteSelectedShape;
