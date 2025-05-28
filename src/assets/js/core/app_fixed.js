/**
 * アプリケーションメインコントローラー
 * 
 * すべてのモジュールを統合し、アプリケーション全体の制御を行う：
 * - モジュール間の連携
 * - 初期化とライフサイクル管理
 * - エラーハンドリング
 * - アプリケーション状態の管理
 */

import appState from './state.js';
import { VideoManager } from '../modules/video.js';
import { CaptureManager } from '../modules/capture.js';
import { MeasurementManager } from '../modules/measurement.js';
import { DOMUtils } from '../utils/dom.js';

export class App {
    constructor() {
        this.state = appState;
        this.videoManager = new VideoManager();
        this.captureManager = new CaptureManager();
        this.measurementManager = new MeasurementManager();
        
        this.elements = {};
        this.isInitialized = false;
        
        console.log('🚀 CarScan App created');
    }
    
    /**
     * アプリケーションの初期化
     */
    async initialize() {
        try {
            console.log('🚀 Initializing CarScan App...');
            
            // 状態の初期化
            this.initializeAppState();
            
            // DOM要素の初期化
            this.initializeDOMElements();
            
            // モジュールの初期化
            await this.initializeModules();
            
            // イベントリスナーの設定
            this.setupEventListeners();
            
            // モジュール間連携の設定
            this.setupModuleInteractions();
            
            // UI状態の初期化
            this.initializeUI();
            
            this.isInitialized = true;
            console.log('✅ CarScan App initialized successfully');
            
        } catch (error) {
            console.error('❌ Failed to initialize CarScan App:', error);
            this.showErrorMessage('アプリケーションの初期化に失敗しました。ページを再読み込みしてください。');
        }
    }
    
    /**
     * DOM要素の初期化
     */
    initializeDOMElements() {
        // ビデオ関連要素
        this.elements.videoCanvas = DOMUtils.getElement('#videoCanvas');
        this.elements.videoFileInput = DOMUtils.getElement('#videoFileInput');
        this.elements.videoControls = DOMUtils.getElement('#videoControls');
        this.elements.playPauseButton = DOMUtils.getElement('#playPauseButton');
        this.elements.captureButton = DOMUtils.getElement('#captureButton');
        this.elements.progressSlider = DOMUtils.getElement('#progressSlider');
        
        // キャプチャ関連要素
        this.elements.captureCanvas = DOMUtils.getElement('#captureCanvas');
        this.elements.captureContainer = DOMUtils.getElement('#captureContainer');
        
        // 測定関連要素
        this.elements.startMeasurementButton = DOMUtils.getElement('#startMeasurementButton');
        this.elements.clearMeasurementButton = DOMUtils.getElement('#clearMeasurementButton');
        this.elements.refObjectActualSizeInput = DOMUtils.getElement('#refObjectActualSizeInput');
        
        // ステータス表示要素
        this.elements.videoStatusText = DOMUtils.getElement('#videoStatusText');
        this.elements.captureStatusText = DOMUtils.getElement('#captureStatusText');
        this.elements.dimensionStatusText = DOMUtils.getElement('#dimensionStatusText');
        
        console.log('🔗 DOM elements initialized');
    }
    
    /**
     * アプリケーション状態の初期化
     */
    initializeAppState() {
        // 初期状態の設定
        this.state.set('app.initialized', false);
        this.state.set('app.currentStep', 'video'); // 'video', 'capture', 'measurement'
        
        // ビデオ状態
        this.state.set('video.loaded', false);
        this.state.set('video.playing', false);
        this.state.set('video.currentTime', 0);
        this.state.set('video.duration', 0);
        
        // キャプチャ状態
        this.state.set('capture.hasImage', false);
        this.state.set('capture.zoomLevel', 1);
        this.state.set('capture.viewOffsetX', 0);
        this.state.set('capture.viewOffsetY', 0);
        this.state.set('capture.imageWidth', 0);
        this.state.set('capture.imageHeight', 0);
        
        // 測定状態
        this.state.set('measurement.mode', 'none');
        this.state.set('measurement.completed', false);
        
        // 状態変更の監視
        this.state.subscribe('app.*', (key, value) => {
            this.onAppStateChange(key, value);
        });
        
        this.state.subscribe('video.*', (key, value) => {
            this.onVideoStateChange(key, value);
        });
        
        this.state.subscribe('capture.*', (key, value) => {
            this.onCaptureStateChange(key, value);
        });
        
        this.state.subscribe('measurement.*', (key, value) => {
            this.onMeasurementStateChange(key, value);
        });
    }
    
