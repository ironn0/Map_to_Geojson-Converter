/**
 * 📦 State Module
 * Gestione centralizzata dello stato dell'applicazione
 * 
 * Author: Map to GeoJSON Converter Project
 */

export const state = {
    // Session
    sessionId: null,
    regions: [],
    points: [],
    imageWidth: 0,
    imageHeight: 0,
    canvasScale: 1,
    clickMode: false,
    geojsonData: null,
    presets: {},
    imageBase64: null,
    segmentVisualization: null,
    currentStep: 1,
    
    // Editor
    selectedRegionId: null,
    selectedPointId: null,
    editingRegionId: null,
    selectedVertexIndex: null,
    originalPoints: null,
    currentTool: 'select',
    isErasing: false,
    eraseStrokes: [],
    currentEraseStroke: null,
    eraserRadius: 18,
    eraserMode: 'erase',
    eraserCursor: null,
    
    // Drawing
    isDrawing: false,
    drawingPoints: [],
    
    // Georef
    georefMap: null,
    imageOverlay: null,
    overlayBounds: null,
    
    // Territory Alignment
    referenceGeojson: null,
    referenceName: null
};

/**
 * Resetta lo stato della sessione
 */
export function resetState() {
    state.sessionId = null;
    state.regions = [];
    state.points = [];
    state.imageWidth = 0;
    state.imageHeight = 0;
    state.canvasScale = 1;
    state.clickMode = false;
    state.geojsonData = null;
    state.imageBase64 = null;
    state.segmentVisualization = null;
    state.currentStep = 1;
    state.selectedRegionId = null;
    state.selectedPointId = null;
    state.editingRegionId = null;
    state.selectedVertexIndex = null;
    state.originalPoints = null;
    state.currentTool = 'select';
    state.isErasing = false;
    state.eraseStrokes = [];
    state.currentEraseStroke = null;
    state.eraserRadius = 18;
    state.eraserMode = 'erase';
    state.eraserCursor = null;
    state.isDrawing = false;
    state.drawingPoints = [];
    state.referenceGeojson = null;
    state.referenceName = null;
}

/**
 * Resetta lo stato dell'editor
 */
export function resetEditorState() {
    state.editingRegionId = null;
    state.selectedVertexIndex = null;
    state.originalPoints = null;
}
