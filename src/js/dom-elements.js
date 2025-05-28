// DOM Elements - 全体で使用されるDOM要素の取得
const videoFile = document.getElementById('videoFile');
const videoPlayer = document.getElementById('videoPlayer');
const videoCanvas = document.getElementById('videoCanvas');
const videoArea = document.getElementById('videoArea');
const loadingIndicator = document.getElementById('loadingIndicator');
const messageBox = document.getElementById('messageBox');
const messageText = document.getElementById('messageText');
const closeMessageButton = document.getElementById('closeMessageButton');
const appSubtitle = document.getElementById('appSubtitle');

// Capture Image Area - キャプチャ画像専用エリア
const captureImageArea = document.getElementById('captureImageArea');
const captureCanvas = document.getElementById('captureCanvas');
const captureZoomInButton = document.getElementById('captureZoomInButton');
const captureZoomOutButton = document.getElementById('captureZoomOutButton');
const captureZoomResetButton = document.getElementById('captureZoomResetButton');

// Mode Selection
const modeSelectionContainer = document.getElementById('modeSelectionContainer');
const dimensionModeButton = document.getElementById('dimensionModeButton');
const oncomingAnalysisModeButton = document.getElementById('oncomingAnalysisModeButton');

// Dimension Measurement Controls & Inputs
const dimensionControlsArea = document.getElementById('dimensionControlsArea');
const startDimensionMeasurementButton = document.getElementById('startDimensionMeasurementButton');
const dimensionMeasurementInputs = document.getElementById('dimensionMeasurementInputs'); 
const refObjectActualSizeInput = document.getElementById('refObjectActualSize');
const commonInstructionText = document.getElementById('commonInstructionText'); 

// Oncoming Vehicle Analysis Controls & Inputs
const oncomingAnalysisControlsArea = document.getElementById('oncomingAnalysisControlsArea');
const oncomingAnalysisInstructionText = document.getElementById('oncomingAnalysisInstructionText');
const captureFrameButton = document.getElementById('captureFrameButton'); 
const startVehicleMarkingButton = document.getElementById('startVehicleMarkingButton'); 

// Shared Controls (Zoom)
const sharedControlsContainer = document.getElementById('sharedControlsContainer'); 
const zoomControlsContainer = document.getElementById('zoomControlsContainer');
const zoomInButton = document.getElementById('zoomInButton');
const zoomOutButton = document.getElementById('zoomOutButton');
const zoomResetButton = document.getElementById('zoomResetButton');

// Results Area
const resultsArea = document.getElementById('resultsArea');
const resetCurrentModeButton = document.getElementById('resetCurrentModeButton');

// Dimension Results
const dimensionResultsDisplay = document.getElementById('dimensionResultsDisplay');
const dimensionStatusText = document.getElementById('dimensionStatusText');
const refPixelLengthText = document.getElementById('refPixelLengthText');
const scaleText = document.getElementById('scaleText');
const targetPixelLengthText = document.getElementById('targetPixelLengthText');
const estimatedSizeText = document.getElementById('estimatedSizeText');

// AI Comment
const aiCommentSection = document.getElementById('aiCommentSection');
const targetObjectNameInput = document.getElementById('targetObjectNameInput');
const getAiCommentButton = document.getElementById('getAiCommentButton');
const aiButtonLoader = document.getElementById('aiButtonLoader');
const aiCommentText = document.getElementById('aiCommentText');

// Oncoming Analysis Results
const oncomingAnalysisResultsDisplay = document.getElementById('oncomingAnalysisResultsDisplay');
const oncomingStatusText = document.getElementById('oncomingStatusText');
const vehicleAngle1Text = document.getElementById('vehicleAngle1Text');
const vehicleAngle2Text = document.getElementById('vehicleAngle2Text');
const angleChangeText = document.getElementById('angleChangeText');
const timeDiffText = document.getElementById('timeDiffText');

// Canvas contexts
const visibleCtx = videoCanvas.getContext('2d');
const sourceFrameCanvas = document.createElement('canvas'); // Offscreen
const sourceFrameCtx = sourceFrameCanvas.getContext('2d');

// Capture Canvas context
const captureCtx = captureCanvas.getContext('2d');