    /**
     * モジュールの初期化
     */
    async initializeModules() {
        try {
            await this.videoManager.init(this.elements.videoCanvas);
            await this.captureManager.init(this.elements.captureCanvas);
            await this.measurementManager.init();
            
            console.log('🔧 All modules initialized');
        } catch (error) {
            console.error('❌ Module initialization failed:', error);
            throw error;
        }
    }
    
    /**
     * イベントリスナーの設定
     */
    setupEventListeners() {
        // 動画ファイル選択
        if (this.elements.videoFileInput) {
            this.elements.videoFileInput.addEventListener('change', (event) => {
                this.handleVideoFileSelect(event);
            });
        }
        
        // 再生/一時停止ボタン
        if (this.elements.playPauseButton) {
            this.elements.playPauseButton.addEventListener('click', () => {
                this.handlePlayPause();
            });
        }
        
        // キャプチャボタン
        if (this.elements.captureButton) {
            this.elements.captureButton.addEventListener('click', () => {
                this.handleCapture();
            });
        }
        
        // 測定開始ボタン
        if (this.elements.startMeasurementButton) {
            this.elements.startMeasurementButton.addEventListener('click', () => {
                this.handleStartMeasurement();
            });
        }
        
        // 測定クリアボタン
        if (this.elements.clearMeasurementButton) {
            this.elements.clearMeasurementButton.addEventListener('click', () => {
                this.handleClearMeasurement();
            });
        }
        
        console.log('🎯 Event listeners set up');
    }
    
    /**
     * モジュール間連携の設定
     */
    setupModuleInteractions() {
        // VideoManager → App
        this.videoManager.onVideoLoaded = (data) => {
            this.onVideoLoaded(data);
        };
        
        this.videoManager.onVideoError = (error) => {
            this.onVideoError(error);
        };
        
        // CaptureManager → App
        this.captureManager.onCaptureComplete = (data) => {
            this.onCaptureComplete(data);
        };
        
        this.captureManager.onCaptureError = (error) => {
            this.onCaptureError(error);
        };
        
        // MeasurementManager → App
        this.measurementManager.onMeasurementComplete = (data) => {
            this.onMeasurementComplete(data);
        };
        
        this.measurementManager.onMeasurementStart = () => {
            this.onMeasurementStart();
        };
        
        console.log('🔗 Module interactions set up');
    }
    
    /**
     * UI状態の初期化
     */
    initializeUI() {
        this.updateCurrentStep('video');
        this.showInstructionMessage('動画ファイルを選択してください。');
        
        // ボタンの初期状態
        if (this.elements.playPauseButton) {
            this.elements.playPauseButton.disabled = true;
        }
        if (this.elements.captureButton) {
            this.elements.captureButton.disabled = true;
        }
        if (this.elements.startMeasurementButton) {
            this.elements.startMeasurementButton.disabled = true;
        }
    }
    
