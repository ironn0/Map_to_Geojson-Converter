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
    currentStep: 1,
    
    // Editor
    selectedRegionId: null,
    selectedPointId: null,
    editingRegionId: null,
    selectedVertexIndex: null,
    originalPoints: null,
    currentTool: 'select',
    
    // Drawing
    isDrawing: false,
    drawingPoints: [],
    
    // Georef
    georefMap: null,
    imageOverlay: null,
    overlayBounds: null,
    georefInitialBounds: null,
    georefDirty: false,
    georefRotationDegrees: 0,
    
    // Territory Alignment
    referenceGeojson: null,
    referenceName: null,
    cvReferenceImageBase64: null,
    cvReferenceImageName: null,
    detectedCircle: null,
    projectHistory: [],
    activeJobs: [],
    latestQualityMessage: 'Pronto a iniziare.'
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
    state.currentStep = 1;
    state.selectedRegionId = null;
    state.selectedPointId = null;
    state.editingRegionId = null;
    state.selectedVertexIndex = null;
    state.originalPoints = null;
    state.currentTool = 'select';
    state.isDrawing = false;
    state.drawingPoints = [];
    state.referenceGeojson = null;
    state.referenceName = null;
    state.cvReferenceImageBase64 = null;
    state.cvReferenceImageName = null;
    state.detectedCircle = null;
    state.projectHistory = [];
    state.activeJobs = [];
    state.latestQualityMessage = 'Pronto a iniziare.';
    state.georefInitialBounds = null;
    state.georefDirty = false;
    state.georefRotationDegrees = 0;
}

/**
 * Resetta lo stato dell'editor
 */
export function resetEditorState() {
    state.editingRegionId = null;
    state.selectedVertexIndex = null;
    state.originalPoints = null;
}
