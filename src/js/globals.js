// Global state variables - アプリケーション全体で使用される状態変数

// アプリケーションモード
let currentAppMode = 'none';
let measurementState = 'idle';

// 測定データ
let points = [];
let pointsForRefLine = [];
let pointsForTargetLine = [];
let refPixelLength = 0;
let scale = 0;
let currentEstimatedSizeMm = 0;

// 対向車分析データ
let vehicleSnapshot1 = { points: [], time: 0, angle: null, midPoint: null, frameCaptured: false };
let vehicleSnapshot2 = { points: [], time: 0, angle: null, midPoint: null, frameCaptured: false };
let oncomingMarkingStep = 0;

// ズーム・パン状態
let videoNaturalWidth = 0, videoNaturalHeight = 0;
let zoomLevel = 1.0;
const MIN_ZOOM = 0.5, MAX_ZOOM = 10.0, ZOOM_STEP = 0.2;
let viewOffsetX = 0, viewOffsetY = 0;
let isPanning = false, lastPanX = 0, lastPanY = 0;
