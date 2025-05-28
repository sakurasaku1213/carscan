/**
 * アプリケーションメインコントローラー
 * 
 * すべてのモジュールを統合し、アプリケーション全体�E制御を行う�E�E
 * - モジュール間�E連携
 * - 初期化とライフサイクル管琁E
 * - エラーハンドリング
 * - アプリケーション状態�E管琁E
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
        
        this.isInitialized = false;
        this.elements = {};
        
        console.log('🚀 CarScan App created');
    }
    
    /**
     * アプリケーションの初期匁E
     */
    async initialize() {
        try {
            console.log('🚀 Initializing CarScan App...');
            
            // DOM要素の取征E
            this.initializeDOMElements();
            
            // アプリケーション状態�E初期匁E
            this.initializeAppState();
            
            // モジュールの初期匁E
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
        
        // スチE�Eタス表示要素
        this.elements.videoStatusText = DOMUtils.getElement('#videoStatusText');
        this.elements.captureStatusText = DOMUtils.getElement('#captureStatusText');
        this.elements.dimensionStatusText = DOMUtils.getElement('#dimensionStatusText');
        this.elements.commonInstructionText = DOMUtils.getElement('#commonInstructionText');
        
        // チE��チE��要素
        this.elements.debugInfo = DOMUtils.getElement('#debugInfo');
        
        console.log('🔗 DOM elements initialized');
    }
    
    /**
     * アプリケーション状態�E初期匁E
     */    initializeAppState() {
        // 初期状態�E設宁E
        this.state.set('app.initialized', false);
        this.state.set('app.currentStep', 'video'); // 'video', 'capture', 'measurement'
        
        // ビデオ状慁E
        this.state.set('video.loaded', false);
        this.state.set('video.playing', false);
        this.state.set('video.currentTime', 0);
        this.state.set('video.duration', 0);
        
        // キャプチャ状慁E
        this.state.set('capture.hasImage', false);
        this.state.set('capture.zoomLevel', 1);
        this.state.set('capture.viewOffsetX', 0);
        this.state.set('capture.viewOffsetY', 0);
        this.state.set('capture.imageWidth', 0);
        this.state.set('capture.imageHeight', 0);
        
        // 測定状慁E
        this.state.set('measurement.mode', 'none');
        this.state.set('measurement.completed', false);
        
        // 状態変更の監要E
        this.state.subscribe('app.*', (key, value) => {
            this.onAppStateChange(key, value);
        });
        
        console.log('📊 App state initialized');
    }
      /**
     * モジュールの初期匁E
     */
    async initializeModules() {
        // ビデオマネージャーの初期匁E
        await this.videoManager.init();
        
        // キャプチャマネージャーの初期匁E
        await this.captureManager.init();
        
        // 測定�Eネ�Eジャーの初期匁E
        await this.measurementManager.init();
        
        console.log('🔧 All modules initialized');
    }
    
    /**
     * イベントリスナ�Eの設宁E
     */
    setupEventListeners() {
        // ビデオファイル選抁E
        if (this.elements.videoFileInput) {
            this.elements.videoFileInput.addEventListener('change', (e) => {
                this.handleVideoFileSelection(e);
            });
        }
        
        // ビデオコントロール
        if (this.elements.playPauseButton) {
            this.elements.playPauseButton.addEventListener('click', () => {
                this.toggleVideoPlayback();
            });
        }
        
        if (this.elements.captureButton) {
            this.elements.captureButton.addEventListener('click', () => {
                this.captureCurrentFrame();
            });
        }
        
        if (this.elements.progressSlider) {
            this.elements.progressSlider.addEventListener('input', (e) => {
                this.seekVideo(parseFloat(e.target.value));
            });
        }
        
        // キャプチャキャンバスのクリチE���E�測定用�E�E
        if (this.elements.captureCanvas) {
            this.elements.captureCanvas.addEventListener('click', (e) => {
                this.handleCaptureCanvasClick(e);
            });
        }
        
        // キーボ�EドショートカチE��
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcut(e);
        });
        
        // ウィンドウリサイズ
        window.addEventListener('resize', () => {
            this.handleWindowResize();
        });
        
        console.log('🎛�E�EEvent listeners setup complete');
    }
    
    /**
     * モジュール間連携の設宁E
     */
    setupModuleInteractions() {
        // ビデオマネージャーの購読
        this.videoManager.subscribe((event, data) => {
            this.onVideoEvent(event, data);
        });
        
        // キャプチャマネージャーの購読
        this.captureManager.subscribe((event, data) => {
            this.onCaptureEvent(event, data);
        });
        
        // 測定�Eネ�Eジャーの購読
        this.measurementManager.subscribe((event, data) => {
            this.onMeasurementEvent(event, data);
        });
        
        console.log('🔄 Module interactions setup complete');
    }
    
    /**
     * UI状態�E初期匁E
     */
    initializeUI() {
        // 初期状態では動画読み込み征E��        this.updateCurrentStep('video');
        this.showInstructionMessage('動画ファイルを選択してください。');
        
        // ボタンの初期状慁E
        if (this.elements.playPauseButton) {
            this.elements.playPauseButton.disabled = true;
        }
        if (this.elements.captureButton) {
            this.elements.captureButton.disabled = true;
        }
        if (this.elements.startMeasurementButton) {
            this.elements.startMeasurementButton.disabled = true;
        }
        
        console.log('🎨 UI initialized');
    }
    
    /**
     * ビデオファイル選択�E処琁E
     * @param {Event} e - ファイル選択イベンチE
     */
    async handleVideoFileSelection(e) {
        const file = e.target.files?.[0];
        if (!file) return;
        
        try {
            this.showInstructionMessage('動画を読み込み中...');
            await this.videoManager.loadVideoFile(file);
        } catch (error) {
            console.error('❁EVideo loading failed:', error);
            this.showErrorMessage('動画ファイルの読み込みに失敗しました、E);
        }
    }
    
    /**
     * ビデオ再生/一時停止の刁E��替ぁE
     */
    toggleVideoPlayback() {
        if (this.state.getState('video.playing')) {
            this.videoManager.pause();
        } else {
            this.videoManager.play();
        }
    }
    
    /**
     * 現在のフレームをキャプチャ
     */
    async captureCurrentFrame() {
        try {
            this.showInstructionMessage('フレームをキャプチャ中...');
            await this.captureManager.captureCurrentFrame();
        } catch (error) {
            console.error('❁EFrame capture failed:', error);
            this.showErrorMessage('フレームのキャプチャに失敗しました、E);
        }
    }
    
    /**
     * ビデオシーク
     * @param {number} progress - 進捗！E-1�E�E
     */
    seekVideo(progress) {
        this.videoManager.seekToProgress(progress);
    }
    
    /**
     * キャプチャキャンバスクリチE��の処琁E
     * @param {MouseEvent} e - マウスイベンチE
     */
    handleCaptureCanvasClick(e) {
        // 測定モード�E場合�Eみ処琁E
        if (this.measurementManager.getMode() === 'none') {
            return;
        }
        
        const rect = this.elements.captureCanvas.getBoundingClientRect();
        const canvasX = e.clientX - rect.left;
        const canvasY = e.clientY - rect.top;
        
        const handled = this.measurementManager.handleClick(canvasX, canvasY);
        
        if (handled) {
            // 測定点が追加された場合、キャプチャキャンバスを�E描画
            this.captureManager.redraw();
        }
    }
    
    /**
     * キーボ�EドショートカチE��の処琁E
     * @param {KeyboardEvent} e - キーボ�EドイベンチE
     */
    handleKeyboardShortcut(e) {
        // Escキー: 現在の操作をキャンセル
        if (e.key === 'Escape') {
            if (this.measurementManager.getMode() !== 'none') {
                this.measurementManager.reset();
                this.captureManager.redraw();
            }
        }
        
        // スペ�Eスキー: 再生/一時停止
        if (e.key === ' ' && this.state.getState('video.loaded')) {
            e.preventDefault();
            this.toggleVideoPlayback();
        }
        
        // Enterキー: フレームキャプチャ
        if (e.key === 'Enter' && this.state.getState('video.loaded')) {
            e.preventDefault();
            this.captureCurrentFrame();
        }
    }
    
    /**
     * ウィンドウリサイズの処琁E
     */
    handleWindowResize() {
        // キャンバスのリサイズ処琁E
        if (this.state.getState('video.loaded')) {
            this.videoManager.resizeCanvas();
        }
        
        if (this.state.getState('capture.hasImage')) {
            this.captureManager.resizeCanvas();
        }
    }
    
    /**
     * ビデオイベント�E処琁E
     * @param {string} event - イベント名
     * @param {*} data - チE�Eタ
     */
    onVideoEvent(event, data) {
        switch (event) {
            case 'videoLoaded':
                this.onVideoLoaded(data);
                break;
            case 'playStateChanged':
                this.onVideoPlayStateChanged(data);
                break;
            case 'timeUpdate':
                this.onVideoTimeUpdate(data);
                break;
            case 'videoError':
                this.onVideoError(data);
                break;
        }
    }
    
    /**
     * キャプチャイベント�E処琁E
     * @param {string} event - イベント名
     * @param {*} data - チE�Eタ
     */
    onCaptureEvent(event, data) {
        switch (event) {
            case 'frameCaptured':
                this.onFrameCaptured(data);
                break;
            case 'captureError':
                this.onCaptureError(data);
                break;
            case 'redrawRequested':
                this.onCaptureRedrawRequested();
                break;
        }
    }
    
    /**
     * 測定イベント�E処琁E
     * @param {string} event - イベント名
     * @param {*} data - チE�Eタ
     */
    onMeasurementEvent(event, data) {
        switch (event) {
            case 'measurementStarted':
                this.onMeasurementStarted();
                break;
            case 'measurementCompleted':
                this.onMeasurementCompleted(data);
                break;
            case 'measurementReset':
                this.onMeasurementReset();
                break;
            case 'referencePointAdded':
            case 'targetPointAdded':
                this.onMeasurementPointAdded(event, data);
                break;
        }
    }
    
    /**
     * 動画読み込み完亁E��の処琁E
     * @param {Object} data - 動画チE�Eタ
     */
    onVideoLoaded(data) {
        this.state.set('video.loaded', true);
        this.state.set('video.duration', data.duration);
        
        // UIの更新
        if (this.elements.playPauseButton) {
            this.elements.playPauseButton.disabled = false;
        }
        if (this.elements.captureButton) {
            this.elements.captureButton.disabled = false;
        }
        if (this.elements.progressSlider) {
            this.elements.progressSlider.disabled = false;
            this.elements.progressSlider.max = 1;
        }
        
        this.updateCurrentStep('capture');
        this.showInstructionMessage('動画が読み込まれました。測定したいフレームでキャプチャボタンを押してください、E);
        this.showStatusMessage(this.elements.videoStatusText, '動画読み込み完亁E);
        
        console.log('📹 Video loaded successfully');
    }
    
    /**
     * 動画再生状態変更時�E処琁E
     * @param {Object} data - 再生状態データ
     */
    onVideoPlayStateChanged(data) {
        this.state.set('video.playing', data.playing);
        
        if (this.elements.playPauseButton) {
            this.elements.playPauseButton.textContent = data.playing ? '⏸ 一時停止' : '▶ 再生';
        }
    }
    
    /**
     * 動画時間更新時�E処琁E
     * @param {Object} data - 時間チE�Eタ
     */
    onVideoTimeUpdate(data) {
        this.state.set('video.currentTime', data.currentTime);
        
        if (this.elements.progressSlider) {
            this.elements.progressSlider.value = data.progress;
        }
    }
    
    /**
     * 動画エラー時�E処琁E
     * @param {Object} data - エラーチE�Eタ
     */
    onVideoError(data) {
        this.showErrorMessage(`動画エラー: ${data.message}`);
        this.showStatusMessage(this.elements.videoStatusText, `エラー: ${data.message}`);
    }
    
    /**
     * フレームキャプチャ完亁E��の処琁E
     * @param {Object} data - キャプチャチE�Eタ
     */
    onFrameCaptured(data) {
        this.state.set('capture.hasImage', true);
        this.state.set('capture.imageWidth', data.width);
        this.state.set('capture.imageHeight', data.height);
        
        // 測定�Eタンを有効匁E
        if (this.elements.startMeasurementButton) {
            this.elements.startMeasurementButton.disabled = false;
        }
        
        this.updateCurrentStep('measurement');
        this.showInstructionMessage('フレームがキャプチャされました。測定開始�Eタンを押して寸法測定を開始してください、E);
        this.showStatusMessage(this.elements.captureStatusText, 'フレームキャプチャ完亁E);
        
        console.log('📸 Frame captured successfully');
    }
    
    /**
     * キャプチャエラー時�E処琁E
     * @param {Object} data - エラーチE�Eタ
     */
    onCaptureError(data) {
        this.showErrorMessage(`キャプチャエラー: ${data.message}`);
        this.showStatusMessage(this.elements.captureStatusText, `エラー: ${data.message}`);
    }
    
    /**
     * キャプチャ再描画要求時の処琁E
     */
    onCaptureRedrawRequested() {
        // 測定要素も含めて再描画
        const ctx = this.elements.captureCanvas.getContext('2d');
        if (ctx) {
            this.measurementManager.drawMeasurementElements(ctx);
        }
    }
    
    /**
     * 測定開始時の処琁E
     */
    onMeasurementStarted() {
        this.state.set('measurement.mode', 'reference');
        this.showInstructionMessage('参�E線を設定してください。既知のサイズのオブジェクト�E両端をクリチE��してください、E);
        this.showStatusMessage(this.elements.dimensionStatusText, '参�E線設定中');
    }
    
    /**
     * 測定完亁E��の処琁E
     * @param {Object} data - 測定結果チE�Eタ
     */
    onMeasurementCompleted(data) {
        this.state.set('measurement.mode', 'completed');
        this.state.set('measurement.completed', true);
        
        this.showInstructionMessage(`測定完亁E��推定サイズ: ${data.estimatedSize.toFixed(2)} mm`);
        this.showStatusMessage(this.elements.dimensionStatusText, '測定完亁E);
        
        console.log('📏 Measurement completed:', data);
    }
    
    /**
     * 測定リセチE��時�E処琁E
     */
    onMeasurementReset() {
        this.state.set('measurement.mode', 'none');
        this.state.set('measurement.completed', false);
        
        this.showInstructionMessage('測定がリセチE��されました、E);
        this.showStatusMessage(this.elements.dimensionStatusText, '測定征E��中');
    }
    
    /**
     * 測定点追加時�E処琁E
     * @param {string} event - イベント名
     * @param {Object} data - 点チE�Eタ
     */
    onMeasurementPointAdded(event, data) {
        // キャプチャキャンバスを�E描画して測定点を表示
        this.captureManager.redraw();
    }
    
    /**
     * アプリケーション状態変更時�E処琁E
     * @param {string} key - 状態キー
     * @param {*} value - 値
     */
    onAppStateChange(key, value) {
        // チE��チE��惁E��の更新
        this.updateDebugInfo();
        
        // 特定�E状態変更に応じた�E琁E
        if (key === 'app.currentStep') {
            this.onCurrentStepChanged(value);
        }
    }
    
    /**
     * 現在のスチE��プ変更時�E処琁E
     * @param {string} step - 新しいスチE��チE
     */
    onCurrentStepChanged(step) {
        // スチE��プインジケーターの更新など
        console.log(`📍 Current step changed to: ${step}`);
    }
    
    /**
     * 現在のスチE��プを更新
     * @param {string} step - スチE��プ名
     */
    updateCurrentStep(step) {
        this.state.set('app.currentStep', step);
    }
    
    /**
     * スチE�EタスメチE��ージの表示
     * @param {HTMLElement} element - 表示要素
     * @param {string} message - メチE��ージ
     */
    showStatusMessage(element, message) {
        if (element) {
            DOMUtils.showMessage(element, message);
        }
    }
    
    /**
     * インストラクションメチE��ージの表示
     * @param {string} message - メチE��ージ
     */
    showInstructionMessage(message) {
        if (this.elements.commonInstructionText) {
            DOMUtils.showMessage(this.elements.commonInstructionText, message);
        }
    }
    
    /**
     * エラーメチE��ージの表示
     * @param {string} message - エラーメチE��ージ
     */
    showErrorMessage(message) {
        console.error('❁EApp Error:', message);
        
        if (this.elements.commonInstructionText) {
            DOMUtils.showMessage(this.elements.commonInstructionText, `❁E${message}`, 'error');
        }
        
        // 忁E��に応じてアラートも表示
        // alert(message);
    }
    
    /**
     * チE��チE��惁E��の更新
     */
    updateDebugInfo() {
        if (!this.elements.debugInfo) return;
        
        const debugData = {
            currentStep: this.state.getState('app.currentStep'),
            videoLoaded: this.state.getState('video.loaded'),
            videoPlaying: this.state.getState('video.playing'),
            captureHasImage: this.state.getState('capture.hasImage'),
            measurementMode: this.state.getState('measurement.mode'),
            zoomLevel: this.state.getState('capture.zoomLevel'),
            initialized: this.isInitialized
        };
        
        this.elements.debugInfo.textContent = JSON.stringify(debugData, null, 2);
    }
    
    /**
     * アプリケーションの破棁E
     */
    destroy() {
        console.log('🗑�E�EDestroying CarScan App...');
        
        // モジュールの破棁E
        this.videoManager.destroy();
        this.captureManager.destroy();
        this.measurementManager.destroy();
        this.state.destroy();
        
        // 要素参�Eのクリア
        this.elements = {};
        this.isInitialized = false;
        
        console.log('✁ECarScan App destroyed');
    }
}

// チE��ォルトエクスポ�EチE
export default App;