    // イベントハンドラー
    handleVideoFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.videoManager.loadVideo(file);
        }
    }
    
    handlePlayPause() {
        this.videoManager.togglePlayPause();
    }
    
    handleCapture() {
        try {
            this.captureManager.captureFrame(this.videoManager.getCurrentFrame());
        } catch (error) {
            this.showErrorMessage('フレームのキャプチャに失敗しました。');
        }
    }
    
    handleStartMeasurement() {
        const refSize = parseFloat(this.elements.refObjectActualSizeInput.value);
        if (isNaN(refSize) || refSize <= 0) {
            this.showErrorMessage('基準オブジェクトのサイズを正しく入力してください。');
            return;
        }
        
        this.measurementManager.startMeasurement(refSize);
    }
    
    handleClearMeasurement() {
        this.measurementManager.clearMeasurement();
    }
    
    // モジュールイベント応答
    onVideoLoaded(data) {
        this.state.set('video.loaded', true);
        this.state.set('video.duration', data.duration);
        
        this.showInstructionMessage('動画が読み込まれました。測定したいフレームでキャプチャボタンを押してください。');
        this.showStatusMessage(this.elements.videoStatusText, '動画読み込み完了');
        
        console.log('📹 Video loaded successfully');
        
        // UIの更新
        if (this.elements.playPauseButton) {
            this.elements.playPauseButton.disabled = false;
        }
        if (this.elements.captureButton) {
            this.elements.captureButton.disabled = false;
        }
    }
    
    onVideoError(error) {
        this.showErrorMessage('動画ファイルの読み込みに失敗しました。');
        console.error('❌ Video loading error:', error);
    }
    
    onCaptureComplete(data) {
        this.state.set('capture.hasImage', true);
        this.state.set('capture.imageWidth', data.width);
        this.state.set('capture.imageHeight', data.height);
        
        this.updateCurrentStep('measurement');
        this.showInstructionMessage('フレームがキャプチャされました。測定開始ボタンを押して寸法測定を開始してください。');
        this.showStatusMessage(this.elements.captureStatusText, 'フレームキャプチャ完了');
        
        console.log('📸 Frame captured successfully');
        
        // UIの更新
        if (this.elements.startMeasurementButton) {
            this.elements.startMeasurementButton.disabled = false;
        }
    }
    
    onCaptureError(error) {
        this.showErrorMessage('フレームのキャプチャに失敗しました。');
        console.error('❌ Capture error:', error);
    }
    
    onMeasurementStart() {
        this.state.set('measurement.mode', 'reference');
        
        this.showInstructionMessage('参照線を設定してください。既知のサイズのオブジェクトの両端をクリックしてください。');
        this.showStatusMessage(this.elements.dimensionStatusText, '参照線設定中');
        
        console.log('📏 Measurement started');
    }
    
    onMeasurementComplete(data) {
        this.state.set('measurement.mode', 'completed');
        this.state.set('measurement.completed', true);
        
        this.showStatusMessage(this.elements.dimensionStatusText, '測定完了');
        this.showSuccessMessage(`測定結果: ${data.result.toFixed(2)}mm`);
        
        console.log('📏 Measurement completed:', data);
    }
    
    // 状態変更ハンドラー
    onAppStateChange(key, value) {
        console.log(`🔄 App state changed: ${key} = ${value}`);
    }
    
    onVideoStateChange(key, value) {
        console.log(`🎬 Video state changed: ${key} = ${value}`);
    }
    
    onCaptureStateChange(key, value) {
        console.log(`📸 Capture state changed: ${key} = ${value}`);
    }
    
    onMeasurementStateChange(key, value) {
        console.log(`📏 Measurement state changed: ${key} = ${value}`);
    }
    
    // ユーティリティメソッド
    updateCurrentStep(step) {
        this.state.set('app.currentStep', step);
        
        // ステップインジケーターの更新
        const steps = ['video', 'capture', 'measurement'];
        steps.forEach((s, index) => {
            const stepElement = document.querySelector(`#step${s.charAt(0).toUpperCase() + s.slice(1)}`);
            if (stepElement) {
                stepElement.classList.toggle('active', steps.indexOf(step) >= index);
            }
        });
    }
    
    showInstructionMessage(message) {
        const element = document.querySelector('.instruction-panel p');
        if (element) {
            element.innerHTML = `<strong>📝 手順:</strong> ${message}`;
        }
    }
    
    showStatusMessage(element, message) {
        if (element) {
            element.textContent = message;
        }
    }
    
    showSuccessMessage(message) {
        this.showMessage(message, 'success');
    }
    
    showErrorMessage(message) {
        this.showMessage(message, 'error');
        console.error('❌ App Error:', message);
    }
    
    showMessage(message, type = 'info') {
        // メッセージ表示の実装
        console.log(`📢 ${type.toUpperCase()}: ${message}`);
    }
}

// グローバルアクセス用（デバッグ時）
if (typeof window !== 'undefined') {
    window.App = App;
}
