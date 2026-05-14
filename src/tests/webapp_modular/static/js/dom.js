/**
 * 🔗 DOM Elements Module
 * Riferimenti agli elementi DOM
 * 
 * Author: Map to GeoJSON Converter Project
 */

// Helper per ottenere elementi per ID
const $ = id => document.getElementById(id);

export const el = {
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
    statPoints: $('stat-points'),
    statVertices: $('stat-vertices'),
    
    // Editor toolbar
    editorToolbar: $('editor-toolbar'),
    selectionLabel: $('selection-label'),
    vertexTools: $('vertex-tools'),
    drawTools: $('draw-tools'),
    addVertexBtn: $('action-add-vertex'),
    deleteVertexBtn: $('action-delete-vertex'),
    savePolygonBtn: $('save-polygon-btn'),
    cancelEditBtn: $('cancel-edit-btn'),
    
    // Draw tools
    toolDrawPolygon: $('tool-draw-polygon'),
    toolDrawPoint: $('tool-draw-point'),
    finishDrawBtn: $('finish-draw-btn'),
    cancelDrawBtn: $('cancel-draw-btn'),
    
    // Rename
    renameBtn: $('action-rename'),
    renameModal: $('rename-modal'),
    renameModalClose: $('rename-modal-close'),
    renameInput: $('rename-input'),
    renameCancel: $('rename-cancel'),
    renameSave: $('rename-save'),
    
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
    georefReset: $('georef-reset'),
    georefResetRotation: $('georef-reset-rotation'),
    georefFit: $('georef-fit'),
    georefCancel: $('georef-cancel'),
    georefApply: $('georef-apply'),
    
    // Alignment
    cvAutoEnabled: $('cv-auto-enabled'),
    cvAutoControls: $('cv-auto-controls'),
    loadCvReferenceBtn: $('load-cv-reference-btn'),
    cvReferenceFile: $('cv-reference-file'),
    cvReferenceInfo: $('cv-reference-info'),
    cvReferenceName: $('cv-reference-name'),
    clearCvReferenceBtn: $('clear-cv-reference-btn'),
    cvRefBoundNorth: $('cv-ref-bound-north'),
    cvRefBoundSouth: $('cv-ref-bound-south'),
    cvRefBoundEast: $('cv-ref-bound-east'),
    cvRefBoundWest: $('cv-ref-bound-west'),
    cvRefUseCurrentBoundsBtn: $('cv-ref-use-current-bounds-btn'),
    cvConfidenceThreshold: $('cv-confidence-threshold'),
    cvConfidenceThresholdValue: $('cv-confidence-threshold-value'),
    cvQualityStatus: $('cv-quality-status'),
    loadReferenceBtn: $('load-reference-btn'),
    referenceFile: $('reference-file'),
    referenceInfo: $('reference-info'),
    clearReferenceBtn: $('clear-reference-btn'),
    referenceBoundsBtn: $('reference-bounds-btn'),
    snapStrength: $('snap-strength'),
    snapStrengthValue: $('snap-strength-value'),
    alignBtn: $('align-btn'),
    
    toastContainer: $('toast-container'),
    
    // Cookie banner
    cookieBanner: $('cookie-banner'),
    cookieAccept: $('cookie-accept'),
    cookieEssential: $('cookie-essential')
};

/**
 * Reinizializza i riferimenti DOM (utile dopo modifiche dinamiche)
 */
export function refreshElements() {
    el.steps = document.querySelectorAll('.step');
}
