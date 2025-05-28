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
        console.log("🌀 App constructor called");
        this.state = appState;
        this.videoManager = null;
        this.captureManager = null;
        this.measurementManager = null;

        this.isDragging = false;
        this.lastMouseX = 0;
        this.lastMouseY = 0;

        this.moduleInteractionsSetup = false; // Flag to prevent multiple setups
        this.eventListenersSetup = false; // Flag to prevent multiple setups

        // DOM elements (centralized for clarity, though UIManager might handle some)
        this.elements = {
            videoCanvas: DOMUtils.getElement('#videoCanvas'),
            videoFileInput: DOMUtils.getElement('#videoFileInput'),
            videoControls: DOMUtils.getElement('#videoControls'),
            playPauseButton: DOMUtils.getElement('#playPauseButton'),
            captureButton: DOMUtils.getElement('#captureButton'),
            progressSlider: DOMUtils.getElement('#progressSlider'),
            captureCanvas: DOMUtils.getElement('#captureCanvas'),
            captureContainer: DOMUtils.getElement('#captureContainer'),
            startMeasurementButton: DOMUtils.getElement('#startMeasurementButton'),
            clearMeasurementButton: DOMUtils.getElement('#clearMeasurementButton'),
            refObjectActualSizeInput: DOMUtils.getElement('#refObjectActualSizeInput'),
            videoStatusText: DOMUtils.getElement('#videoStatusText'),
            captureStatusText: DOMUtils.getElement('#captureStatusText'),
            dimensionStatusText: DOMUtils.getElement('#dimensionStatusText'),
        };

        // Ensure critical elements exist
        if (!this.elements.videoCanvas || !this.elements.captureCanvas) {
            console.error("🔥 Critical UI elements (videoCanvas or captureCanvas) not found in DOM during App construction.");
            this.showErrorMessage("UIの初期化に失敗しました。必須要素が見つかりません。", true);
            // Potentially throw an error or prevent further initialization
            // For now, we'll let initialize try to proceed but it will likely fail.
        }
        console.log("🌀 App constructor finished");
    }

    /**
     * アプリケーションの初期化
     */
    async initialize() {
        console.log("🚀 App.initialize() called");
        this.showErrorMessage('', false); // Clear any previous errors

        try {
            // Initialize managers first, as they might be needed by event listeners or interactions
            console.log("🔧 Initializing managers...");
            this.videoManager = new VideoManager(this.state, this.elements.videoCanvas);
            this.captureManager = new CaptureManager(this.state, this.videoManager, this.elements.captureCanvas);
            this.measurementManager = new MeasurementManager(this.state, this.captureManager);
            console.log("👍 Managers initialized.");

            this.setupEventListeners();
            this.setupModuleInteractions();

            this.state.set('app.initialized', true);
            console.log("✅ App initialized successfully.");
            this.updateUIBasedOnState(); // Initial UI update
            return true;
        } catch (error) {
            console.error("❌ Error during app initialization:", error);
            this.showErrorMessage(`初期化エラー: ${error.message}`, true);
            this.state.set('app.initialized', false);
            return false;
        }
    }

    /**
     * イベントリスナーの設定
     */
    setupEventListeners() {
        if (this.eventListenersSetup) {
            console.warn("🎧 Event listeners already set up. Skipping.");
            return;
        }
        console.log('🎧 Setting up event listeners...');

        // 動画ファイル選択
        if (this.elements.videoFileInput) {
            this.elements.videoFileInput.addEventListener('change', (event) => {
                this.handleVideoFileSelect(event);
            });
        } else {
            console.warn("videoFileInput element not found for event listener setup.");
        }

        // 再生/一時停止ボタン
        if (this.elements.playPauseButton) {
            this.elements.playPauseButton.addEventListener('click', () => {
                this.handlePlayPause();
            });
        } else {
            console.warn("playPauseButton element not found for event listener setup.");
        }

        // キャプチャボタン
        if (this.elements.captureButton) {
            this.elements.captureButton.addEventListener('click', () => {
                this.handleCapture();
            });
        } else {
            console.warn("captureButton element not found for event listener setup.");
        }

        // 測定開始ボタン
        if (this.elements.startMeasurementButton) {
            this.elements.startMeasurementButton.addEventListener('click', () => {
                this.handleStartMeasurement();
            });
        } else {
            console.warn("startMeasurementButton element not found for event listener setup.");
        }

        // 測定クリアボタン
        if (this.elements.clearMeasurementButton) {
            this.elements.clearMeasurementButton.addEventListener('click', () => {
                this.handleClearMeasurement();
            });
        } else {
            console.warn("clearMeasurementButton element not found for event listener setup.");
        }

        console.log('🎧 Event listeners set up.');
        this.eventListenersSetup = true;
    }

    /**
     * モジュール間連携の設定
     */
    setupModuleInteractions() {
        if (this.moduleInteractionsSetup) {
            console.warn("🔗 Module interactions already set up. Skipping.");
            return;
        }
        console.log('🔗 App.setupModuleInteractions() called. Setting up module interactions and state subscriptions...');

        this.state.subscribe('app.initialized', (path, key, newValue) => this.onAppStateChange(key, newValue));

        this.state.subscribe('video.*', (path, key, newValue, oldValue) => {
            this.onVideoStateChange(key, newValue, oldValue);
        });
        this.state.subscribe('capture.*', (path, key, newValue, oldValue) => {
            this.onCaptureStateChange(key, newValue, oldValue);
        });
        this.state.subscribe('measurement.*', (path, key, newValue, oldValue) => {
            this.onMeasurementStateChange(key, newValue, oldValue);
        });

        this.moduleInteractionsSetup = true; // Set flag after successful setup
        console.log('🔗 Module interactions and state subscriptions set up.');
    }

    // イベントハンドラー
    handleVideoFileSelect(event) {
        console.log("📹 handleVideoFileSelect triggered");
        if (!this.videoManager) {
            console.error("VideoManager not initialized in handleVideoFileSelect!");
            this.showErrorMessage("VideoManagerが初期化されていません。");
            return;
        }
        const file = event.target.files[0];
        if (file) {
            this.videoManager.loadVideoFile(file);
        }
    }
    
    handlePlayPause() {
        console.log('⏯️ Play/Pause button clicked');
        if (!this.videoManager) {
            console.error("VideoManager not initialized in handlePlayPause!");
            this.showErrorMessage("VideoManagerが初期化されていません。");
            return;
        }
        // This will throw if togglePlayPause is not a function
        try {
            this.videoManager.togglePlayPause(); 
        } catch (error) {
            console.error("Error calling videoManager.togglePlayPause():", error);
            this.showErrorMessage("再生/一時停止の切り替えに失敗しました。");
        }
        // UI update should be handled by onVideoStateChange reacting to 'video.playing'
        console.log(`Current video.playing state: ${this.state.get('video.playing')}`);
    }
    
    handleCapture() {
        console.log('📸 Capture button clicked');
        if (!this.captureManager) {
            console.error("CaptureManager not initialized in handleCapture!");
            this.showErrorMessage("CaptureManagerが初期化されていません。");
            return;
        }
        try {
            this.captureManager.captureFrame(); // 変更後：引数なしで呼び出す
        } catch (error) {
            console.error("Error during captureFrame call from app.js:", error);
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
    
    handleResetMeasurement() {
        console.log('🔄 Reset Measurement button clicked');
        if (!this.measurementManager) {
            console.error("MeasurementManager not initialized in handleResetMeasurement!");
            this.showErrorMessage("MeasurementManagerが初期化されていません。");
            return;
        }
        this.measurementManager.clearMeasurement();
    }
    
    handleCanvasMouseDown(event) {
        // console.log('🖱️ Canvas Mouse Down');
        if (!this.captureManager) return;
        if (event.button === 0) { // Left mouse button
            this.captureManager.startPan(event.offsetX, event.offsetY);
        }
    }

    handleCanvasMouseMove(event) {
        // console.log('↔️ Canvas Mouse Move');
        if (!this.captureManager) return;
        if (this.state.get('capture.isPanning')) {
            this.captureManager.pan(event.offsetX, event.offsetY);
        }
    }

    handleCanvasMouseUp() {
        // console.log('🖱️ Canvas Mouse Up');
        if (!this.captureManager) return;
        if (this.state.get('capture.isPanning')) {
            this.captureManager.endPan();
        }
    }

    handleCanvasMouseLeave() {
        // console.log('💨 Canvas Mouse Leave');
        if (!this.captureManager) return;
        // Optional: If you want panning to stop when the mouse leaves the canvas
        if (this.state.get('capture.isPanning')) {
            this.captureManager.endPan();
        }
    }

    handleCanvasWheel(event) {
        // console.log('🎡 Canvas Wheel');
        if (!this.captureManager) return;
        event.preventDefault();
        this.captureManager.zoom(event.deltaY > 0 ? 1 : -1);
    }

    handlePhotoClick(event) {
        console.log('🖱️ Photo Clicked for measurement');
        if (!this.measurementManager) {
            console.error("MeasurementManager not initialized in handlePhotoClick!");
            this.showErrorMessage("MeasurementManagerが初期化されていません。");
            return;
        }
        this.measurementManager.addMeasurementPoint(event.offsetX, event.offsetY);
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
    onAppStateChange(key, newValue) {
        console.log(`🔄 App state changed. Key: "${key}", NewValue: ${newValue}`);
    }
    
    onVideoStateChange(key, newValue, oldValue) {
        console.log(`🎬 App.onVideoStateChange - Key: "${key}", NewValue:`, newValue, `, OldValue:`, oldValue);

        if (key === 'loaded') {
            console.log(`📹 'loaded' change detected. New value: ${newValue}`);
            if (newValue === true) {
                console.log('📹 Processing video.loaded === true...');
                if (this.elements.playPauseButton) {
                    this.elements.playPauseButton.disabled = false;
                    console.log('📹 Play/Pause button enabled.');
                } else {
                    console.warn('📹 Play/Pause button element not found.');
                }

                if (this.elements.captureButton) {
                    this.elements.captureButton.disabled = false;
                    console.log('📹 Capture button enabled.');
                } else {
                    console.warn('📹 Capture button element not found.');
                }
                
                this.showInstructionMessage('動画が読み込まれました。測定したいフレームでキャプチャボタンを押してください。');
                this.showStatusMessage(this.elements.videoStatusText, '動画読み込み完了');
                console.log('📹 UI messages updated for video loaded.');

            } else { // video.loaded is false
                console.log('📹 Processing video.loaded === false...');
                if (this.elements.playPauseButton) {
                    this.elements.playPauseButton.disabled = true;
                    console.log('📹 Play/Pause button disabled.');
                } else {
                    console.warn('📹 Play/Pause button element not found during disable.');
                }
                if (this.elements.captureButton) {
                    this.elements.captureButton.disabled = true;
                    console.log('📹 Capture button disabled.');
                } else {
                    console.warn('📹 Capture button element not found during disable.');
                }
                this.showInstructionMessage('動画ファイルを選択してください。');
                this.showStatusMessage(this.elements.videoStatusText, '動画未読み込み');
                console.log('📹 UI messages updated for video not loaded.');
            }
        } else if (key === 'playing') {
            console.log(`▶️ 'playing' change detected. New value: ${newValue}`);
            if (this.elements.playPauseButton) {
                this.elements.playPauseButton.textContent = newValue ? '一時停止' : '再生';
                console.log(`⏯️ Play/Pause button text updated to: ${this.elements.playPauseButton.textContent}`);
            } else {
                console.warn('⏯️ Play/Pause button element not found for text update.');
            }
        } else if (key === 'currentTime') {
            // console.log(`⏱️ 'currentTime' change detected. New value: ${newValue}`);
            // スライダー更新などの処理 (必要であれば)
            if (this.elements.progressSlider && this.state.get('video.duration') > 0) {
                const progress = (newValue / this.state.get('video.duration')) * 100;
                this.elements.progressSlider.value = progress;
            }
        } else if (key === 'duration') {
            console.log(`⏳ 'duration' change detected. New value: ${newValue}`);
            // UI更新 (例: duration表示)
        } else if (key === 'element') {
            console.log('📹 Video element set in state.');
            // 必要であれば、ここでvideo要素に依存するUIの初期設定を行う
        }
    }
    
    onCaptureStateChange(key, newValue, oldValue) {
        console.log(`📸 App.onCaptureStateChange - Key: "${key}", NewValue:`, newValue, `, OldValue:`, oldValue);

        if (key === 'hasImage') {
            console.log(`🖼️ 'hasImage' change detected. New value: ${newValue}`);
            if (newValue === true) {
                this.updateCurrentStep('measurement');
                this.showInstructionMessage('フレームがキャプチャされました。測定開始ボタンを押して寸法測定を開始してください。');
                this.showStatusMessage(this.elements.captureStatusText, 'フレームキャプチャ完了');
                if (this.elements.startMeasurementButton) {
                    this.elements.startMeasurementButton.disabled = false;
                }
                console.log('🖼️ UI updated for capture hasImage true.');
            } else {
                this.updateCurrentStep('capture'); // Or 'video' if appropriate
                this.showInstructionMessage('動画を再生し、測定したいフレームでキャプチャボタンを押してください。');
                this.showStatusMessage(this.elements.captureStatusText, 'キャプチャ待機中');
                if (this.elements.startMeasurementButton) {
                    this.elements.startMeasurementButton.disabled = true;
                }
                console.log('🖼️ UI updated for capture hasImage false.');
            }
        } else if (key === 'isCapturing') {
            console.log(`⏳ 'isCapturing' change detected. New value: ${newValue}`);
            if (this.elements.captureButton) {
                this.elements.captureButton.disabled = newValue; // Disable while capturing
            }
            this.showStatusMessage(this.elements.captureStatusText, newValue ? 'キャプチャ処理中...' : 'キャプチャ待機中');
        }
    }

    onMeasurementStateChange(key, newValue, oldValue) {
        console.log(`📏 App.onMeasurementStateChange - Key: "${key}", NewValue:`, newValue, `, OldValue:`, oldValue);

        if (key === 'mode') {
            console.log(`📐 'mode' change detected. New value: ${newValue}`);
            switch (newValue) {
                case 'idle':
                    this.showInstructionMessage('測定を開始するには、「測定開始」ボタンを押してください。');
                    this.showStatusMessage(this.elements.dimensionStatusText, '測定待機中');
                    if (this.elements.clearMeasurementButton) this.elements.clearMeasurementButton.disabled = true;
                    break;
                case 'reference':
                    this.showInstructionMessage('参照線を設定してください。既知のサイズのオブジェクトの両端をクリックしてください。');
                    this.showStatusMessage(this.elements.dimensionStatusText, '参照線設定中');
                     if (this.elements.clearMeasurementButton) this.elements.clearMeasurementButton.disabled = false;
                    break;
                case 'measure':
                    this.showInstructionMessage('測定対象のオブジェクトの両端をクリックしてください。');
                    this.showStatusMessage(this.elements.dimensionStatusText, '寸法測定中');
                    break;
                case 'completed':
                    this.showStatusMessage(this.elements.dimensionStatusText, '測定完了');
                    // 結果表示は measurement.result で行う
                    break;
            }
        } else if (key === 'result') {
            console.log(`📊 'result' change detected. New value:`, newValue);
            if (newValue && newValue.value !== null) {
                this.showSuccessMessage(`測定結果: ${newValue.value.toFixed(2)} ${newValue.unit || 'mm'}`);
                this.state.set('measurement.mode', 'completed'); // Ensure mode is completed
            } else {
                // Clear previous result if any
                // this.showSuccessMessage(''); // Or hide the message area
            }
        } else if (key === 'referenceLine') {
            console.log('📏 Reference line updated:', newValue);
            if (newValue && newValue.points && newValue.points.length === 2 && newValue.length > 0) {
                this.showInstructionMessage('参照線が設定されました。次に、測定対象のオブジェクトの両端をクリックしてください。');
                this.state.set('measurement.mode', 'measure');
            }
        } else if (key === 'measurementLine') {
             console.log('📏 Measurement line updated:', newValue);
            // Potentially update UI based on measurement line progress
        }
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

document.addEventListener('DOMContentLoaded', async () => {
    console.log("✨ DOMContentLoaded event fired.");
    if (window.appInstance) {
        console.warn("⚠️ App instance already exists on window.appInstance. Skipping new initialization.");
        return;
    }
    console.log("🚀 Creating new App instance.");
    window.appInstance = new App(); // Use a global flag to ensure single instance
    window.app = window.appInstance; // Keep original window.app for compatibility with potential direct calls

    try {
        const initialized = await window.app.initialize(); // Call initialize on the instance
        if (initialized) {
            console.log("✅ Application successfully initialized and ready via DOMContentLoaded.");
        } else {
            console.error("❌ Application initialization failed via DOMContentLoaded.");
            // Error message is shown by initialize() itself.
        }
    } catch (error) {
        console.error("❌ Critical error during app initialization via DOMContentLoaded:", error);
        // Attempt to show an error on the page if possible
        const errorElement = document.getElementById('appStatus') || document.createElement('div');
        if (!document.getElementById('appStatus')) {
            errorElement.id = 'appStatus'; // Ensure it has an ID if created
            // Try to prepend to body, but be careful if body itself is not ready (though DOMContentLoaded implies it is)
            if (document.body) {
                document.body.prepend(errorElement);
            }
        }
        errorElement.textContent = `致命的な初期化エラー: ${error.message}。詳細はコンソールを確認してください。`;
        errorElement.style.color = 'red';
        errorElement.style.padding = '10px';
        errorElement.style.backgroundColor = '#ffeeee';
        errorElement.style.border = '1px solid red';
        errorElement.style.position = 'fixed';
        errorElement.style.top = '10px';
        errorElement.style.left = '10px';
        errorElement.style.zIndex = '10000';
    }
});
